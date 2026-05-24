from pydantic import BaseModel
from typing import Optional, List, Dict


class EarningsCall(BaseModel):
    ticker: str
    financial_quarter: Optional[str] = None
    financial_year: Optional[int] = None
    date: str
    summary: str
    takeaways: List[str]
    risks: List[str]
    transcript: str
    sentiment_score: Optional[float] = None
    label: Optional[str] = None


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
    financial_quarter: Optional[str] = None
    financial_year: Optional[int] = None


class ExtractTranscriptResult(BaseModel):
    summary: str = ""
    takeaways: List[str] = []
    risks: List[str] = []
    transcript: str = ""


class AnalyseRequest(BaseModel):
    ticker: str
    quarter: Optional[str] = None
    year: Optional[int] = None


class EarningCallRequest(BaseModel):
    ticker: str
    quarter: Optional[str] = None
    year: Optional[int] = None
