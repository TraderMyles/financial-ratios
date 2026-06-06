# DAX40 Financial Analyser — Claude Code Instructions

## Project Overview

A Streamlit app that displays 18 financial ratios for all 40 DAX40 companies across 3 fiscal years (2022, 2023, 2024), with pre-generated AI insights and interactive charts. Zero API calls at runtime — everything is pre-computed and stored in CSVs.

## Architecture

```
fetch_data.py     → run once → pulls raw financials from yfinance → saves data/raw_financials.csv + data/share_prices.csv
calculate.py      → run once → reads raw CSVs → computes all 18 ratios + YoY changes + sector averages → saves data/ratios.csv
insights.py       → run once → reads ratios.csv → calls Claude API 4x per company (160 calls total) → saves data/insights.csv
app.py            → Streamlit app → reads ratios.csv + insights.csv → pure display, no external calls
```

## File Structure to Build

```
dax40_analyser/
├── fetch_data.py          # already written — do not modify
├── calculate.py           # to build
├── insights.py            # to build
├── app.py                 # to build
├── requirements.txt       # already written — do not modify
├── CLAUDE.md              # this file
└── data/                  # created by fetch_data.py
    ├── raw_financials.csv
    ├── share_prices.csv
    ├── ratios.csv
    └── insights.csv
```

---

## calculate.py — What to Build

Reads `data/raw_financials.csv` and `data/share_prices.csv`. Computes all ratios per company per year. Saves `data/ratios.csv`.

### Ratios to Calculate

**Profitability**
- `gross_profit_margin` = gross_profit / total_revenue × 100
- `operating_profit_margin` = operating_income / total_revenue × 100
- `roce` = ebit / (total_assets - current_liabilities) × 100

**YoY Changes** (for each of the 3 profitability ratios)
- `gpm_change_y0_y1` = GPM year1 - GPM year0 (i.e. 2023 minus 2022)
- `gpm_change_y1_y2` = GPM year2 - GPM year1 (i.e. 2024 minus 2023)
- Same pattern for OPM and ROCE

**Solvency**
- `gearing_ratio` = total_debt / stockholders_equity × 100
- `interest_cover` = ebit / abs(interest_expense)

**Liquidity**
- `current_ratio` = current_assets / current_liabilities
- `acid_ratio` = (current_assets - inventory) / current_liabilities
- `trade_payables_days` = (accounts_payable / total_revenue) × 365
- `trade_receivables_days` = (accounts_receivable / total_revenue) × 365
- `inventory_days` = (inventory / (total_revenue - gross_profit)) × 365  [use COGS = revenue - gross profit]
- `working_capital_cycle` = trade_receivables_days + inventory_days - trade_payables_days

**Investor**
- `share_price` = pulled from share_prices.csv by ticker + year
- `share_price_change` = ((price_year - price_prev_year) / price_prev_year) × 100  [None for year 0]
- `eps` = net_income / shares_outstanding
- `dps` = abs(dividends_paid) / shares_outstanding  [dividends_paid is negative in yfinance]
- `dividend_yield` = dps / share_price × 100
- `pe_ratio` = share_price / eps  [None if eps <= 0]

### Sector Averages
After computing per-company ratios, compute the mean of each ratio grouped by sector and year. Save these as additional rows with `ticker = "SECTOR_AVG"` and `name = sector name`. The app and insights script will use these for benchmarking.

### Output columns
ticker, name, sector, year, [all 18 ratios], [6 YoY change columns], [sector average columns prefixed with `sector_avg_`]

---

## insights.py — What to Build

Reads `data/ratios.csv`. For each company, makes 4 Claude API calls (one per section). Saves `data/insights.csv`.

### Setup
```python
import anthropic
import os
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```

### Per Company, Per Section — 4 calls

Sections: `profitability`, `solvency`, `liquidity`, `investor`

For each call, pass:
- Company name and sector
- The relevant ratios for all 3 years (formatted as a clean table in the prompt)
- The sector average for each ratio across the same 3 years
- The YoY changes where applicable

### Insight Brief — include this verbatim in every system prompt

```
You are a financial analyst writing AFM-level ratio commentary.

Rules:
1. Do NOT simply state whether a ratio moved up or down. That is the minimum — go beyond it.
2. Suggest WHY the change may have taken place — reference plausible business, macroeconomic, or sector-specific drivers. Be specific to the company and sector.
3. Describe the implications if the trend PERSISTS — what does it mean for the company's financial health, competitive position, or investor returns?
4. Where a ratio diverges from the sector average, explain what that divergence signals about this company specifically.
5. Write in flowing paragraphs, not bullet points. Analytical, not descriptive.
6. Max 200 words per section. Be precise and dense — every sentence should add something.
```

### Prompt structure per section

```
Company: {name} | Sector: {sector}

{section_name} Ratios — 3 Year Trend:
{table of ratios for this section, all 3 years}

Sector Average ({sector}):
{table of sector averages for same ratios, all 3 years}

Write your {section_name} insight.
```

### Output CSV columns
`ticker, name, section, insight`

Where `section` is one of: `profitability`, `solvency`, `liquidity`, `investor`

