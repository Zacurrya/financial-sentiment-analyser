import logging
import re
from dotenv import load_dotenv
from urllib.parse import urlparse

from constants import QUARTER_YEAR_PATTERN, TICKER_BOUNDARY_PATTERN_FORMAT
from models import TranscriptURLData
from scraping import serp_client

load_dotenv()

logger = logging.getLogger(__name__)


def _normalize_quarter(value):
    if value is None: return None

    text = str(value).strip().upper()
    if not text: return None
    if text.startswith("Q"): text = text[1:]

    return f"Q{text}" if text in {"1", "2", "3", "4"} else None

def extract_date(url):
    if not url: return None
    path = urlparse(url).path.rstrip("/")
    match = re.search(r"/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/", path + "/")
    if not match:
        return None

    return int(match.group("year")), int(match.group("month")), int(match.group("day"))

def format_date(value):
    if not value: return ""
    year, month, day = value
    return f"{year:04d}/{month:02d}/{day:02d}"


# TICKER MATCHING
def url_matches_ticker(url: str, ticker: str) -> bool:
    if not url or not ticker: return False

    path = urlparse(url).path.lower()
    ticker_text = ticker.lower()

    # generate candidate strings to match the ticker
    cands = {
        ticker_text,
        re.sub(r"[^a-z0-9]", "-", ticker_text),
        re.sub(r"[^a-z0-9]", "", ticker_text)
    }
    
    # filter out empty candidates
    cands = {c for c in cands if c}
    if not cands: return False

    # match candidates bounded by standard path/slug delimiters
    escaped_cands = "|".join(re.escape(cand) for cand in sorted(cands, key=len, reverse=True))
    pattern = re.compile(TICKER_BOUNDARY_PATTERN_FORMAT.format(escaped_cands))


    match = pattern.search(path)
    if not match: return False

    quarter_match = QUARTER_YEAR_PATTERN.search(path)
    if not quarter_match: return False

    return match.start(1) < quarter_match.start()
# ---

# QUARTER & YEAR FILTERING
def extract_quarter_and_year(url):
    if not url: return None, None

    match = QUARTER_YEAR_PATTERN.search(url)
    if not match: return None, None

    return f"Q{match.group('quarter')}", int(match.group('year'))

def url_matches_quarter(url: str, quarter) -> bool:
    normalized_quarter = _normalize_quarter(quarter)
    if normalized_quarter is None: return True

    url_quarter, _ = extract_quarter_and_year(url)
    return url_quarter == normalized_quarter

def url_matches_year(url: str, year) -> bool:
    if year is None: return True

    _, url_year = extract_quarter_and_year(url)
    return url_year == int(year)
# ---

# gets the most recent earning call transcript url and the date it occurred
def get_transcript_url(ticker, quarter=None, year=None):
    """Query SerpAPI for transcript URLs related to the ticker.

    Uses a session with retries and an environment-configurable timeout to make the lookup resilient.
    """
    params = serp_client.build_serp_params(ticker, quarter=quarter, year=year)

    try:
        data = serp_client.query_serp(params)
    except Exception as exc:
        logger.exception("SerpAPI request failed for %s", ticker)
        raise RuntimeError(f"Error querying SerpAPI: {type(exc).__name__}: {exc}") from exc

    urls = serp_client.extract_urls_from_serp_data(data, domain="fool.com")
    logger.debug("SerpAPI returned %d candidate URLs for %s", len(urls), ticker)
    
    # get the best match url
    selected_url = get_relevant_url(urls, ticker=ticker, quarter=quarter, year=year)
    
    if not selected_url:
        return TranscriptURLData(
            url=None,
            date="",
            financial_quarter=None,
            financial_year=None,
        )
    
    # get the date, quarter and year from that url
    date_tuple = extract_date(selected_url)
    financial_quarter, financial_year = extract_quarter_and_year(selected_url)
    
    return TranscriptURLData(
        url=selected_url,
        date=format_date(date_tuple),
        financial_quarter=financial_quarter,
        financial_year=financial_year,
    )


# takes in a list of urls
def get_relevant_url(urls, ticker=None, quarter=None, year=None):
    if not urls: return None

    matching_urls = []
    for url_item in urls:
        if isinstance(url_item, tuple):
            url, date_tuple = url_item
        else:
            url = url_item
            date_tuple = extract_date(url)

        if ticker and not url_matches_ticker(url, ticker):
            continue
        if not url_matches_quarter(url, quarter):
            continue
        if not url_matches_year(url, year):
            continue

        matching_urls.append((url, date_tuple))

    if not matching_urls: return None

    return max(matching_urls, key=lambda item: item[1] or (0, 0, 0))[0]