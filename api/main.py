from fastapi import FastAPI
from api.exception_handlers import (
    register_exception_handlers,
)
from api.transcript_service import TranscriptService
from api.caching_service import CacheService
from models import EarningsCall, AnalyseRequest, EarningCallRequest
import logging


logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
register_exception_handlers(app)

# -- SHARED LOGIC --
def get_earnings_call(ticker: str, quarter: int | None, year: int | None) -> EarningsCall:
    transcript_service = TranscriptService()
    cache_service = CacheService()
    
    # 1. check the cache
    earnings_call = cache_service.get(ticker=ticker, year=year, quarter=quarter)
    
    # 2. scrape, calculate and cache
    if earnings_call is None:
        earnings_call = transcript_service.get_earnings_call(
            ticker=ticker,
            quarter=quarter,
            year=year
        )
        cache_service.store(earnings_call)
        
    return earnings_call


@app.post("/earnings-call", 
          summary="Return the transcript object",
          response_model=EarningsCall,
          )
def scrape_motley_fool(request: EarningCallRequest):
    return get_earnings_call(request.ticker, request.quarter, request.year)