from __future__ import annotations

import sys
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

sys.modules.setdefault("analysis.transcript_processor", MagicMock())
sys.modules.setdefault("scraping", MagicMock())
sys.modules.setdefault("scraping.scraper", MagicMock())
sys.modules.setdefault("scraping.url_fetching", MagicMock())

from api.main import app
from models import EarningsCall


client = TestClient(app)


def test_earnings_call_endpoint_returns_earnings_call(monkeypatch):
    expected = EarningsCall(
        ticker="AAPL",
        financial_quarter=1,
        financial_year=2026,
        date="2026-01-30",
        summary="Quarterly summary",
        takeaways=["Revenue growth"],
        risks=["Macro uncertainty"],
        transcript="Full transcript text",
        sentiment_score=0.42,
        label="positive",
    )

    monkeypatch.setattr("api.main.get_earnings_call", lambda ticker, quarter, year: expected)

    response = client.post(
        "/earnings-call",
        json={"ticker": "AAPL", "quarter": 1, "year": 2026},
    )

    assert response.status_code == 200
    assert response.json() == expected.model_dump()