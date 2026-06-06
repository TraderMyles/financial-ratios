"""
DAX40 Financial Analyser — Streamlit app.
Reads data/ratios.csv and data/insights.csv. Zero external calls at runtime.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DAX40 Financial Analyser",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Ratio metadata ─────────────────────────────────────────────────────────────
SECTIONS = {
    "Profitability": {
        "ratios": ["gross_profit_margin", "operating_profit_margin", "roce"],
        "labels": {
            "gross_profit_margin": "Gross Profit Margin",
            "operating_profit_margin": "Operating Profit Margin",
            "roce": "ROCE",
        },
        "units": {
            "gross_profit_margin": "%",
            "operating_profit_margin": "%",
            "roce": "%",
        },
        "yoy_col": {
            "gross_profit_margin": "gpm_change_y1_y2",
            "operating_profit_margin": "opm_change_y1_y2",
            "roce": "roce_change_y1_y2",
        },
        "insight_key": "profitability",
    },
    "Solvency": {
        "ratios": ["gearing_ratio", "interest_cover"],
        "labels": {
            "gearing_ratio": "Gearing Ratio",
            "interest_cover": "Interest Cover",
        },
        "units": {
            "gearing_ratio": "%",
            "interest_cover": "x",
        },
        "yoy_col": {},
        "insight_key": "solvency",
    },
    "Liquidity": {
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
            "working_capital_cycle": "Working Capital Cycle",
        },
        "units": {
            "current_ratio": "x",
            "acid_ratio": "x",
            "trade_payables_days": "days",
            "trade_receivables_days": "days",
            "inventory_days": "days",
            "working_capital_cycle": "days",
        },
        "yoy_col": {},
        "insight_key": "liquidity",
    },
    "Investor": {
        "ratios": ["share_price", "eps", "dps", "dividend_yield", "pe_ratio"],
        "labels": {
            "share_price": "Share Price",
            "eps": "EPS",
            "dps": "DPS",
            "dividend_yield": "Dividend Yield",
            "pe_ratio": "P/E Ratio",
        },
        "units": {
            "share_price": "€",
            "eps": "€",
            "dps": "€",
            "dividend_yield": "%",
            "pe_ratio": "x",
        },
        "yoy_col": {
            "share_price": "share_price_change",
        },
        "insight_key": "investor",
    },
}

# higher = better for these; lower = better for others
HIGHER_IS_BETTER = {
    "gross_profit_margin", "operating_profit_margin", "roce",
    "interest_cover", "current_ratio", "acid_ratio",
    "trade_payables_days",
    "share_price", "eps", "dps", "dividend_yield",
}
LOWER_IS_BETTER = {
    "gearing_ratio", "trade_receivables_days", "inventory_days", "working_capital_cycle",
}

YEARS = [2022, 2023, 2024]


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    ratios = pd.read_csv("data/ratios.csv")
    ratios["year"] = ratios["year"].astype(int)
    try:
        insights = pd.read_csv("data/insights.csv")
    except FileNotFoundError:
        insights = pd.DataFrame(columns=["ticker", "name", "section", "insight"])
    return ratios, insights


# ── Helpers ────────────────────────────────────────────────────────────────────
def _v(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def fmt_val(val, unit):
    v = _v(val)
    if v is None:
        return "N/A"
    if unit == "€":
        return f"€{v:,.2f}"
    if unit == "%":
        return f"{v:.1f}%"
    if unit == "x":
        return f"{v:.2f}x"
    if unit == "days":
        return f"{v:.1f}"
    return f"{v:.2f}"


def delta_label(change, ratio):
    v = _v(change)
    if v is None:
        return None, None
    is_good = (ratio in HIGHER_IS_BETTER and v > 0) or (ratio in LOWER_IS_BETTER and v < 0)
    delta_str = f"{'+' if v >= 0 else ''}{v:.2f}"
    return delta_str, "normal" if is_good else "inverse"


def make_chart(ratio_label, company_vals, sector_vals, years=YEARS, unit=""):
    fig = go.Figure()

    y_company = [_v(company_vals.get(yr)) for yr in years]
    y_sector = [_v(sector_vals.get(yr)) for yr in years]

    has_company = any(v is not None for v in y_company)
    has_sector = any(v is not None for v in y_sector)

    if not has_company:
        return None

    fig.add_trace(go.Scatter(
        x=years,
        y=y_company,
        mode="lines+markers",
        name="Company",
        line=dict(color="#4F8EF7", width=2.5),
        marker=dict(size=7),
        hovertemplate=f"%{{y:.2f}}{unit}<extra>Company</extra>",
        connectgaps=True,
    ))

    if has_sector:
        fig.add_trace(go.Scatter(
            x=years,
            y=y_sector,
            mode="lines+markers",
            name="Sector Avg",
            line=dict(color="#888888", width=1.5, dash="dash"),
            marker=dict(size=5),
            hovertemplate=f"%{{y:.2f}}{unit}<extra>Sector Avg</extra>",
            connectgaps=True,
        ))

    fig.update_layout(
        template="plotly_dark",
        title=dict(text=ratio_label, font=dict(size=13), x=0),
        height=240,
        margin=dict(l=40, r=20, t=36, b=30),
        xaxis=dict(tickvals=years, ticktext=[str(y) for y in years], gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.0,
            xanchor="right", x=1,
            font=dict(size=11),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_insight(insights_df, ticker, section_key):
    row = insights_df[
        (insights_df["ticker"] == ticker) & (insights_df["section"] == section_key)
    ]
    if row.empty:
        st.markdown(
            "<div style='background:#1e2530;border-left:3px solid #555;padding:12px 16px;"
            "border-radius:4px;color:#888;font-style:italic;'>"
            "Run <code>insights.py</code> to generate AI analysis.</div>",
            unsafe_allow_html=True,
        )
        return

    text = row.iloc[0]["insight"]
    st.markdown(
        f"<div style='background:#0d1117;border-left:3px solid #4F8EF7;padding:14px 18px;"
        f"border-radius:4px;line-height:1.6;font-size:0.95rem;'>"
        f"<span style='color:#4F8EF7;font-size:0.8rem;font-weight:600;letter-spacing:0.05em;"
        f"text-transform:uppercase;'>AI Analysis</span><br><br>"
        f"{text}"
        f"<br><br><span style='color:#555;font-size:0.75rem;'>"
        f"Generated from 3-year financial data via Claude.</span></div>",
        unsafe_allow_html=True,
    )


# ── Main app ───────────────────────────────────────────────────────────────────
def main():
    if not __import__("os").path.exists("data/ratios.csv"):
        st.error(
            "No data found. Run the pipeline first:\n\n"
            "```\npython fetch_data.py\npython calculate.py\n```"
        )
        st.stop()

    ratios, insights = load_data()

    company_rows = (
        ratios[ratios["ticker"] != "SECTOR_AVG"][["ticker", "name", "sector"]]
        .drop_duplicates()
        .sort_values("name")
        .reset_index(drop=True)
    )
    company_names = company_rows["name"].tolist()
    tickers = company_rows["ticker"].tolist()

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<h2 style='font-size:1.4rem;margin-bottom:0;'>📊 DAX40 Analyser</h2>",
            unsafe_allow_html=True,
        )
        st.caption("Financial ratios · 2022 – 2024")
        st.divider()

        if "company_idx" not in st.session_state:
            st.session_state.company_idx = 0

        selected_name = st.selectbox(
            "Select company",
            company_names,
            index=st.session_state.company_idx,
            key="company_select",
        )
        st.session_state.company_idx = company_names.index(selected_name)

        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("← Prev", use_container_width=True):
                st.session_state.company_idx = (st.session_state.company_idx - 1) % len(company_names)
                st.rerun()
        with col_next:
            if st.button("Next →", use_container_width=True):
                st.session_state.company_idx = (st.session_state.company_idx + 1) % len(company_names)
                st.rerun()

        idx = st.session_state.company_idx
        ticker = tickers[idx]
        selected_name = company_names[idx]
        sector = company_rows.iloc[idx]["sector"]

        st.divider()
        st.markdown(f"**{selected_name}**")
        st.caption(f"{sector}  ·  `{ticker}`")
        st.divider()

        # Quick-glance 2024 metrics
        row_2024 = ratios[(ratios["ticker"] == ticker) & (ratios["year"] == 2024)]
        if not row_2024.empty:
            r = row_2024.iloc[0]
            st.markdown("<small><b>2024 Snapshot</b></small>", unsafe_allow_html=True)
            gpm = _v(r.get("gross_profit_margin"))
            opm = _v(r.get("operating_profit_margin"))
            roce = _v(r.get("roce"))
            cr = _v(r.get("current_ratio"))
            st.metric("GPM", f"{gpm:.1f}%" if gpm is not None else "N/A")
            st.metric("OPM", f"{opm:.1f}%" if opm is not None else "N/A")
            st.metric("ROCE", f"{roce:.1f}%" if roce is not None else "N/A")
            st.metric("Current Ratio", f"{cr:.2f}x" if cr is not None else "N/A")

    # ── Main area ──────────────────────────────────────────────────────────────
    st.markdown(f"## {selected_name}")
    st.caption(f"{sector}  ·  {ticker}")

    company_data = ratios[ratios["ticker"] == ticker]
    year_data = {int(r["year"]): r for _, r in company_data.iterrows()}

    tabs = st.tabs(list(SECTIONS.keys()))

    for tab, (section_name, section_def) in zip(tabs, SECTIONS.items()):
        with tab:
            ratio_list = section_def["ratios"]
            labels = section_def["labels"]
            units = section_def["units"]
            yoy_cols = section_def["yoy_col"]
            insight_key = section_def["insight_key"]

            row_2024_d = year_data.get(2024, {})

            # ── Metric cards ──────────────────────────────────────────────────
            num_metrics = len(ratio_list)
            metric_cols = st.columns(min(num_metrics, 4))

            for i, ratio in enumerate(ratio_list):
                with metric_cols[i % 4]:
                    val_2024 = _v(row_2024_d.get(ratio)) if row_2024_d else None
                    unit = units[ratio]
                    display = fmt_val(val_2024, unit)

                    change_col = yoy_cols.get(ratio)
                    delta_str, delta_color = None, None
                    if change_col:
                        raw_change = row_2024_d.get(change_col) if row_2024_d else None
                        delta_str, delta_color = delta_label(raw_change, ratio)
                    else:
                        val_2023 = _v(year_data.get(2023, {}).get(ratio)) if year_data.get(2023) is not None else None
                        if val_2024 is not None and val_2023 is not None:
                            change = val_2024 - val_2023
                            delta_str, delta_color = delta_label(change, ratio)

                    st.metric(
                        label=labels[ratio],
                        value=display,
                        delta=delta_str,
                        delta_color=delta_color or "off",
                    )

            st.divider()

            # ── Charts (2 per row) ────────────────────────────────────────────
            chart_ratios = [r for r in ratio_list if any(
                _v(year_data.get(yr, {}).get(r)) is not None for yr in YEARS
            )]

            if chart_ratios:
                for i in range(0, len(chart_ratios), 2):
                    chart_cols = st.columns(2)
                    for j, ratio in enumerate(chart_ratios[i:i + 2]):
                        with chart_cols[j]:
                            company_vals = {yr: year_data.get(yr, {}).get(ratio) for yr in YEARS}
                            sector_avg_col = f"sector_avg_{ratio}"
                            sector_vals = {yr: year_data.get(yr, {}).get(sector_avg_col) for yr in YEARS}
                            unit = units[ratio]
                            fig = make_chart(labels[ratio], company_vals, sector_vals, unit=unit)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # ── Insight block ─────────────────────────────────────────────────
            render_insight(insights, ticker, insight_key)


if __name__ == "__main__":
    main()
