import sys
from pathlib import Path
import logging
logger = logging.getLogger("uvicorn.error")

sys.path.append(str(Path(__file__).parent.parent))
from db import supabase
from models import EarningsCall
from typing import cast
class CacheService:
    def get(self, ticker: str, year: int | None, quarter: int | None) -> EarningsCall | None:
        if year is None and quarter is None:
            return self.get_most_recent_earnings_call(ticker)

        if year is None or quarter is None:
            return None
            
        result = supabase.table("earnings_calls")\
            .select("*")\
            .eq("ticker", ticker)\
            .eq("financial_year", year)\
            .eq("financial_quarter", quarter)\
            .execute()
            
        if result.data:
            logger.info("cache hit: ticker=%s year=%s quarter=%s", ticker, year, quarter)
            return EarningsCall(**cast(dict, result.data[0]))
        else:
            logger.info("cache miss: ticker=%s year=%s quarter=%s", ticker, year, quarter)
            return None
    
    
    def get_most_recent_earnings_call(self, ticker: str) -> EarningsCall | None:
        result = supabase.table("earnings_calls")\
            .select("*")\
            .eq("ticker", ticker)\
            .order("financial_year", desc=True)\
            .order("financial_quarter", desc=True)\
            .limit(1)\
            .execute()
            
        if result.data:
            # most-recent call is a cache hit for the ticker
            logger.info("cache hit (most recent earnings): ticker=%s", ticker)
            return EarningsCall(**cast(dict, result.data[0]))
        else:
            logger.info("cache miss (most recent earnings): ticker=%s", ticker)
            return None
    
    
    def store(self, earnings_call: EarningsCall):
        supabase.table("earnings_calls").insert(earnings_call.model_dump()).execute()
    
    