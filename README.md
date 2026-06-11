# Financial Sentiment Analyser

## Setup

**1. `pip install -r requirements.txt`**
**2. Run the API:** `uvicorn api.main:app --reload`

### API Endpoints

- **POST `/analysed-earnings`**
  - Body: `{ "ticker": "AAPL", "quarter": "Q1" }`
  - Returns: full `EarningsCall` object with sentiment.
- **POST `/earning-call`**
  - Body: `{ "ticker": "AAPL", "quarter": "Q1" }`
  - Returns: `EarningsCall` without sentiment (scrape only).

The `transcript` field is returned as a single string.

> [!NOTE]
> This application scrapes transcripts directly from **Motley Fool** (`fool.com`). Therefore, only tickers/quarters with earnings call transcripts published on Motley Fool are supported. If no transcript is found for the requested ticker, the API returns a `500` response: `"No earnings call transcript found for ticker <TICKER>"`.

## Design

##### Sequence Diagram

![1779551988039](image/README/1779551988039.png)

## Study

### Hypothesis
The core hypothesis under test is whether the sentiment of an earnings call (quantified using the FinBERT sentiment model) is reflected in subsequent share price movements:
1. **Efficient Market Hypothesis (EMH)** suggests that the market is relatively efficient, so any predictable sentiment expectations are priced in *before* the call takes place. Therefore, we should see sentiment alignment in the days leading up to the call.
2. **Investment Strategy Hypothesis** suggests that investors can trade on earnings call sentiment to generate positive excess returns post-call. Therefore, sentiment should align with price movements in the days/weeks after the call.

### Methodology
- **Sentiment Scoring**: Earnings call transcripts are processed using **FinBERT** (a BERT model fine-tuned for financial sentiment analysis) to yield a directional sentiment score. Neutral transcripts (score = 0.0) are excluded from the directional hypothesis tests.
- **Price Returns**: Historical daily close prices are fetched from Yahoo Finance.
- **Windows Evaluated**:
  - **Pre-call windows**: 1, 3, and 5 days prior to the call date.
  - **Post-call windows**: 1, 3, 5, 7, 10, 15, and 30 days after the call date.
- **Metrics**:
  - **Alignment Rate**: Percentage of calls where the sign of the sentiment score (positive/negative) matches the sign of the price return (positive/negative). Random baseline is 50.0%.
  - **Correlation**: Pearson correlation coefficient between sentiment score and price return.

---

### Findings (Non-Neutral Tickers, N=10)

The hypothesis was evaluated across 19 earnings calls, 10 of which returned non-neutral sentiment scores.

#### Pre-Call Windows (Leading INTO the Call)

| Window | N | Alignment Rate | Correlation | Average Return |
| :--- | :---: | :---: | :---: | :---: |
| **Pre -1 day** | 10 | **70.0%** | 0.378 | +2.43% |
| **Pre -3 days** | 10 | 50.0% | 0.295 | +3.20% |
| **Pre -5 days** | 10 | 50.0% | 0.310 | +4.03% |

#### Post-Call Windows (Following the Call)

| Window | N | Alignment Rate | Correlation | Average Return |
| :--- | :---: | :---: | :---: | :---: |
| **Post +1 day** | 10 | 40.0% | 0.178 | +0.60% |
| **Post +3 days** | 10 | **70.0%** | 0.258 | +0.45% |
| **Post +5 days** | 10 | 40.0% | 0.149 | +0.15% |
| **Post +7 days** | 10 | 50.0% | 0.120 | +0.53% |
| **Post +10 days** | 10 | 50.0% | 0.090 | +0.26% |
| **Post +15 days** | 10 | 50.0% | 0.152 | +1.56% |
| **Post +30 days** | 8 | 37.5% | 0.315 | +0.52% |

> [!NOTE]
> Post-30d analysis excludes two tickers (NVDA and CSCO) whose calls occurred less than 35 days ago.

#### Per-Ticker Detail (Non-Neutral Sentiment Only)

