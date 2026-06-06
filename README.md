# DAX40 Financial Analyser

A Streamlit app displaying 18 financial ratios for all 40 DAX40 companies across 2022–2024, with pre-generated AI insights and interactive charts. Zero API calls at runtime — everything is pre-computed and stored in CSVs.

---

## Features

- **18 financial ratios** across Profitability, Solvency, Liquidity, and Investor categories
- **3-year trend charts** with sector average benchmarking
- **YoY delta badges** — context-aware (lower gearing is green, not red)
- **AI insights** per company per section, generated via Claude at build time
- **Sidebar navigation** — step through all 40 companies with Prev/Next buttons

---

## Ratios Covered

| Category | Ratios |
|---|---|
| Profitability | Gross Profit Margin, Operating Profit Margin, ROCE |
| Solvency | Gearing Ratio, Interest Cover |
| Liquidity | Current Ratio, Acid Test, Trade Payables Days, Trade Receivables Days, Inventory Days, Working Capital Cycle |
| Investor | Share Price, EPS, DPS, Dividend Yield, P/E Ratio |

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Run Order

**Step 1 — Fetch raw financial data** (~5–10 min)
```bash
python fetch_data.py
```
Pulls income statements, balance sheets, cash flows and year-end share prices from yfinance for all 40 companies. Creates `data/raw_financials.csv` and `data/share_prices.csv`.

**Step 2 — Calculate ratios** (instant)
```bash
python calculate.py
```
Computes all ratios, YoY changes, and sector averages. Creates `data/ratios.csv`.

**Step 3 — Generate AI insights** (~5 min)
```bash
export ANTHROPIC_API_KEY=your_key_here
python insights.py
```
Makes 4 Claude API calls per company (160 total) and saves to `data/insights.csv`. Resume-safe — re-running skips companies already completed.

**Step 4 — Launch the app**
```bash
streamlit run app.py
```

---

## Project Structure

```
├── fetch_data.py       # Fetches raw data from yfinance
├── calculate.py        # Computes all ratios and sector averages
├── insights.py         # Generates AI analysis via Claude API
├── app.py              # Streamlit frontend
├── requirements.txt
└── data/               # Generated — not committed to git
    ├── raw_financials.csv
    ├── share_prices.csv
    ├── ratios.csv
    └── insights.csv
```

---

## Notes

- Financials are sourced from yfinance and denominated in euros
- All 40 companies use a 31 December fiscal year end
- Share prices are the closing price on the last trading day of each December
- Financial sector companies (Allianz, Deutsche Bank, Deutsche Boerse, Hannover Re, Munich Re) may show N/A for inventory-based liquidity ratios — this is expected
- The `data/` directory is gitignored
