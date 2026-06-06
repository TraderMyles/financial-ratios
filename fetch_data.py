"""
Fetches raw financial data for all 40 DAX40 companies from yfinance.
Run once to produce data/raw_financials.csv and data/share_prices.csv.
"""

import os
import time
import numpy as np
import pandas as pd
import yfinance as yf

DAX40 = [
    {"ticker": "ADS.DE",  "name": "Adidas",                 "sector": "Consumer Discretionary"},
    {"ticker": "ALV.DE",  "name": "Allianz",                 "sector": "Financials"},
    {"ticker": "BAS.DE",  "name": "BASF",                    "sector": "Materials"},
    {"ticker": "BAYN.DE", "name": "Bayer",                   "sector": "Healthcare"},
    {"ticker": "BEI.DE",  "name": "Beiersdorf",              "sector": "Consumer Staples"},
    {"ticker": "BMW.DE",  "name": "BMW",                     "sector": "Consumer Discretionary"},
    {"ticker": "BNR.DE",  "name": "Brenntag",                "sector": "Materials"},
    {"ticker": "CBK.DE",  "name": "Commerzbank",             "sector": "Financials"},
    {"ticker": "CON.DE",  "name": "Continental",             "sector": "Consumer Discretionary"},
    {"ticker": "1COV.DE", "name": "Covestro",                "sector": "Materials"},
    {"ticker": "DTG.DE",  "name": "Daimler Truck",           "sector": "Industrials"},
    {"ticker": "DBK.DE",  "name": "Deutsche Bank",           "sector": "Financials"},
    {"ticker": "DB1.DE",  "name": "Deutsche Boerse",         "sector": "Financials"},
    {"ticker": "DHL.DE",  "name": "Deutsche Post",           "sector": "Industrials"},
    {"ticker": "DTE.DE",  "name": "Deutsche Telekom",        "sector": "Communication Services"},
    {"ticker": "EOAN.DE", "name": "E.ON",                    "sector": "Utilities"},
    {"ticker": "FRE.DE",  "name": "Fresenius",               "sector": "Healthcare"},
    {"ticker": "FME.DE",  "name": "Fresenius Medical Care",  "sector": "Healthcare"},
    {"ticker": "HNR1.DE", "name": "Hannover Re",             "sector": "Financials"},
    {"ticker": "HEIG.DE", "name": "Heidelberg Materials",    "sector": "Materials"},
    {"ticker": "HEN3.DE", "name": "Henkel",                  "sector": "Consumer Staples"},
    {"ticker": "IFX.DE",  "name": "Infineon",                "sector": "Technology"},
    {"ticker": "MBG.DE",  "name": "Mercedes-Benz",           "sector": "Consumer Discretionary"},
    {"ticker": "MRK.DE",  "name": "Merck KGaA",              "sector": "Healthcare"},
    {"ticker": "MTX.DE",  "name": "MTU Aero Engines",        "sector": "Industrials"},
    {"ticker": "MUV2.DE", "name": "Munich Re",               "sector": "Financials"},
    {"ticker": "P911.DE", "name": "Porsche AG",              "sector": "Consumer Discretionary"},
    {"ticker": "PAH3.DE", "name": "Porsche SE",              "sector": "Consumer Discretionary"},
    {"ticker": "QIA.DE",  "name": "Qiagen",                  "sector": "Healthcare"},
    {"ticker": "RHM.DE",  "name": "Rheinmetall",             "sector": "Industrials"},
    {"ticker": "RWE.DE",  "name": "RWE",                     "sector": "Utilities"},
    {"ticker": "SAP.DE",  "name": "SAP",                     "sector": "Technology"},
    {"ticker": "SRT3.DE", "name": "Sartorius",               "sector": "Healthcare"},
    {"ticker": "SIE.DE",  "name": "Siemens",                 "sector": "Industrials"},
    {"ticker": "ENR.DE",  "name": "Siemens Energy",          "sector": "Industrials"},
    {"ticker": "SHL.DE",  "name": "Siemens Healthineers",    "sector": "Healthcare"},
    {"ticker": "SY1.DE",  "name": "Symrise",                 "sector": "Materials"},
    {"ticker": "VNA.DE",  "name": "Vonovia",                 "sector": "Real Estate"},
    {"ticker": "VOW3.DE", "name": "Volkswagen",              "sector": "Consumer Discretionary"},
    {"ticker": "ZAL.DE",  "name": "Zalando",                 "sector": "Consumer Discretionary"},
]

