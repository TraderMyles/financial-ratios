"""
Reads data/ratios.csv. Makes 4 Claude API calls per company (160 total).
Saves data/insights.csv. Resume-safe: skips already-completed companies.
"""

import os
import time
import anthropic
import pandas as pd

SECTIONS = {
    "profitability": {
        "ratios": ["gross_profit_margin", "operating_profit_margin", "roce"],
        "labels": {
            "gross_profit_margin": "Gross Profit Margin (%)",
            "operating_profit_margin": "Operating Profit Margin (%)",
            "roce": "ROCE (%)",
        },
        "yoy": {
            "gross_profit_margin": ("gpm_change_y0_y1", "gpm_change_y1_y2"),
            "operating_profit_margin": ("opm_change_y0_y1", "opm_change_y1_y2"),
            "roce": ("roce_change_y0_y1", "roce_change_y1_y2"),
        },
    },
    "solvency": {
        "ratios": ["gearing_ratio", "interest_cover"],
        "labels": {
            "gearing_ratio": "Gearing Ratio (%)",
            "interest_cover": "Interest Cover (x)",
        },
    },
    "liquidity": {
        "ratios": [
            "current_ratio", "acid_ratio",
            "trade_payables_days", "trade_receivables_days",
            "inventory_days", "working_capital_cycle",
        ],
        "labels": {
            "current_ratio": "Current Ratio",
            "acid_ratio": "Acid Test Ratio",
            "trade_payables_days": "Trade Payables Days",
            "trade_receivables_days": "Trade Receivables Days",
            "inventory_days": "Inventory Days",
            "working_capital_cycle": "Working Capital Cycle (days)",
        },
    },
    "investor": {
        "ratios": ["share_price", "share_price_change", "eps", "dps", "dividend_yield", "pe_ratio"],
        "labels": {
            "share_price": "Share Price (€)",
            "share_price_change": "Share Price Change (%)",
            "eps": "EPS (€)",
            "dps": "DPS (€)",
            "dividend_yield": "Dividend Yield (%)",
            "pe_ratio": "P/E Ratio",
        },
    },
}

SYSTEM_PROMPT = """You are a financial analyst writing AFM-level ratio commentary.

Rules:
1. Do NOT simply state whether a ratio moved up or down. That is the minimum — go beyond it.
2. Suggest WHY the change may have taken place — reference plausible business, macroeconomic, or sector-specific drivers. Be specific to the company and sector.
3. Describe the implications if the trend PERSISTS — what does it mean for the company's financial health, competitive position, or investor returns?
4. Where a ratio diverges from the sector average, explain what that divergence signals about this company specifically.
5. Write in flowing paragraphs, not bullet points. Analytical, not descriptive.
6. Max 200 words per section. Be precise and dense — every sentence should add something."""


def _fmt(val, decimals=2):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def build_table(company_data, section_key, section_def, sector_data):
    """Build a formatted string table for a section."""
    ratios = section_def["ratios"]
    labels = section_def["labels"]
    yoy = section_def.get("yoy", {})

    year_rows = {r["year"]: r for r in company_data}
    sector_rows = {r["year"]: r for r in sector_data}

    lines = []
    lines.append(f"{'Metric':<36} {'2022':>10} {'2023':>10} {'2024':>10}", )
    if yoy:
        lines[-1] += f"  {'22→23':>8}  {'23→24':>8}"
    lines.append("-" * (len(lines[0])))

    for ratio in ratios:
        label = labels[ratio]
        v22 = _fmt(year_rows.get(2022, {}).get(ratio))
        v23 = _fmt(year_rows.get(2023, {}).get(ratio))
        v24 = _fmt(year_rows.get(2024, {}).get(ratio))
        line = f"{label:<36} {v22:>10} {v23:>10} {v24:>10}"
        if yoy and ratio in yoy:
            c01_col, c12_col = yoy[ratio]
            c01 = _fmt(year_rows.get(2022, {}).get(c01_col))
            c12 = _fmt(year_rows.get(2024, {}).get(c12_col))
            line += f"  {c01:>8}  {c12:>8}"
        lines.append(line)

    sector_lines = []
    sector_lines.append(f"\nSector Average:")
    sector_lines.append(f"{'Metric':<36} {'2022':>10} {'2023':>10} {'2024':>10}")
    sector_lines.append("-" * 68)
    for ratio in ratios:
        label = labels[ratio]
        sv22 = _fmt(sector_rows.get(2022, {}).get(f"sector_avg_{ratio}"))
        sv23 = _fmt(sector_rows.get(2023, {}).get(f"sector_avg_{ratio}"))
        sv24 = _fmt(sector_rows.get(2024, {}).get(f"sector_avg_{ratio}"))
        sector_lines.append(f"{label:<36} {sv22:>10} {sv23:>10} {sv24:>10}")

    return "\n".join(lines) + "\n" + "\n".join(sector_lines)


def generate_insight(client, name, sector, section_key, table_str):
    prompt = (
        f"Company: {name} | Sector: {sector}\n\n"
        f"{section_key.capitalize()} Ratios — 3 Year Trend:\n"
        f"{table_str}\n\n"
        f"Write your {section_key} insight."
    )
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def main():
    ratios_df = pd.read_csv("data/ratios.csv")

    existing = set()
    if os.path.exists("data/insights.csv"):
        existing_df = pd.read_csv("data/insights.csv")
        existing = set(zip(existing_df["ticker"], existing_df["section"]))
        print(f"Resuming — {len(existing_df)} insights already saved.")

    companies = (
        ratios_df[ratios_df["ticker"] != "SECTOR_AVG"][["ticker", "name", "sector"]]
        .drop_duplicates()
        .sort_values("name")
        .reset_index(drop=True)
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results = []
    total = len(companies)

    for idx, company_row in companies.iterrows():
        ticker = company_row["ticker"]
        name = company_row["name"]
        sector = company_row["sector"]

        company_data = ratios_df[
            (ratios_df["ticker"] == ticker)
        ].to_dict("records")

        # sector_avg_* columns are already on each company row
        # pass company_data as sector source so build_table can read sector_avg_* fields
        sector_data = company_data

        for section_key, section_def in SECTIONS.items():
            if (ticker, section_key) in existing:
                print(f"[{idx + 1}/{total}] {name} — {section_key} (skipped)")
                continue

            try:
                table_str = build_table(company_data, section_key, section_def, sector_data)
                insight = generate_insight(client, name, sector, section_key, table_str)
                status = "✓"
            except Exception as e:
                insight = "Insight unavailable."
                status = f"✗ ({e})"

            results.append({
                "ticker": ticker,
                "name": name,
                "section": section_key,
                "insight": insight,
            })
            print(f"[{idx + 1}/{total}] {name} — {section_key} {status}")

            if results:
                new_df = pd.DataFrame(results)
                if os.path.exists("data/insights.csv") and existing:
                    old_df = pd.read_csv("data/insights.csv")
                    combined = pd.concat([old_df, new_df], ignore_index=True)
                    combined.drop_duplicates(subset=["ticker", "section"], keep="last").to_csv(
                        "data/insights.csv", index=False
                    )
                else:
                    new_df.to_csv("data/insights.csv", index=False)

            time.sleep(0.5)

    print(f"\nDone. Saved data/insights.csv")


if __name__ == "__main__":
    main()
