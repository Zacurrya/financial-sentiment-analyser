import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def build_serp_params(ticker, quarter=None, year=None, site="fool.com", num=5):

    search_terms = [ticker, "earnings call transcript"]
    if quarter: search_terms.append(str(quarter).strip().lower())
    if year: search_terms.append(str(year))

    api_key = os.getenv("SERPAPI_KEY")
    if not api_key: 
        logger.debug("SERPAPI_KEY not set when building params")

    return {
        "engine": "google",
        "q": f"site:{site} {' '.join(search_terms)}",
        "api_key": api_key,
        "num": num,
    }


def get_serp_session(retries_total=3, backoff_factor=0.5):
    session = requests.Session()
    retries = Retry(total=retries_total, backoff_factor=backoff_factor,
                    status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def query_serp(params, timeout=None):
    timeout = timeout or int(os.getenv("SERPAPI_TIMEOUT", "10"))
    session = get_serp_session()
    try:
        logger.debug("Querying SerpAPI with params %s", params)
        resp = session.get("https://serpapi.com/search", params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.exception("SerpAPI request failed")
        raise


def extract_urls_from_serp_data(data, domain="fool.com"):
    urls = []
    for item in data.get("organic_results", []):
        url = item.get("link")
        if url and domain in url:
            urls.append(url)
    return urls