### Error handling
- Wrap each API call in try/except
- If a call fails, write `"Insight unavailable."` to that cell
- Print progress: `[5/40] SAP — profitability ✓`
- Add `time.sleep(0.5)` between calls to avoid rate limits
- Check if insights.csv already exists and skip companies already completed (so you can resume if interrupted)

---

## app.py — What to Build

Streamlit app. Reads `data/ratios.csv` and `data/insights.csv`. No external API calls.

### Layout

**Sidebar**
- DAX40 logo or title: "DAX40 Analyser"
- Selectbox: company name (sorted A-Z), maps to ticker
- Previous / Next buttons to step through companies sequentially
- Show: company name, sector, ticker
- Small summary: current year (2024) GPM, OPM, ROCE, Current Ratio as quick-glance metrics

**Main area — 4 tabs**
- Profitability
- Solvency
- Liquidity
- Investor

### Each Tab Structure

1. **Metric cards row** — show each ratio for 2024 with YoY delta badge (green/red arrow + % change)
2. **Charts** — one Plotly line chart per ratio showing the 3-year trend, with a dashed line showing the sector average trend across the same years. Use `plotly.graph_objects` not express — more control. All charts: clean, minimal, dark-friendly
3. **Insight block** — styled text box with the pre-generated Claude insight for that section. Label it clearly: "AI Analysis" with a small disclaimer "Generated from 3-year financial data via Claude."

### Chart spec
- X axis: 2022, 2023, 2024
- Company line: solid, coloured
- Sector average line: dashed, grey
- Hover shows exact value
- Title is the ratio name
- No legend clutter — label lines directly or use a minimal legend

### YoY delta badges
- Green with ↑ if ratio improved (context-aware — higher is not always better, e.g. gearing)
- Red with ↓ if ratio worsened
- Grey if no change or insufficient data
- Define a dict of which direction is "good" for each ratio

### Data loading
```python
@st.cache_data
def load_data():
    ratios = pd.read_csv("data/ratios.csv")
    insights = pd.read_csv("data/insights.csv")
    return ratios, insights
```

### Error states
- If `data/ratios.csv` doesn't exist: show instructions to run `fetch_data.py` then `calculate.py`
- If `data/insights.csv` doesn't exist: show ratios and charts but replace insight blocks with "Run insights.py to generate AI analysis."
- If a specific ratio is None/NaN for a company: show "N/A" gracefully, skip that ratio's chart

---

## Run Order

```bash
pip install -r requirements.txt

python fetch_data.py
# → creates data/raw_financials.csv and data/share_prices.csv
# Takes ~5-10 minutes for all 40 companies

python calculate.py
# → creates data/ratios.csv
# Instant

export ANTHROPIC_API_KEY=your_key_here
python insights.py
# → creates data/insights.csv
# Takes ~5 minutes (160 API calls with polite delays)

streamlit run app.py
# → opens in browser
```

---

## Key Decisions & Constraints

- **yfinance row labels**: income statement uses "Total Revenue", "Gross Profit", "Operating Income", "EBIT", "Net Income", "Interest Expense". Balance sheet uses "Total Assets", "Current Assets", "Current Liabilities", "Inventory", "Total Debt", "Stockholders Equity", "Cash And Cash Equivalents", "Accounts Receivable", "Accounts Payable". Cash flow uses "Cash Dividends Paid". These are exact strings — use them.
- **yfinance column order**: most recent year first. fetch_data.py already normalises columns to integer years (2022, 2023, 2024).
- **Fiscal year**: all DAX40 companies use Dec 31 fiscal year end. Share prices are the closing price on the last trading day of each calendar year.
- **Interest expense**: yfinance returns this as a negative number. Use `abs()` when calculating interest cover.
- **Dividends paid**: yfinance returns this as a negative number in cashflow. Use `abs()` when calculating DPS.
- **Financials are in euros**: display with € symbol. Share prices are in EUR.
- **Some companies will have missing data**: handle None/NaN gracefully everywhere — never let a missing value crash the app.
- **Sector averages**: exclude companies with NaN ratios from the sector average calculation (use `skipna=True` in mean).
- **Financial sector quirk**: Allianz, Deutsche Bank, Deutsche Boerse, Hannover Re, Munich Re are financials — they don't have meaningful inventory or COGS. Their liquidity ratios may be None. Handle gracefully.

---

## Aesthetics

- Streamlit theme: dark preferred
- Charts: Plotly with dark template (`template="plotly_dark"`)
- Insight boxes: `st.info()` or a custom `st.markdown()` with HTML styling
- Keep it clean — this is a video tool, it needs to look good on screen
- Metric cards: use `st.metric()` with delta for YoY change

---

## What fetch_data.py Already Does

Already written. Do not rewrite it. It:
- Defines all 40 DAX40 tickers with names and sectors
- Fetches income statement, balance sheet, cash flow for 2022/2023/2024
- Fetches fiscal year end share prices (last trading day of Dec each year)
- Saves `data/raw_financials.csv` and `data/share_prices.csv`

Start with `calculate.py`.