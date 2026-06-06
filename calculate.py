"""
Reads data/raw_financials.csv and data/share_prices.csv.
Computes all 18 ratios, YoY changes, and sector averages.
Saves data/ratios.csv.
"""

import os
import numpy as np
import pandas as pd

YEARS = [2022, 2023, 2024]

RATIO_COLS = [
    "gross_profit_margin", "operating_profit_margin", "roce",
    "gearing_ratio", "interest_cover",
    "current_ratio", "acid_ratio",
    "trade_payables_days", "trade_receivables_days", "inventory_days", "working_capital_cycle",
    "share_price", "share_price_change", "eps", "dps", "dividend_yield", "pe_ratio",
]

YOY_RATIOS = [
    ("gross_profit_margin", "gpm"),
    ("operating_profit_margin", "opm"),
    ("roce", "roce"),
]

YOY_COLS = [f"{p}_change_y0_y1" for _, p in YOY_RATIOS] + [f"{p}_change_y1_y2" for _, p in YOY_RATIOS]


def _f(val):
    """Convert to float, returning None for NaN/None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def safe_div(a, b):
    a, b = _f(a), _f(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def pct(a, b):
    d = safe_div(a, b)
    return d * 100 if d is not None else None


def compute_ratios(row, price, prev_price):
    rev = _f(row.get("Total Revenue"))
    gp = _f(row.get("Gross Profit"))
    oi = _f(row.get("Operating Income"))
    ebit = _f(row.get("EBIT"))
    ni = _f(row.get("Net Income"))
    ie = _f(row.get("Interest Expense"))
    ta = _f(row.get("Total Assets"))
    ca = _f(row.get("Current Assets"))
    cl = _f(row.get("Current Liabilities"))
    inv = _f(row.get("Inventory"))
    td = _f(row.get("Total Debt"))
    se = _f(row.get("Stockholders Equity"))
    ar = _f(row.get("Accounts Receivable"))
    ap = _f(row.get("Accounts Payable"))
    cdp = _f(row.get("Cash Dividends Paid"))
    shares = _f(row.get("shares_outstanding"))

    r = {}

    # --- Profitability ---
    r["gross_profit_margin"] = pct(gp, rev)
    r["operating_profit_margin"] = pct(oi, rev)
    # ROCE = EBIT / (Total Assets - Current Liabilities)
    if ebit is not None and ta is not None and cl is not None:
        capital_employed = ta - cl
        r["roce"] = pct(ebit, capital_employed)
    else:
        r["roce"] = None

    # --- Solvency ---
    r["gearing_ratio"] = pct(td, se)
    if ebit is not None and ie is not None and ie != 0:
        r["interest_cover"] = ebit / abs(ie)
    else:
        r["interest_cover"] = None

    # --- Liquidity ---
    r["current_ratio"] = safe_div(ca, cl)
    if ca is not None and inv is not None and cl is not None and cl != 0:
        r["acid_ratio"] = (ca - inv) / cl
    else:
        r["acid_ratio"] = None

    r["trade_payables_days"] = None if (ap is None or rev is None or rev == 0) else (ap / rev) * 365
    r["trade_receivables_days"] = None if (ar is None or rev is None or rev == 0) else (ar / rev) * 365

    cogs = (rev - gp) if rev is not None and gp is not None else None
    r["inventory_days"] = None if (inv is None or cogs is None or cogs == 0) else (inv / cogs) * 365

    trd = r["trade_receivables_days"]
    invd = r["inventory_days"]
    tpd = r["trade_payables_days"]
    if trd is not None and invd is not None and tpd is not None:
        r["working_capital_cycle"] = trd + invd - tpd
    else:
        r["working_capital_cycle"] = None

    # --- Investor ---
    r["share_price"] = price
    if price is not None and prev_price is not None and prev_price != 0:
        r["share_price_change"] = ((price - prev_price) / prev_price) * 100
    else:
        r["share_price_change"] = None

    r["eps"] = safe_div(ni, shares)

    if cdp is not None and shares is not None and shares != 0:
        r["dps"] = abs(cdp) / shares
    else:
        r["dps"] = None

    r["dividend_yield"] = pct(r["dps"], price)

    eps = r["eps"]
    if price is not None and eps is not None and eps > 0:
        r["pe_ratio"] = price / eps
    else:
        r["pe_ratio"] = None

    return r


def main():
    print("Loading raw data...")
    raw = pd.read_csv("data/raw_financials.csv")
    prices = pd.read_csv("data/share_prices.csv")

    price_lookup = {(row["ticker"], int(row["year"])): _f(row["price"])
                    for _, row in prices.iterrows()}

    output_rows = []

    for ticker, group in raw.groupby("ticker", sort=False):
        group = group.sort_values("year").reset_index(drop=True)

        year_to_row = {int(r["year"]): r for _, r in group.iterrows()}

        for year in YEARS:
            if year not in year_to_row:
                continue
            row = year_to_row[year]
            price = price_lookup.get((ticker, year))
            prev_price = price_lookup.get((ticker, year - 1))

            ratios = compute_ratios(row, price, prev_price)

            out = {
                "ticker": ticker,
                "name": row["name"],
                "sector": row["sector"],
                "year": year,
            }
            out.update(ratios)
            output_rows.append(out)

    df = pd.DataFrame(output_rows)

    # --- YoY changes (stored on all rows for a company) ---
    for ratio, prefix in YOY_RATIOS:
        df[f"{prefix}_change_y0_y1"] = None
        df[f"{prefix}_change_y1_y2"] = None

    for ticker, group in df.groupby("ticker"):
        yv = {int(r["year"]): r[ratio] for ratio, _ in YOY_RATIOS
              for _, r in group.iterrows()}

        for ratio, prefix in YOY_RATIOS:
            vals = {int(r["year"]): _f(r[ratio]) for _, r in group.iterrows()}
            v0, v1, v2 = vals.get(2022), vals.get(2023), vals.get(2024)

            c01 = (v1 - v0) if v0 is not None and v1 is not None else None
            c12 = (v2 - v1) if v1 is not None and v2 is not None else None

            mask = df["ticker"] == ticker
            df.loc[mask, f"{prefix}_change_y0_y1"] = c01
            df.loc[mask, f"{prefix}_change_y1_y2"] = c12

    # --- Sector averages ---
    sector_avgs = (
        df[df["ticker"] != "SECTOR_AVG"]
        .groupby(["sector", "year"])[RATIO_COLS]
        .mean()
        .reset_index()
    )

    sector_avg_cols = {col: f"sector_avg_{col}" for col in RATIO_COLS}
    sector_avgs = sector_avgs.rename(columns=sector_avg_cols)

    df = df.merge(sector_avgs, on=["sector", "year"], how="left")

    # --- Sector average rows ---
    sector_rows = []
    for (sector, year), group in df.groupby(["sector", "year"]):
        srow = {"ticker": "SECTOR_AVG", "name": sector, "sector": sector, "year": year}
        for col in RATIO_COLS:
            vals = group[col].dropna()
            srow[col] = float(vals.mean()) if not vals.empty else None
        for col in YOY_COLS:
            srow[col] = None
        for col in [f"sector_avg_{c}" for c in RATIO_COLS]:
            srow[col] = None
        sector_rows.append(srow)

    sector_df = pd.DataFrame(sector_rows)
    df = pd.concat([df, sector_df], ignore_index=True)

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/ratios.csv", index=False)

    companies = df[df["ticker"] != "SECTOR_AVG"]["ticker"].nunique()
    print(f"Saved data/ratios.csv ({len(df)} rows, {companies} companies + sector averages)")


if __name__ == "__main__":
    main()