| Ticker | Sentiment Score | Label | Pre-1d | Pre-3d | Pre-5d | Post-1d | Post-5d | Post-15d | Post-30d |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GOOGL** | +0.705 | positive | +0.05% * | -0.11% | +1.61% * | +9.96% * | +9.52% * | +14.61% * | +8.69% * |
| **META** | +0.501 | positive | -0.33% | -1.40% | -0.88% | -8.55% | -8.77% | -7.58% | -5.47% |
| **NVDA** | +0.786 | positive | +1.30% * | +0.52% * | -0.82% | -1.77% | -3.85% | -2.04% | n/a |
| **JPM** | -0.662 | negative | -1.26% * | +0.87% | +0.98% | +0.01% | -0.44% * | +0.61% | -3.19% * |
| **V** | +0.850 | positive | +8.26% * | +8.14% * | +8.22% * | -1.50% | -2.39% | -3.49% | -2.34% |
| **UNH** | +0.871 | positive | +6.96% * | +6.59% * | +9.36% * | +2.17% * | +2.51% * | +6.15% * | +10.54% * |
| **XOM** | +0.946 | positive | -1.02% | +1.45% * | +3.08% * | +0.00% | -2.66% | +4.09% * | -1.54% |
| **MA** | +0.681 | positive | -4.25% | -0.69% | -0.25% | -1.48% | -1.16% | -1.73% | -1.78% |
| **AVGO** | +0.937 | positive | +1.18% * | -0.40% | -0.63% | +4.80% * | +8.89% * | +0.73% * | -0.73% |
| **CSCO** | +0.955 | positive | +13.41% * | +17.03% * | +19.63% * | +2.32% * | -0.13% | +4.23% * | n/a |

> `*` = Price return direction aligned with sentiment direction.

---

### Interpretation & Conclusions

1. **Pre-Call Pricing-In (EMH Support)**:
   - Sentiment has a strong **70.0% alignment rate** one day prior to the earnings call, with an average return of **+2.43%**.
   - This provides evidence that market participants correctly anticipate the tone of the earnings call and trade on it beforehand, pricing in the information prior to the official announcement.
2. **Post-Call Randomness (Lack of Predictive Power)**:
   - Following the call, the alignment rate drops to **48.2%** on average across all windows—worse than a random coin flip.
   - Pearson correlation coefficients are consistently weak (mostly below 0.30), showing no systematic relationship.
   - High idiosyncratic variance suggests sentiment-based trading is highly stock-specific rather than a reliable market-wide anomaly.

> [!IMPORTANT]
> **Conclusion**: The data does not support using earnings-call sentiment alone as a systematic investment strategy. Post-call returns are essentially random relative to the sentiment score, supporting the hypothesis that the market incorporates earnings expectations before the actual call.

---

### Comparison with Long-Term Quarterly Results
Analysis of the larger [quarterly_results.csv](file:///P:/financial-sentiment-analyser/quarterly_results.csv) dataset (containing over 1,000 historical records) confirms the same pattern at a broader timeline:
- **Quarterly Alignment Rate**: **53.33%** (near coin-flip baseline).
- **Quarterly Correlation**: **0.00** (no linear relationship).

This shows that the dilution of the post-call sentiment signal is consistent across both short-term daily and long-term quarterly horizons.

---

### Analysis Utilities & Scripts

- [hypothesis_test.py](file:///P:/financial-sentiment-analyser/analysis/hypothesis_test.py): Runs the directional hypothesis testing. It fetches Yahoo Finance daily historical price data, maps them to call dates from [results.csv](file:///P:/financial-sentiment-analyser/results.csv), calculates returns across pre-call and post-call windows, and outputs metrics to [hypothesis_results.csv](file:///P:/financial-sentiment-analyser/hypothesis_results.csv).
- [quarter_returns.py](file:///P:/financial-sentiment-analyser/analysis/quarter_returns.py): Computes historical price returns and alignments at a quarterly level using [quarterly_results.csv](file:///P:/financial-sentiment-analyser/quarterly_results.csv).
- [test_hypothesis.py](file:///P:/financial-sentiment-analyser/tests/test_hypothesis.py): Pytest suite verifying the mathematical calculations, correctness of alignments, and data constraints across all target windows.

To execute the hypothesis test analysis script:
```bash
python analysis/hypothesis_test.py
```

To run the unit and integration tests:
```bash
pytest
```
