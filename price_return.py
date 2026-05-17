import yfinance as yf
from dotenv import load_dotenv
import requests
import os 
load_dotenv()

# TO DO
def get_earning_call_dates(ticker):
    earning_dates = requests.get(
        f'https://financialmodelingprep.com/stable/earnings?symbol=AAPL&apikey={os.getenv("FMP_TOKEN")}', 
        params={'symbol' == ticker}
        )
    

# gets the price return (as a percentage) of a stock over a single quarter
def get_price_return(ticker, year, quarter):
    quarter_dates = {
        "Q1": (f"{year}-04-01", f"{year}-06-30"),
        "Q2": (f"{year}-07-01", f"{year}-09-30"),
        "Q3": (f"{year}-10-01", f"{year}-12-31"),
        "Q4": (f"{year}-01-01", f"{int(year)+1}-03-31"),
    }
    start, end = quarter_dates[quarter] 

    ticker = yf.Ticker(ticker)
    
    try:
        data = ticker.history(start=start, end=end)
    except Exception:
        return None
    
    # No price data for
    if data is None: return None

    start_price, end_price = data.iloc[0]["Close"], data.iloc[-1]["Close"]
    
    return (end_price - start_price) / start_price
