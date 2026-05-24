from fastapi import FastAPI
from api.exception_handlers import (
    register_exception_handlers,
)
from api.transcript_service import TranscriptService
from models import EarningsCall, AnalyseRequest, EarningCallRequest
import logging


logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
register_exception_handlers(app)



# -- W/ SENTIMENT CALC --
@app.post("/analysed-earnings", 
          summary="Analyse an earnings call",
          description="Fetches the most recent earnings call transcript of a given ticker, as well as it's analysed sentiment",
          response_model=EarningsCall
          )
def analyse(request: AnalyseRequest):
    service = TranscriptService()
    return service.get_earnings_call(request.ticker, request.quarter, request.year)



# -- WITHOUT SENTIMENT CALCS --
@app.post("/earnings-call", 
          summary="Return the transcript object",
          response_model=EarningsCall,
          )
def scrape_motley_fool(request: EarningCallRequest):
    service = TranscriptService()
    return service.get_earnings_call(request.ticker, request.quarter, request.year, compute_sentiment=False)