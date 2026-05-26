from datetime import datetime, timedelta

import yfinance as yf

from api.transcript_service import TranscriptService


def get_earning_call_return(ticker, quarter=None, window_days=5):
    service = TranscriptService()
    earnings_call = service.get_earnings_call(ticker, quarter=quarter)
    if not earnings_call.date:
        return None

    try:
        call_date = datetime.strptime(earnings_call.date, "%Y/%m/%d")
    except ValueError:
        return None

    start = call_date - timedelta(days=window_days)
    end = call_date + timedelta(days=window_days)

    try:
        data = yf.Ticker(ticker).history(start=start, end=end)
    except Exception:
        return None

    if data is None or data.empty:
        return None

    start_price, end_price = data.iloc[0]["Close"], data.iloc[-1]["Close"]
    return (end_price - start_price) / start_price
