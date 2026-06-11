"""
Hypothesis test: Does earnings-call sentiment predict share price movement?

Tests directional price returns BEFORE and AFTER the earnings call date
across multiple time windows, then reports alignment rates and correlations.

Windows tested:
  PRE-CALL:  -1d, -3d, -5d        (price change leading into the call)
  POST-CALL: +1d, +3d, +5d, +7d, +10d, +15d, +30d  (price change after)

"Alignment" = sentiment direction matches price-return direction:
  - positive sentiment + positive return = aligned
  - negative sentiment + negative return = aligned
  - otherwise = not aligned

Neutral sentiments (score == 0) are excluded from the hypothesis test
since they carry no directional prediction.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# -- Configuration --
RESULTS_CSV = Path(__file__).resolve().parent.parent / "results.csv"

PRE_WINDOWS  = [1, 3, 5]                     # days before the call
POST_WINDOWS = [1, 3, 5, 7, 10, 15, 30]      # days after the call

MIN_AGE_BUFFER = 5  # extra buffer beyond the window for weekends/holidays

# -- Helpers --
def parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y/%m/%d")
    except (ValueError, TypeError):
        return None


def compute_return(start_price: float | None, end_price: float | None) -> float | None:
    if start_price is None or end_price is None or start_price == 0:
        return None
    return (end_price - start_price) / start_price


def is_aligned(sentiment: float, price_return: float) -> bool:
    if sentiment > 0 and price_return > 0:
        return True
    if sentiment < 0 and price_return < 0:
        return True
    if sentiment == 0 and price_return == 0:
        return True
    return False


def print_table(title: str, window_labels: list[str],
                results: dict[str, list[tuple[str, float, float, bool]]],
                filter_neutral: bool = False) -> list[dict]:
    """Print a formatted table and return summary data."""
    label_suffix = " (non-neutral only)" if filter_neutral else " (all tickers)"
    print(f"\n  {title}{label_suffix}")
    print("  " + "-" * 70)
    print(f"  {'Window':<14} {'N':>4}  {'Alignment':>10}  {'Correlation':>12}  {'Avg Return':>11}")
    print("  " + "-" * 70)

    summary = []
    for label in window_labels:
        data = results[label]
        if filter_neutral:
            data = [(t, s, r, a) for t, s, r, a in data if s != 0.0]

        n = len(data)
        if n == 0:
            print(f"  {label:<14} {0:>4}  {'n/a':>10}  {'n/a':>12}  {'n/a':>11}")
            summary.append({"window": label, "n": 0, "alignment": None,
                            "correlation": None, "avg_return": None})
            continue

        sentiments = [d[1] for d in data]
        returns = [d[2] for d in data]
        alignments = [d[3] for d in data]

        alignment_rate = sum(alignments) / n
        df_temp = pd.DataFrame({"s": sentiments, "r": returns})
        corr = df_temp["s"].corr(df_temp["r"])
        avg_ret = sum(returns) / n

        corr_str = f"{corr:.3f}" if not pd.isna(corr) else "n/a"
        print(f"  {label:<14} {n:>4}  {alignment_rate:>9.1%}  {corr_str:>12}  {avg_ret:>+10.2%}")

        summary.append({
            "window": label, "n": n,
            "alignment": alignment_rate,
            "correlation": corr if not pd.isna(corr) else None,
            "avg_return": avg_ret,
        })

    print("  " + "-" * 70)
    return summary


# -- Main Analysis --
def main() -> None:
    if not RESULTS_CSV.exists():
        print(f"ERROR: {RESULTS_CSV} not found. Run analysis/tests.py first.")
        sys.exit(1)

    rows = []
    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    today = datetime.now()

    window_labels = (
        [f"pre_{d}d" for d in PRE_WINDOWS]
        + [f"post_{d}d" for d in POST_WINDOWS]
    )

    # {window_label: [(ticker, sentiment, return, aligned), ...]}
    results: dict[str, list[tuple[str, float, float, bool]]] = {
        w: [] for w in window_labels
    }

    print("Fetching price data from Yahoo Finance...\n")

    for row in rows:
        ticker = row["ticker"]
        sentiment = float(row["sentiment_score"])
        sentiment_label = row["sentiment_label"]
        call_dt = parse_date(row["call_date"])
        if call_dt is None:
            continue

        days_since_call = (today - call_dt).days

        print(f"  {ticker:<6} call={row['call_date']}  "
              f"sentiment={sentiment:+.3f} ({sentiment_label:>8})  "
              f"age={days_since_call}d")

        yf_ticker = yf.Ticker(ticker)

        # Fetch wide history in one call
        history_start = call_dt - timedelta(days=max(PRE_WINDOWS) + 10)
        history_end = call_dt + timedelta(days=max(POST_WINDOWS) + 10)
        try:
            history = yf_ticker.history(start=history_start, end=history_end)
        except Exception as e:
            print(f"         ERROR: {e}")
            continue

        if history is None or history.empty:
            print(f"         No price data")
            continue

        history.index = history.index.tz_localize(None)

        def closest_price(target: datetime) -> float | None:
            """Find the closest trading day's close to target (within 5 days)."""
            if history.empty:
                return None
            idx = history.index
            for offset in range(6):
                for delta in ([0] if offset == 0 else [offset, -offset]):
                    check = target + timedelta(days=delta)
                    mask = ((idx.year == check.year)
                            & (idx.month == check.month)
                            & (idx.day == check.day))
                    if mask.any():
                        return float(history.loc[mask, "Close"].iloc[0])
            return None

        call_price = closest_price(call_dt)
        if call_price is None:
            print(f"         No price on call date")
            continue

        # PRE-CALL windows: return from N days before -> call date
        for d in PRE_WINDOWS:
            pre_price = closest_price(call_dt - timedelta(days=d))
            ret = compute_return(pre_price, call_price)
            if ret is not None:
                results[f"pre_{d}d"].append(
                    (ticker, sentiment, ret, is_aligned(sentiment, ret)))

        # POST-CALL windows: return from call date -> N days after
        for d in POST_WINDOWS:
            if days_since_call < d + MIN_AGE_BUFFER:
                continue
            post_price = closest_price(call_dt + timedelta(days=d))
            ret = compute_return(call_price, post_price)
            if ret is not None:
                results[f"post_{d}d"].append(
                    (ticker, sentiment, ret, is_aligned(sentiment, ret)))

    # -- Results --
    print("\n" + "=" * 78)
    print("  HYPOTHESIS TEST: Earnings-Call Sentiment vs Share Price Movement")
    print("=" * 78)

    n_total = len(rows)
    n_non_neutral = sum(1 for r in rows if float(r["sentiment_score"]) != 0.0)
    print(f"\n  Dataset: {n_total} earnings calls, "
          f"{n_non_neutral} with non-neutral sentiment")

    # --- Table 1: All tickers ---
    all_summary = print_table("TABLE 1", window_labels, results,
                              filter_neutral=False)

    # --- Table 2: Non-neutral only (the real hypothesis test) ---
    nn_summary = print_table("TABLE 2", window_labels, results,
                             filter_neutral=True)

    # -- Per-ticker detail
    print(f"\n{'=' * 78}")
    print("  PER-TICKER DETAIL (non-neutral sentiment only)")
    print("=" * 78)
    print(f"\n  {'Ticker':<7} {'Sent':>6} {'Label':>9}"
          f"  {'Pre-1d':>8} {'Pre-3d':>8} {'Pre-5d':>8}"
          f"  {'Post-1d':>8} {'Post-5d':>8} {'Post-15d':>9} {'Post-30d':>9}")
    print("  " + "-" * 95)

    for row in rows:
        ticker = row["ticker"]
        sentiment = float(row["sentiment_score"])
        if sentiment == 0.0:
            continue

        def find_return(window_label: str) -> str:
            for t, s, r, a in results.get(window_label, []):
                if t == ticker:
                    marker = " *" if a else ""
                    return f"{r:+.2%}{marker}"
            return "n/a"

        print(f"  {ticker:<7} {sentiment:>+.3f} {row['sentiment_label']:>9}"
              f"  {find_return('pre_1d'):>8} {find_return('pre_3d'):>8} "
              f"{find_return('pre_5d'):>8}"
              f"  {find_return('post_1d'):>8} {find_return('post_5d'):>8} "
              f"{find_return('post_15d'):>9} {find_return('post_30d'):>9}")

    print("\n  (* = aligned with sentiment direction)")

    # -- Interpretation
    print(f"\n{'=' * 78}")
    print("  INTERPRETATION (based on non-neutral tickers)")
    print("=" * 78)

    post_nn = [(d["window"], d["alignment"], d["correlation"], d["avg_return"])
               for d in nn_summary
               if d["window"].startswith("post_") and d["alignment"] is not None]

    pre_nn = [(d["window"], d["alignment"], d["correlation"], d["avg_return"])
              for d in nn_summary
              if d["window"].startswith("pre_") and d["alignment"] is not None]

    if pre_nn:
        print("\n  PRE-CALL (does the market price-in sentiment before the call?)")
        for w, a, c, r in pre_nn:
            c_str = f"{c:.3f}" if c is not None else "n/a"
            print(f"    {w:<12} alignment={a:.1%}  corr={c_str}  avg_return={r:+.2%}")
        avg_pre = sum(d[1] for d in pre_nn) / len(pre_nn)
        if avg_pre > 0.55:
            print(f"\n    --> Pre-call avg alignment {avg_pre:.1%}: "
                  "evidence of pricing-in BEFORE the call (supports EMH)")
        else:
            print(f"\n    --> Pre-call avg alignment {avg_pre:.1%}: "
                  "little evidence of pre-call pricing-in")

    if post_nn:
        print("\n  POST-CALL (does sentiment predict price direction after the call?)")
        for w, a, c, r in post_nn:
            c_str = f"{c:.3f}" if c is not None else "n/a"
            print(f"    {w:<12} alignment={a:.1%}  corr={c_str}  avg_return={r:+.2%}")
        avg_post = sum(d[1] for d in post_nn) / len(post_nn)

        print(f"\n    --> Post-call avg alignment {avg_post:.1%}")
        if avg_post > 0.60:
            print("    --> CONCLUSION: Sentiment IS predictive of post-call price direction.")
            print("        This SUPPORTS the hypothesis that earnings-call sentiment")
            print("        can inform investment decisions.")
        elif avg_post > 0.50:
            print("    --> CONCLUSION: Marginal predictive signal (slightly above 50%).")
            print("        WEAK support for a sentiment-based strategy.")
        else:
            print("    --> CONCLUSION: Sentiment is NOT reliably predictive of post-call")
            print("        price direction. Does NOT support using earnings-call sentiment")
            print("        alone as an investment signal.")

    print(f"\n  Random baseline (coin flip): 50.0%")
    print("=" * 78)

    # -- Save CSV --
    out_csv = Path(__file__).resolve().parent.parent / "hypothesis_results.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "window", "scope", "n", "alignment", "correlation", "avg_return",
        ])
        writer.writeheader()
        for scope, summary in [("all", all_summary), ("non_neutral", nn_summary)]:
            for d in summary:
                writer.writerow({
                    "window": d["window"],
                    "scope": scope,
                    "n": d["n"],
                    "alignment": f"{d['alignment']:.4f}" if d["alignment"] is not None else "",
                    "correlation": f"{d['correlation']:.4f}" if d["correlation"] is not None else "",
                    "avg_return": f"{d['avg_return']:.6f}" if d["avg_return"] is not None else "",
                })
    print(f"\n  Results saved to: {out_csv}")


if __name__ == "__main__":
    main()