YEARS = [2022, 2023, 2024]

INCOME_FIELDS = [
    "Total Revenue", "Gross Profit", "Operating Income", "EBIT",
    "Net Income", "Interest Expense",
]
BALANCE_FIELDS = [
    "Total Assets", "Current Assets", "Current Liabilities", "Inventory",
    "Total Debt", "Stockholders Equity", "Cash And Cash Equivalents",
    "Accounts Receivable", "Accounts Payable",
]
CASHFLOW_FIELDS = ["Cash Dividends Paid"]
SHARES_FIELDS = ["Diluted Average Shares", "Basic Average Shares", "Ordinary Shares Number"]


def _normalize_stmt(stmt):
    """Convert datetime-indexed columns to a {year: Series} dict."""
    if stmt is None or stmt.empty:
        return {}
    result = {}
    for col in stmt.columns:
        yr = getattr(col, "year", None)
        if yr is not None:
            result[yr] = stmt[col]
    return result


def _get(normalized, field, year):
    series = normalized.get(year)
    if series is None:
        return None
    try:
        val = series.get(field, None)
        if val is None:
            return None
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def get_year_end_price(ticker, year):
    try:
        data = yf.download(
            ticker,
            start=f"{year}-12-01",
            end=f"{year + 1}-01-10",
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return None
        dec_data = data[data.index.year == year]
        if dec_data.empty:
            return None
        close = dec_data["Close"].iloc[-1]
        # Handle multi-level columns from newer yfinance
        if hasattr(close, "item"):
            close = close.item()
        return float(close)
    except Exception:
        return None


def fetch_company(company, idx, total):
    ticker = company["ticker"]
    name = company["name"]
    sector = company["sector"]

    print(f"[{idx}/{total}] Fetching {name} ({ticker})...", end=" ", flush=True)

    try:
        stock = yf.Ticker(ticker)
        income = _normalize_stmt(stock.income_stmt)
        balance = _normalize_stmt(stock.balance_sheet)
        cashflow = _normalize_stmt(stock.cashflow)

        rows = []
        for year in YEARS:
            row = {"ticker": ticker, "name": name, "sector": sector, "year": year}

            for field in INCOME_FIELDS:
                row[field] = _get(income, field, year)

            for field in BALANCE_FIELDS:
                row[field] = _get(balance, field, year)

            for field in CASHFLOW_FIELDS:
                row[field] = _get(cashflow, field, year)

            shares = None
            for sf in SHARES_FIELDS:
                shares = _get(income, sf, year)
                if shares is not None:
                    break
            row["shares_outstanding"] = shares

            rows.append(row)

        print("✓")
        return rows

    except Exception as e:
        print(f"✗ ({e})")
        return [{"ticker": ticker, "name": name, "sector": sector, "year": year} for year in YEARS]


def fetch_share_prices():
    rows = []
    total = len(DAX40)
    print("\nFetching year-end share prices...")
    for idx, company in enumerate(DAX40, 1):
        ticker = company["ticker"]
        print(f"  [{idx}/{total}] {ticker}", end=" ", flush=True)
        for year in YEARS:
            price = get_year_end_price(ticker, year)
            rows.append({"ticker": ticker, "year": year, "price": price})
            time.sleep(0.1)
        print("✓")
    return pd.DataFrame(rows)


def main():
    os.makedirs("data", exist_ok=True)
    total = len(DAX40)

    all_rows = []
    for idx, company in enumerate(DAX40, 1):
        rows = fetch_company(company, idx, total)
        all_rows.extend(rows)
        time.sleep(0.3)

    raw_df = pd.DataFrame(all_rows)
    raw_df.to_csv("data/raw_financials.csv", index=False)
    print(f"\nSaved data/raw_financials.csv ({len(raw_df)} rows)")

    prices_df = fetch_share_prices()
    prices_df.to_csv("data/share_prices.csv", index=False)
    print(f"Saved data/share_prices.csv ({len(prices_df)} rows)")


if __name__ == "__main__":
    main()
