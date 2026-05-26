from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

import pandas as pd
import yfinance as yf

from api.transcript_service import TranscriptService


TEST_TICKERS = [
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    "JPM",
    "JNJ",
    "V",
    "UNH",
    "HD",
    "PG",
    "XOM",
    "MA",
    "AVGO",
    "COST",
    "DIS",
    "PEP",
    "CSCO",
]


@dataclass
class TestResult:
    ticker: str
    call_date: str
    sentiment_score: float
    sentiment_label: str
    price_return: float
    aligned: bool


def parse_call_date(call_date: str) -> Optional[datetime]:
    if not call_date:
        return None
    try:
        return datetime.strptime(call_date, "%Y/%m/%d")
    except ValueError:
        return None


def get_price_return(ticker: str, call_date: datetime, window_days: int = 5) -> Optional[float]:
    start = call_date - timedelta(days=window_days)
    end = call_date + timedelta(days=window_days)

    try:
        data = yf.Ticker(ticker).history(start=start, end=end)
    except Exception:
        return None

    if data is None or data.empty:
        return None

    start_price = data.iloc[0]["Close"]
    end_price = data.iloc[-1]["Close"]
    return (end_price - start_price) / start_price


def is_aligned(sentiment_score: float, price_return: float) -> bool:
    if sentiment_score > 0 and price_return > 0:
        return True
    if sentiment_score < 0 and price_return < 0:
        return True
    if sentiment_score == 0 and price_return == 0:
        return True
    return False


def build_results(tickers: Iterable[str]) -> list[TestResult]:
    service = TranscriptService()
    results: list[TestResult] = []

    for ticker in tickers:
        earnings_call = service.get_earnings_call(ticker, quarter=None)
        call_dt = parse_call_date(earnings_call.date)
        if call_dt is None or earnings_call.sentiment_score is None or earnings_call.label is None:
            continue

        price_return = get_price_return(ticker, call_dt)
        if price_return is None:
            continue

        aligned = is_aligned(earnings_call.sentiment_score, price_return)
        results.append(
            TestResult(
                ticker=ticker,
                call_date=earnings_call.date,
                sentiment_score=earnings_call.sentiment_score,
                sentiment_label=earnings_call.label,
                price_return=price_return,
                aligned=aligned,
            )
        )

    return results


def main() -> None:
    results = build_results(TEST_TICKERS)
    if not results:
        print("No results collected.")
        return

    df = pd.DataFrame([result.__dict__ for result in results])
    df.to_csv("results.csv", index=False)

    alignment_rate = df["aligned"].mean()
    correlation = df["sentiment_score"].corr(df["price_return"])

    print(f"Alignment rate: {alignment_rate:.2%}")
    if pd.isna(correlation):
        print("Correlation: unavailable (insufficient data)")
    else:
        print(f"Correlation: {correlation:.2f}")


if __name__ == "__main__":
    main()
