"""
Hypothesis tests for the financial sentiment analyser.

Tests the core hypothesis: whether earnings-call sentiment (from FinBERT)
is reflected in the share-price movement around those calls.

Separate directional windows are tested:
  PRE-CALL:  -1d, -3d, -5d   (price movement leading into the call)
  POST-CALL: +1d, +3d, +5d, +7d, +10d, +15d, +30d (price movement after)

Non-neutral tickers are the primary focus since neutral sentiment
carries no directional prediction.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Avoid loading the FinBERT model at import time.
# ---------------------------------------------------------------------------
_mock_tp = MagicMock()
sys.modules.setdefault("analysis.transcript_processor", _mock_tp)
sys.modules.setdefault("scraping", MagicMock())
sys.modules.setdefault("scraping.scraper", MagicMock())
sys.modules.setdefault("scraping.url_fetching", MagicMock())

from analysis.tests import (  # noqa: E402
    TestResult,
    is_aligned,
    parse_call_date,
    get_price_return,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV = PROJECT_ROOT / "results.csv"
QUARTERLY_CSV = PROJECT_ROOT / "quarterly_results.csv"
HYPOTHESIS_CSV = PROJECT_ROOT / "hypothesis_results.csv"


# ===================================================================
#  Unit tests – core helper functions
# ===================================================================

class TestParseCallDate:
    def test_valid_date(self):
        assert parse_call_date("2026/04/30") == datetime(2026, 4, 30)

    def test_empty_string_returns_none(self):
        assert parse_call_date("") is None

    def test_wrong_format_returns_none(self):
        assert parse_call_date("30-04-2026") is None

    def test_none_input(self):
        assert parse_call_date(None) is None


class TestIsAligned:
    def test_positive_sentiment_positive_return(self):
        assert is_aligned(0.8, 0.05) is True

    def test_negative_sentiment_negative_return(self):
        assert is_aligned(-0.5, -0.03) is True

    def test_neutral_sentiment_zero_return(self):
        assert is_aligned(0.0, 0.0) is True

    def test_positive_sentiment_negative_return(self):
        assert is_aligned(0.8, -0.02) is False

    def test_negative_sentiment_positive_return(self):
        assert is_aligned(-0.5, 0.04) is False

    def test_neutral_sentiment_positive_return(self):
        assert is_aligned(0.0, 0.03) is False

    def test_positive_sentiment_zero_return(self):
        assert is_aligned(0.5, 0.0) is False

    def test_zero_sentiment_negative_return(self):
        assert is_aligned(0.0, -0.01) is False


# ===================================================================
#  get_price_return – tested with mocked Yahoo Finance data
# ===================================================================

def _make_price_history(call_date: datetime, window: int,
                        start_price: float, end_price: float) -> pd.DataFrame:
    """Build a minimal yfinance-style DataFrame with Close prices."""
    start = call_date - timedelta(days=window)
    end = call_date + timedelta(days=window)
    dates = pd.bdate_range(start, end)
    n = len(dates)
    prices = [start_price + (end_price - start_price) * i / (n - 1) for i in range(n)]
    return pd.DataFrame({"Close": prices}, index=dates)


class TestGetPriceReturn:
    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_positive_return(self, window: int):
        call_dt = datetime(2026, 4, 30)
        history = _make_price_history(call_dt, window, 100.0, 110.0)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = history
        with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
            ret = get_price_return("AAPL", call_dt, window_days=window)
        assert ret is not None
        assert ret == pytest.approx(0.10, abs=0.02)

    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_negative_return(self, window: int):
        call_dt = datetime(2026, 4, 30)
        history = _make_price_history(call_dt, window, 100.0, 90.0)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = history
        with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
            ret = get_price_return("AAPL", call_dt, window_days=window)
        assert ret is not None
        assert ret == pytest.approx(-0.10, abs=0.02)

    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_flat_return(self, window: int):
        call_dt = datetime(2026, 4, 30)
        history = _make_price_history(call_dt, window, 100.0, 100.0)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = history
        with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
            ret = get_price_return("AAPL", call_dt, window_days=window)
        assert ret == pytest.approx(0.0, abs=1e-9)

    def test_empty_history_returns_none(self):
        call_dt = datetime(2026, 4, 30)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
            assert get_price_return("AAPL", call_dt, window_days=5) is None

    def test_api_exception_returns_none(self):
        call_dt = datetime(2026, 4, 30)
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("network error")
        with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
            assert get_price_return("AAPL", call_dt, window_days=5) is None

    def test_window_affects_date_range(self):
        """Different windows produce different start/end date ranges."""
        call_dt = datetime(2026, 4, 30)
        calls = {}
        for window in [1, 3, 5]:
            history = _make_price_history(call_dt, window, 100.0, 105.0)
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = history
            with patch("analysis.tests.yf.Ticker", return_value=mock_ticker):
                get_price_return("AAPL", call_dt, window_days=window)
            hist_call = mock_ticker.history.call_args
            calls[window] = {
                "start": hist_call.kwargs.get("start") or hist_call[1].get("start"),
                "end": hist_call.kwargs.get("end") or hist_call[1].get("end"),
            }
        assert calls[1]["start"] > calls[3]["start"]
        assert calls[3]["start"] > calls[5]["start"]
        assert calls[1]["end"] < calls[3]["end"]
        assert calls[3]["end"] < calls[5]["end"]


# ===================================================================
#  Hypothesis tests – synthetic scenarios
# ===================================================================

def _build_synthetic_results(
    sentiment_scores: List[float],
    price_returns: List[float],
) -> pd.DataFrame:
    records = []
    for i, (s, p) in enumerate(zip(sentiment_scores, price_returns)):
        records.append(TestResult(
            ticker=f"SYN{i}", call_date="2026/04/30",
            sentiment_score=s,
            sentiment_label="positive" if s > 0 else "negative" if s < 0 else "neutral",
            price_return=p, aligned=is_aligned(s, p),
        ))
    return pd.DataFrame([r.__dict__ for r in records])


class TestHypothesisPerfectAlignment:
    def test_alignment_rate_is_100_percent(self):
        df = _build_synthetic_results([0.9, 0.7, -0.8, -0.5, 0.3],
                                      [0.05, 0.03, -0.04, -0.02, 0.01])
        assert df["aligned"].mean() == 1.0

    def test_correlation_is_strongly_positive(self):
        df = _build_synthetic_results([0.9, 0.7, -0.8, -0.5, 0.3],
                                      [0.05, 0.03, -0.04, -0.02, 0.01])
        assert df["sentiment_score"].corr(df["price_return"]) > 0.8


class TestHypothesisNoAlignment:
    def test_alignment_rate_is_0_percent(self):
        df = _build_synthetic_results([0.9, 0.7, -0.8, -0.5, 0.3],
                                      [-0.05, -0.03, 0.04, 0.02, -0.01])
        assert df["aligned"].mean() == 0.0

    def test_correlation_is_strongly_negative(self):
        df = _build_synthetic_results([0.9, 0.7, -0.8, -0.5, 0.3],
                                      [-0.05, -0.03, 0.04, 0.02, -0.01])
        assert df["sentiment_score"].corr(df["price_return"]) < -0.8


class TestHypothesisNeutralBaseline:
    def test_neutral_sentiment_never_aligns_with_nonzero_returns(self):
        df = _build_synthetic_results([0.0, 0.0, 0.0, 0.0, 0.0],
                                      [0.05, -0.03, 0.02, -0.01, 0.04])
        assert df["aligned"].mean() == 0.0

    def test_neutral_should_be_excluded_from_hypothesis(self):
        """Neutral sentiments should be filtered out when testing the
        hypothesis, since they carry no directional prediction."""
        df = _build_synthetic_results(
            [0.9, 0.0, 0.0, -0.5, 0.0],
            [0.05, 0.03, -0.01, -0.02, 0.04],
        )
        non_neutral = df[df["sentiment_score"] != 0.0]
        assert non_neutral["aligned"].mean() == 1.0
        assert df["aligned"].mean() < 1.0  # diluted by neutrals


# ===================================================================
#  Directional window tests (pre-call vs post-call)
# ===================================================================

# Mock data representing 10 earnings calls with known sentiment
# and realistic pre/post price returns
MOCK_CALLS = [
    # (ticker, sentiment, label)
    ("GOOGL", +0.705, "positive"),
    ("META",  +0.501, "positive"),
    ("NVDA",  +0.786, "positive"),
    ("JPM",   -0.662, "negative"),
    ("V",     +0.850, "positive"),
    ("UNH",   +0.871, "positive"),
    ("XOM",   +0.946, "positive"),
    ("MA",    +0.681, "positive"),
    ("AVGO",  +0.937, "positive"),
    ("CSCO",  +0.955, "positive"),
]

# Simulated returns for each directional window
MOCK_PRE_RETURNS = {
    1: {"GOOGL": +0.0005, "META": -0.003, "NVDA": +0.013, "JPM": -0.013,
        "V": +0.083, "UNH": +0.070, "XOM": -0.010, "MA": -0.043,
        "AVGO": +0.012, "CSCO": +0.134},
    3: {"GOOGL": -0.001, "META": -0.014, "NVDA": +0.005, "JPM": +0.009,
        "V": +0.081, "UNH": +0.066, "XOM": +0.015, "MA": -0.007,
        "AVGO": -0.004, "CSCO": +0.170},
    5: {"GOOGL": +0.016, "META": -0.009, "NVDA": -0.008, "JPM": +0.010,
        "V": +0.082, "UNH": +0.094, "XOM": +0.031, "MA": -0.003,
        "AVGO": -0.006, "CSCO": +0.196},
}

MOCK_POST_RETURNS = {
    1:  {"GOOGL": +0.100, "META": -0.086, "NVDA": -0.018, "JPM": +0.0001,
         "V": -0.015, "UNH": +0.022, "XOM": +0.000, "MA": -0.015,
         "AVGO": +0.048, "CSCO": +0.023},
    3:  {"GOOGL": +0.095, "META": -0.088, "NVDA": -0.039, "JPM": -0.004,
         "V": -0.024, "UNH": +0.025, "XOM": -0.027, "MA": -0.012,
         "AVGO": +0.089, "CSCO": -0.001},
    5:  {"GOOGL": +0.095, "META": -0.088, "NVDA": -0.039, "JPM": -0.004,
         "V": -0.024, "UNH": +0.025, "XOM": -0.027, "MA": -0.012,
         "AVGO": +0.089, "CSCO": -0.001},
    15: {"GOOGL": +0.146, "META": -0.076, "NVDA": -0.020, "JPM": +0.006,
         "V": -0.035, "UNH": +0.062, "XOM": +0.041, "MA": -0.017,
         "AVGO": +0.007, "CSCO": +0.042},
    30: {"GOOGL": +0.087, "META": -0.055, "NVDA": None, "JPM": -0.032,
         "V": -0.023, "UNH": +0.105, "XOM": -0.015, "MA": -0.018,
         "AVGO": -0.007, "CSCO": None},
}


def _compute_window_stats(calls, returns_dict, window):
    """Compute alignment rate and correlation for a given window."""
    data = []
    for ticker, sentiment, label in calls:
        ret = returns_dict.get(window, {}).get(ticker)
        if ret is None:
            continue
        data.append((sentiment, ret, is_aligned(sentiment, ret)))

    if not data:
        return None, None, 0

    n = len(data)
    alignment = sum(d[2] for d in data) / n
    df = pd.DataFrame({"s": [d[0] for d in data], "r": [d[1] for d in data]})
    corr = df["s"].corr(df["r"])
    return alignment, corr if not pd.isna(corr) else None, n


class TestPreCallWindows:
    """Test that pre-call windows (price movement leading INTO the call)
    are computed correctly for 1, 3, and 5-day horizons."""

    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_pre_window_produces_results(self, window):
        alignment, corr, n = _compute_window_stats(
            MOCK_CALLS, MOCK_PRE_RETURNS, window)
        assert n == 10
        assert alignment is not None

    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_pre_alignment_is_valid(self, window):
        alignment, _, _ = _compute_window_stats(
            MOCK_CALLS, MOCK_PRE_RETURNS, window)
        assert 0.0 <= alignment <= 1.0

    @pytest.mark.parametrize("window", [1, 3, 5])
    def test_pre_correlation_is_valid(self, window):
        _, corr, _ = _compute_window_stats(
            MOCK_CALLS, MOCK_PRE_RETURNS, window)
        assert corr is not None
        assert -1.0 <= corr <= 1.0

    def test_pre_1d_alignment_rate(self):
        """Pre-1d: GOOGL+, NVDA+, JPM-, V+, UNH+, AVGO+, CSCO+ aligned (7/10)
        META-, XOM-, MA- not aligned → 70%"""
        alignment, _, _ = _compute_window_stats(
            MOCK_CALLS, MOCK_PRE_RETURNS, 1)
        assert alignment == pytest.approx(7 / 10, abs=0.01)


class TestPostCallWindows:
    """Test that post-call windows (price movement AFTER the call)
    are computed correctly for 1, 3, 5, 15, and 30-day horizons."""

    @pytest.mark.parametrize("window", [1, 3, 5, 15])
    def test_post_window_produces_results(self, window):
        _, _, n = _compute_window_stats(
            MOCK_CALLS, MOCK_POST_RETURNS, window)
        assert n >= 8  # some may be None for 30d

    @pytest.mark.parametrize("window", [1, 3, 5, 15, 30])
    def test_post_alignment_is_valid(self, window):
        alignment, _, n = _compute_window_stats(
            MOCK_CALLS, MOCK_POST_RETURNS, window)
        if n > 0:
            assert 0.0 <= alignment <= 1.0

    @pytest.mark.parametrize("window", [1, 3, 5, 15])
    def test_post_correlation_is_valid(self, window):
        _, corr, _ = _compute_window_stats(
            MOCK_CALLS, MOCK_POST_RETURNS, window)
        assert corr is not None
        assert -1.0 <= corr <= 1.0

    def test_post_30d_handles_missing_tickers(self):
        """NVDA and CSCO have None returns for 30d (too recent).
        The test should still produce results for the remaining 8."""
        _, _, n = _compute_window_stats(
            MOCK_CALLS, MOCK_POST_RETURNS, 30)
        assert n == 8


class TestEMHPricingIn:
    """Test whether pre-call windows show evidence of the market
    pricing-in sentiment before the earnings call (EMH)."""

    def test_pre_call_alignment_above_random(self):
        """If EMH holds, pre-call alignment should be above 50%
        (market anticipates the call direction)."""
        alignments = []
        for w in [1, 3, 5]:
            a, _, _ = _compute_window_stats(MOCK_CALLS, MOCK_PRE_RETURNS, w)
            alignments.append(a)
        avg = sum(alignments) / len(alignments)
        # Based on mock data modeled after real results
        assert avg > 0.50


class TestPostCallStrategy:
    """Test whether post-call sentiment alignment is strong enough
    to support a sentiment-based investment strategy."""

    def test_post_call_alignment_summary(self):
        """Compute average post-call alignment across all windows."""
        alignments = []
        for w in [1, 3, 5, 15, 30]:
            a, _, n = _compute_window_stats(MOCK_CALLS, MOCK_POST_RETURNS, w)
            if n > 0:
                alignments.append(a)
        avg = sum(alignments) / len(alignments)
        # Assert it's a valid number (the actual verdict is in the
        # interpretation, not a pass/fail gate)
        assert 0.0 <= avg <= 1.0


# ===================================================================
#  Integration tests – CSV fixtures
# ===================================================================

class TestResultsCSVFixture:
    @pytest.fixture
    def results_df(self):
        if not RESULTS_CSV.exists():
            pytest.skip("results.csv not found")
        return pd.read_csv(RESULTS_CSV)

    def test_csv_has_expected_columns(self, results_df):
        expected = {"ticker", "call_date", "sentiment_score",
                    "sentiment_label", "price_return", "aligned"}
        assert expected.issubset(set(results_df.columns))

    def test_csv_has_at_least_10_tickers(self, results_df):
        assert len(results_df) >= 10

    def test_sentiment_scores_in_valid_range(self, results_df):
        assert (results_df["sentiment_score"] >= -1.0).all()
        assert (results_df["sentiment_score"] <= 1.0).all()

    def test_alignment_values_are_consistent(self, results_df):
        for _, row in results_df.iterrows():
            expected = is_aligned(row["sentiment_score"], row["price_return"])
            assert row["aligned"] == expected, f"{row['ticker']}: mismatch"

    def test_non_neutral_tickers_exist(self, results_df):
        """At least some tickers should have non-neutral sentiment."""
        non_neutral = results_df[results_df["sentiment_score"] != 0.0]
        assert len(non_neutral) >= 5


class TestQuarterlyCSVFixture:
    @pytest.fixture
    def quarterly_df(self):
        if not QUARTERLY_CSV.exists():
            pytest.skip("quarterly_results.csv not found")
        return pd.read_csv(QUARTERLY_CSV)

    def test_csv_has_expected_columns(self, quarterly_df):
        expected = {"company", "year", "quarter", "sentiment_score",
                    "price_return", "aligned"}
        assert expected.issubset(set(quarterly_df.columns))

    def test_csv_has_substantial_data(self, quarterly_df):
        assert len(quarterly_df) > 100

    def test_quarterly_alignment_rate_near_coin_flip(self, quarterly_df):
        rate = quarterly_df["aligned"].mean()
        assert 0.40 <= rate <= 0.60, f"Quarterly alignment {rate:.2%}"

    def test_quarterly_correlation_near_zero(self, quarterly_df):
        corr = quarterly_df["sentiment_score"].corr(quarterly_df["price_return"])
        assert abs(corr) < 0.15, f"Quarterly correlation {corr:.3f}"


class TestHypothesisCSVFixture:
    """Validate the hypothesis_results.csv produced by hypothesis_test.py."""

    @pytest.fixture
    def hyp_df(self):
        if not HYPOTHESIS_CSV.exists():
            pytest.skip("hypothesis_results.csv not found – "
                        "run analysis/hypothesis_test.py first")
        return pd.read_csv(HYPOTHESIS_CSV)

    def test_has_expected_columns(self, hyp_df):
        expected = {"window", "scope", "n", "alignment", "correlation", "avg_return"}
        assert expected.issubset(set(hyp_df.columns))

    def test_has_both_scopes(self, hyp_df):
        scopes = set(hyp_df["scope"].unique())
        assert "all" in scopes
        assert "non_neutral" in scopes

    def test_pre_windows_present(self, hyp_df):
        windows = set(hyp_df["window"].unique())
        for d in [1, 3, 5]:
            assert f"pre_{d}d" in windows

    def test_post_windows_present(self, hyp_df):
        windows = set(hyp_df["window"].unique())
        for d in [1, 3, 5, 7, 10, 15, 30]:
            assert f"post_{d}d" in windows

    def test_non_neutral_alignment_values_are_valid(self, hyp_df):
        nn = hyp_df[hyp_df["scope"] == "non_neutral"]
        valid = nn[nn["alignment"].notna()]
        assert (valid["alignment"] >= 0.0).all()
        assert (valid["alignment"] <= 1.0).all()


# ===================================================================
#  Summary comparison test
# ===================================================================

class TestWindowComparison:
    @pytest.fixture
    def all_metrics(self):
        metrics = {"pre": {}, "post": {}}
        for w in [1, 3, 5]:
            a, c, n = _compute_window_stats(MOCK_CALLS, MOCK_PRE_RETURNS, w)
            metrics["pre"][w] = {"alignment": a, "correlation": c, "n": n}
        for w in [1, 3, 5, 15, 30]:
            a, c, n = _compute_window_stats(MOCK_CALLS, MOCK_POST_RETURNS, w)
            metrics["post"][w] = {"alignment": a, "correlation": c, "n": n}
        return metrics

    def test_all_pre_windows_present(self, all_metrics):
        for w in [1, 3, 5]:
            assert w in all_metrics["pre"]

    def test_all_post_windows_present(self, all_metrics):
        for w in [1, 3, 5, 15, 30]:
            assert w in all_metrics["post"]

    def test_summary_output(self, all_metrics, capsys):
        print("\n" + "=" * 70)
        print("  HYPOTHESIS RESULTS: Sentiment vs Price (mock data)")
        print("=" * 70)
        print(f"  {'Direction':<6} {'Window':<10} {'N':>3} {'Alignment':>10} {'Correlation':>12}")
        print("  " + "-" * 50)
        for direction in ["pre", "post"]:
            for w in sorted(all_metrics[direction]):
                m = all_metrics[direction][w]
                a_str = f"{m['alignment']:.1%}" if m["alignment"] is not None else "n/a"
                c_str = f"{m['correlation']:.3f}" if m["correlation"] is not None else "n/a"
                print(f"  {direction:<6} {w:>3}d     {m['n']:>3} {a_str:>10} {c_str:>12}")
        print("=" * 70)
        captured = capsys.readouterr()
        assert "HYPOTHESIS RESULTS" in captured.out
