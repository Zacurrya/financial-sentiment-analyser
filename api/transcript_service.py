import logging

from scraping.scraper import extract_transcript, scrape_site
from scraping.url_fetching import get_transcript_url
from models import EarningsCall, TranscriptOnly
from analysis.transcript_processor import get_sentiment_score

logger = logging.getLogger(__name__)


class TranscriptService:
    def get_earnings_call(self, ticker: str, quarter: int | None = None, year: int | None = None) -> EarningsCall:

        # get transcript URL metadata
        try:
            logger.debug("get_earnings_call: fetching URL data for %s quarter=%s year=%s", ticker, quarter, year)
            transcript_url_data = get_transcript_url(ticker, quarter=quarter, year=year)
            logger.debug("get_earnings_call: url data: %s", transcript_url_data)
        except Exception as e:
            logger.exception("get_earnings_call: failed to fetch transcript URL data for %s", ticker)
            raise RuntimeError(f"Error fetching transcript URL data: {type(e).__name__}: {e}") from e

        if not transcript_url_data.url:
            logger.warning("get_earnings_call: no relevant transcript URL for %s quarter=%s year=%s", ticker, quarter, year)
            raise RuntimeError(f"No earnings call transcript found for ticker {ticker}")
        
        # scrape transcript
        try:
            logger.debug("get_earnings_call: scraping URL %s", transcript_url_data.url)
            soup = scrape_site(transcript_url_data.url)
            data = extract_transcript(soup)

            call_date = transcript_url_data.date
            logger.debug("get_earnings_call: scraped date=%s transcript_len=%d", call_date, len(data.transcript or ""))
        except Exception as e:
            logger.exception("get_earnings_call: failed scraping %s", transcript_url_data.url)
            raise RuntimeError(f"Error scraping transcript: {type(e).__name__}: {e}") from e
            
        # assemble result
        if not data.transcript:
            raise RuntimeError(f"Scraped transcript is empty for ticker {ticker}")

        # analyse earning call sentiment
        try:
            score = get_sentiment_score(data.transcript)
            label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
        except Exception as e:
            raise RuntimeError(f"Error analysing transcript sentiment: {type(e).__name__}: {e}") from e

        fq = transcript_url_data.financial_quarter or quarter
        fy = transcript_url_data.financial_year or year
        if fq is None or fy is None:
            raise RuntimeError(f"Could not determine financial quarter and year for {ticker}")

        # assemble and return
        return EarningsCall(
            ticker=ticker,
            financial_quarter=fq,
            financial_year=fy,
            date=call_date or "",
            **data.model_dump(),
            sentiment_score=score,
            label=label,
        )
