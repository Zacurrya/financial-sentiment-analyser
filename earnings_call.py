from pydantic import BaseModel
from typing import Optional

class EarningsCall(BaseModel):
    ticker: str
    financial_quarter: Optional[str] = None
    financial_year: Optional[int] = None
    date: str
    summary: str
    takeaways: list[str]
    risks: list[str]
    transcript: str
    sentiment_score: Optional[float] = None
    label: Optional[str] = None