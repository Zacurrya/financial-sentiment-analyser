from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class EarningsCall(BaseModel):
    model_config = {"extra": "ignore"}
    
    ticker: str
    financial_quarter: int
    financial_year: int
    date: str
    summary: str
    takeaways: List[str]
    risks: List[str]
    transcript: str
    sentiment_score: float
    label: str


class TranscriptOnly(BaseModel):
    """Lightweight response that excludes sentiment analysis fields.
    Use this when you want to avoid loading the FinBERT model."""
    model_config = {"extra": "ignore"}

    ticker: str
    financial_quarter: int
    financial_year: int
    date: str
    summary: str
    takeaways: List[str]
    risks: List[str]
    transcript: str


class SerpUrl(BaseModel):
    url: str
    rank: Optional[int] = None


class SerpAPIResponse(BaseModel):
    query: str
    total_results: Optional[int] = None
    took_ms: Optional[int] = None
    # Only keep the fields we need (URLs and optional rank)
    organic_results: Optional[List[SerpUrl]] = None
    ads: Optional[List[Dict]] = None
    serp_provider: Optional[str] = None


class TranscriptURLData(BaseModel):
    url: Optional[str] = None
    date: str = ""
    financial_quarter: Optional[int] = None
    financial_year: Optional[int] = None


class ExtractTranscriptResult(BaseModel):
    summary: str = ""
    takeaways: List[str] = []
    risks: List[str] = []
    transcript: str = ""


class AnalyseRequest(BaseModel):
    ticker: str
    quarter: Optional[int] = Field(None, ge=1, le=4)
    year: Optional[int] = None


class EarningCallRequest(BaseModel):
    ticker: str
    quarter: Optional[int] = Field(None, ge=1, le=4)
    year: Optional[int] = None
