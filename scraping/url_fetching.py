import os
import re
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

from constants import QUARTER_YEAR_PATTERN
from scraping import serp_client

load_dotenv()

logger = logging.getLogger(__name__)

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
    return get_transcript_url_data(urls, quarter=quarter, year=year)
    
# gets the most recent transcript out of a list of urls
def get_transcript_url_data(urls, quarter=None, year=None):
    dated_urls = []
    for url in urls:
        date_tuple = extract_date(url)
        if date_tuple:
            dated_urls.append((url, date_tuple))

    if quarter or year:
        normalized_quarter = _normalize_quarter(quarter)
        normalized_year = int(year) if year is not None else None
        filtered_urls = []

        for url, date_tuple in dated_urls:
            url_quarter, url_year = extract_quarter_and_year(url)
            if normalized_quarter and url_quarter != normalized_quarter:
                continue
            if normalized_year and url_year != normalized_year:
                continue
            filtered_urls.append((url, date_tuple))

        if filtered_urls:
            dated_urls = filtered_urls

    selected_url = get_relevant_url(dated_urls, quarter=quarter, year=year)
    if selected_url is None:
        return { "url": None, "date": "", "financial_quarter": None, "financial_year": None }

    date_tuple = next((date for url, date in dated_urls if url == selected_url), None)

    financial_quarter, financial_year = extract_quarter_and_year(selected_url)
    return {
        "url": selected_url,
        "date": format_date(date_tuple),
        "financial_quarter": financial_quarter,
        "financial_year": financial_year,
    }

# takes in a list of urls
# outputs the url which matches the quarter and year of the url
def get_relevant_url(urls, quarter=None, year=None):
    if not urls:
        return None

    normalized_quarter = _normalize_quarter(quarter)
    normalized_year = int(year) if year is not None else None

    matching_urls = []
    for url_item in urls:
        if isinstance(url_item, tuple):
            url, date_tuple = url_item
        else:
            url = url_item
            date_tuple = extract_date(url)

        url_quarter, url_year = extract_quarter_and_year(url)
        if normalized_quarter and url_quarter != normalized_quarter:
            continue
        if normalized_year and url_year != normalized_year:
            continue
        matching_urls.append((url, date_tuple))

    if not matching_urls:
        return None

    return max(matching_urls, key=lambda item: item[1] or (0, 0, 0))[0]


def extract_quarter_and_year(url):
    if not url:
        return None, None

    match = QUARTER_YEAR_PATTERN.search(url)
    if not match:
        return None, None

    return f"Q{match.group('quarter')}", int(match.group('year'))


def _normalize_quarter(value):
    if value is None:
        return None

    text = str(value).strip().upper()
    if not text:
        return None

    if text.startswith("Q"):
        text = text[1:]

    return f"Q{text}" if text in {"1", "2", "3", "4"} else None


def extract_date(url):
    path = urlparse(url).path.rstrip("/")
    match = re.search(r"/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/", path + "/")
    if not match:
        return None

    return int(match.group("year")), int(match.group("month")), int(match.group("day"))

def format_date(value):
    if not value:
        return ""
    year, month, day = value
    return f"{year:04d}/{month:02d}/{day:02d}"