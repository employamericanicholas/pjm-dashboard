import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PJM 2025 Market Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .kpi-box {
        background: #1e2130;
        border: 1px solid #2e3250;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
    .kpi-label { font-size: 12px; color: #9aa0b4; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #f0f2f6; line-height: 1.1; }
    .kpi-delta-up { font-size: 13px; color: #f4a261; margin-top: 4px; }
    .kpi-delta-down { font-size: 13px; color: #52b788; margin-top: 4px; }
    .kpi-delta-warn { font-size: 13px; color: #e07a5f; margin-top: 4px; }
    .callout { background: #1e2130; border-left: 4px solid #f4a261; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #d0d3e0; }
    .callout-red { background: #1e2130; border-left: 4px solid #e07a5f; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #d0d3e0; }
    .callout-green { background: #1e2130; border-left: 4px solid #52b788; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #d0d3e0; }
    div[data-testid="stTab"] button { font-size: 15px; }
</style>
""", unsafe_allow_html=True)

CHART_THEME = "plotly_dark"
PLOT_BG = "#0e1117"
GRID_COLOR = "#2e3250"

def styled_chart(fig, height=420):
    fig.update_layout(
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color="#c9cdd8"),
        height=height,
        margin=dict(l=16, r=16, t=40, b=16),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig

def kpi(label, value, delta=None, delta_type="up"):
    arrow = "▲" if "+" in (delta or "") else "▼"
    delta_class = {"up": "kpi-delta-up", "down": "kpi-delta-down", "warn": "kpi-delta-warn"}.get(delta_type, "kpi-delta-up")
    delta_html = f'<div class="{delta_class}">{arrow} {delta}</div>' if delta else ""
    return f"""
    <div class="kpi-box">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>"""

# ── Data ───────────────────────────────────────────────────────────────────────

FUEL_COLORS = {
    "Gas": "#F4A261",
    "Coal": "#4A4E69",
    "Nuclear": "#E07A5F",
    "Hydro": "#81B29A",
    "Wind": "#52B788",
    "Solar": "#FFD166",
    "Oil": "#A8956A",
    "Waste": "#8B8B8B",
    "Battery": "#B5838D",
    "Biofuel": "#A8DADC",
}

# Historical load-weighted LMP $/MWh (1998–2025) — Table 3-38
lmp_historical = pd.DataFrame({
    "Year": list(range(1998, 2026)),
    "LMP": [24.16,34.07,30.72,36.65,31.60,41.23,44.34,63.46,53.35,61.66,
            71.13,39.05,48.35,45.94,35.23,38.66,53.14,36.16,29.23,30.99,
            38.24,27.32,21.77,39.78,80.14,31.08,33.74,50.73],
})

# Monthly LMP 2025 on/off peak — Table 3-39
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
lmp_monthly_2024 = [38.50,24.49,21.64,23.99,28.99,26.66,32.20,26.71,24.53,26.60,23.80,31.60]
lmp_monthly_2024_peak = [47.10,25.23,24.79,30.03,42.74,40.04,60.78,44.99,39.42,36.49,33.18,38.70]
lmp_monthly_2025 = [55.29,43.75,38.89,38.15,27.32,39.62,39.08,29.15,34.41,41.55,40.52,49.92]
lmp_monthly_2025_peak = [70.54,54.12,45.68,52.08,45.53,94.51,77.77,49.92,52.55,59.43,55.12,60.68]

lmp_monthly_df = pd.DataFrame({
    "Month": months * 4,
    "Year": ["2024"]*12 + ["2024"]*12 + ["2025"]*12 + ["2025"]*12,
    "Type": ["Off-Peak"]*12 + ["On-Peak"]*12 + ["Off-Peak"]*12 + ["On-Peak"]*12,
    "LMP": lmp_monthly_2024 + lmp_monthly_2024_peak + lmp_monthly_2025 + lmp_monthly_2025_peak,
})

# Generation by fuel (GWh) 2024 & 2025 — Table 3-63
gen_fuel = pd.DataFrame([
    {"Fuel": "Gas",      "GWh_2024": 376249.8, "GWh_2025": 373837.1, "Pct_2025": 42.8},
    {"Fuel": "Nuclear",  "GWh_2024": 272744.4, "GWh_2025": 270642.3, "Pct_2025": 31.0},
    {"Fuel": "Coal",     "GWh_2024": 122583.3, "GWh_2025": 145830.3, "Pct_2025": 16.7},
    {"Fuel": "Wind",     "GWh_2024": 31384.5,  "GWh_2025": 32156.2,  "Pct_2025": 3.7},
    {"Fuel": "Hydro",    "GWh_2024": 16001.4,  "GWh_2025": 15509.6,  "Pct_2025": 1.8},
    {"Fuel": "Solar",    "GWh_2024": 17547.7,  "GWh_2025": 24782.1,  "Pct_2025": 2.8},
    {"Fuel": "Oil",      "GWh_2024": 4098.6,   "GWh_2025": 5320.4,   "Pct_2025": 0.6},
    {"Fuel": "Waste",    "GWh_2024": 3912.1,   "GWh_2025": 3950.9,   "Pct_2025": 0.5},
    {"Fuel": "Biofuel",  "GWh_2024": 1249.4,   "GWh_2025": 1229.5,   "Pct_2025": 0.1},
    {"Fuel": "Battery",  "GWh_2024": 51.7,     "GWh_2025": 80.4,     "Pct_2025": 0.0},
])
gen_fuel["Change_Pct"] = ((gen_fuel["GWh_2025"] - gen_fuel["GWh_2024"]) / gen_fuel["GWh_2024"] * 100).round(1)

# Monthly generation by fuel 2025 — Table 3-64
monthly_gen = pd.DataFrame({
    "Month": months,
    "Coal":    [18584.7,12714.7,9375.7,9538.0,8603.3,13359.0,17631.6,12981.8,8619.7,9280.4,10312.7,14828.8],
    "Nuclear": [25031.1,21749.3,21593.7,20300.6,21890.2,23429.7,23878.6,23982.7,22274.5,20212.2,21869.0,24430.7],
    "Gas":     [33699.7,30340.4,27994.5,23473.1,25932.2,33888.3,41588.9,37031.7,33172.9,26876.6,26097.0,33741.8],
    "Wind":    [3907.9,3085.7,4259.4,3256.9,2656.6,1776.2,1088.0,1119.9,1058.9,2798.4,3433.7,3714.7],
    "Solar":   [1261.4,1308.6,2120.4,2397.3,2408.1,2804.2,2966.1,2792.1,2316.9,2037.2,1361.5,1008.3],
    "Hydro":   [1197.5,1221.5,1601.9,1272.6,1730.5,1881.7,1731.0,1181.3,878.9,723.5,955.8,1133.4],
    "Oil":     [668.6,303.8,183.2,306.9,268.4,570.3,914.6,478.4,441.9,388.9,403.2,392.1],
    "Waste":   [332.5,303.5,309.3,329.9,347.3,303.4,348.5,348.2,303.3,326.4,346.6,351.8],
})

# Installed capacity by fuel — Table 5-3 Dec 31 2025
capacity_fuel = pd.DataFrame([
    {"Fuel": "Gas",      "MW": 88888.4},
    {"Fuel": "Coal",     "MW": 37544.6},
    {"Fuel": "Nuclear",  "MW": 32176.2},
    {"Fuel": "Hydro",    "MW": 8215.2},
    {"Fuel": "Solar",    "MW": 8296.8},
    {"Fuel": "Wind",     "MW": 4370.6},
    {"Fuel": "Oil",      "MW": 4066.5},
    {"Fuel": "Waste",    "MW": 609.4},
    {"Fuel": "Battery",  "MW": 24.0},
])

# Zonal generation & load 2025 — Table 3-62
zones = pd.DataFrame([
    {"Zone": "ACEC",  "Full_Name": "Atlantic City Electric",      "State": "NJ", "Lat": 39.36, "Lon": -74.55, "Gen": 831,    "Load": 9649,   "Net": -8818},
    {"Zone": "AEP",   "Full_Name": "American Electric Power",     "State": "WV", "Lat": 38.95, "Lon": -82.10, "Gen": 164877, "Load": 137014, "Net": 27862},
    {"Zone": "APS",   "Full_Name": "Appalachian Power",           "State": "WV", "Lat": 37.27, "Lon": -81.22, "Gen": 49900,  "Load": 48976,  "Net": 924},
    {"Zone": "ATSI",  "Full_Name": "FirstEnergy (ATSI)",          "State": "OH", "Lat": 41.10, "Lon": -81.65, "Gen": 53435,  "Load": 66455,  "Net": -13020},
    {"Zone": "BGE",   "Full_Name": "Baltimore Gas & Electric",    "State": "MD", "Lat": 39.30, "Lon": -76.65, "Gen": 17496,  "Load": 30067,  "Net": -12572},
    {"Zone": "COMED", "Full_Name": "ComEd (Northern Illinois)",   "State": "IL", "Lat": 41.85, "Lon": -88.00, "Gen": 141514, "Load": 93042,  "Net": 48472},
    {"Zone": "DAY",   "Full_Name": "Dayton Power & Light",        "State": "OH", "Lat": 39.76, "Lon": -84.19, "Gen": 2679,   "Load": 17495,  "Net": -14817},
    {"Zone": "DUKE",  "Full_Name": "Duke Energy Ohio/KY",         "State": "OH", "Lat": 39.10, "Lon": -84.51, "Gen": 14183,  "Load": 26369,  "Net": -12186},
    {"Zone": "DOM",   "Full_Name": "Dominion Energy Virginia",    "State": "VA", "Lat": 37.54, "Lon": -77.44, "Gen": 107539, "Load": 130922, "Net": -23383},
    {"Zone": "DPL",   "Full_Name": "Delmarva Power & Light",      "State": "DE", "Lat": 38.91, "Lon": -75.53, "Gen": 5860,   "Load": 18489,  "Net": -12629},
    {"Zone": "DUQ",   "Full_Name": "Duquesne Light",              "State": "PA", "Lat": 40.44, "Lon": -79.99, "Gen": 16123,  "Load": 12915,  "Net": 3208},
    {"Zone": "EKPC",  "Full_Name": "East Kentucky Power",         "State": "KY", "Lat": 37.99, "Lon": -84.47, "Gen": 11116,  "Load": 14233,  "Net": -3117},
    {"Zone": "JCPLC", "Full_Name": "Jersey Central P&L",          "State": "NJ", "Lat": 40.36, "Lon": -74.29, "Gen": 9087,   "Load": 21585,  "Net": -12498},
    {"Zone": "MEC",   "Full_Name": "Metropolitan Edison (PA)",    "State": "PA", "Lat": 40.22, "Lon": -76.01, "Gen": 19538,  "Load": 14943,  "Net": 4596},
    {"Zone": "OVEC",  "Full_Name": "Ohio Valley Electric",        "State": "OH", "Lat": 38.73, "Lon": -82.99, "Gen": 11152,  "Load": 114,    "Net": 11038},
    {"Zone": "PECO",  "Full_Name": "PECO Energy (Philadelphia)",  "State": "PA", "Lat": 39.95, "Lon": -75.15, "Gen": 74893,  "Load": 38190,  "Net": 36704},
    {"Zone": "PE",    "Full_Name": "PENELEC (West/Central PA)",   "State": "PA", "Lat": 41.12, "Lon": -78.43, "Gen": 30432,  "Load": 16257,  "Net": 14175},
    {"Zone": "PEPCO", "Full_Name": "Pepco (DC/MD)",               "State": "MD", "Lat": 38.91, "Lon": -77.04, "Gen": 12080,  "Load": 27807,  "Net": -15727},
    {"Zone": "PPL",   "Full_Name": "PPL Electric (PA)",           "State": "PA", "Lat": 40.60, "Lon": -75.48, "Gen": 75239,  "Load": 40502,  "Net": 34737},
    {"Zone": "PSEG",  "Full_Name": "PSE&G (NJ)",                  "State": "NJ", "Lat": 40.73, "Lon": -74.17, "Gen": 42917,  "Load": 41970,  "Net": 947},
    {"Zone": "REC",   "Full_Name": "Rockland Electric (NY/NJ)",   "State": "NJ", "Lat": 41.12, "Lon": -74.15, "Gen": 0,      "Load": 1402,   "Net": -1402},
])
zones["Net_Status"] = zones["Net"].apply(lambda x: "Net Exporter" if x > 0 else "Net Importer")
zones["Abs_Net"] = zones["Net"].abs()

# BRA clearing prices (RTO) — Table 5-21
bra = pd.DataFrame([
    {"Delivery_Year": "2021/2022", "Price": 140.00},
    {"Delivery_Year": "2022/2023", "Price": 50.00},
    {"Delivery_Year": "2023/2024", "Price": 34.13},
    {"Delivery_Year": "2024/2025", "Price": 28.92},
    {"Delivery_Year": "2025/2026", "Price": 269.92},
    {"Delivery_Year": "2026/2027", "Price": 329.17},
    {"Delivery_Year": "2027/2028", "Price": 333.44},
])

# Cost per MWh 2024 vs 2025 — Tables 9–10
cost_df = pd.DataFrame([
    {"Category": "Energy",       "2024": 32.59, "2025": 49.28},
    {"Category": "Capacity",     "2024": 3.61,  "2025": 13.09},
    {"Category": "Transmission", "2024": 17.73, "2025": 18.53},
])

# Historical total real-time load GWh 2001–2025 — Table data line 1990
hist_load_years = list(range(2001, 2026))
hist_load_gwh = [265398, 312899, 327533, 438874, 684592, 696165, 715524,
                 698459, 666069, 697391, 723101, 764300, 773790, 780505,
                 776093, 778269, 758775, 791094, 771929, 742987, 767425,
                 778624, 755053, 784182, 810894]
hist_load_df = pd.DataFrame({"Year": hist_load_years, "GWh": hist_load_gwh})

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ PJM Dashboard")
    st.markdown("### 2025 State of the Market")
    st.markdown("**Published:** March 12, 2026")
    st.markdown("**Source:** Monitoring Analytics, LLC  \nIndependent Market Monitor for PJM")
    st.divider()
    st.markdown("**What is PJM?**")
    st.markdown(
        "PJM Interconnection operates the world's largest competitive electricity market "
        "serving 65 million people across 13 states + DC with ~184 GW of installed capacity."
    )
    st.divider()
    st.markdown("**Delivery Year:** June 1 – May 31")
    st.markdown("**Coverage:** DE, IL, IN, KY, MD, MI, NJ, NC, OH, PA, TN, VA, WV, DC")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "⚡ Energy Market",
    "🔋 Generation Mix",
    "🗺️ Zonal Analysis",
    "🏭 Capacity Market",
    "💰 Cost Analysis",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("## 2025 PJM State of the Market — At a Glance")
    st.markdown("*Data covers the PJM wholesale electricity market for calendar year 2025.*")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi("Total Energy Delivered", "810,894 GWh", "+3.4% vs 2024", "up"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Avg Real-Time LMP", "$50.73/MWh", "+50.4% vs 2024", "warn"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi("Peak Load", "158,789 MW", "+6.3% vs 2024", "warn"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Installed Capacity", "184,202 MW", "+2.5% vs 2024", "up"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi("Total Cost / MWh", "$82.67", "+51.0% vs 2024", "warn"), unsafe_allow_html=True)

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Historical Energy Prices (1998–2025)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=lmp_historical["Year"], y=lmp_historical["LMP"],
            mode="lines+markers", name="Annual Avg LMP",
            line=dict(color="#F4A261", width=2.5),
            marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(244,162,97,0.12)",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MWh<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[2025], y=[50.73],
            mode="markers", name="2025 (current)",
            marker=dict(size=12, color="#FFD166", symbol="star"),
        ))
        fig.update_layout(title="Real-Time Load-Weighted Average LMP", showlegend=True)
        st.plotly_chart(styled_chart(fig), use_container_width=True)

    with col_right:
        st.subheader("Key 2025 Findings")
        st.markdown("""
        <div class="callout-red">
        <b>Capacity Market Crisis:</b> PJM was short 6,517 MW in the 2027/2028 BRA.
        Capacity prices jumped from $28.92 to $333.44/MW-day in two years — a 1,053% increase.
        </div>
        <div class="callout">
        <b>Data Center Surge:</b> Data center load growth drove an irreversible $23.1B increase
        across the 2025/2026, 2026/2027, and 2027/2028 BRAs.
        </div>
        <div class="callout-green">
        <b>Solar Boom:</b> Solar generation surged +41.2% year-over-year (17,548 → 24,782 GWh).
        Installed solar capacity grew 64% in a single year.
        </div>
        <div class="callout">
        <b>Coal Comeback:</b> Coal generation rose +19.0% as high gas prices made coal more
        competitive. Coal went from 14.5% to 16.7% of generation mix.
        </div>
        <div class="callout-red">
        <b>Record Peak Load:</b> PJM set a new winter peak load record in 2025 — 158,789 MW,
        up 6.3% from the prior year.
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("PJM System Snapshot — 2024 vs 2025")
    snap = pd.DataFrame({
        "Metric": [
            "Total Real-Time Load (GWh)",
            "Avg Hourly Load (MWh)",
            "Peak Load (MWh)",
            "Installed Capacity (MW)",
            "Avg LMP ($/MWh)",
            "Energy Cost ($/MWh)",
            "Capacity Cost ($/MWh)",
            "Transmission Cost ($/MWh)",
            "Total Wholesale Cost ($/MWh)",
        ],
        "2024": ["784,182","94,787","149,398","179,656","$33.74","$32.59","$3.61","$17.73","$55.52"],
        "2025": ["810,894","98,613","158,789","184,202","$50.73","$49.28","$13.09","$18.53","$82.67"],
        "Change": ["+3.4%","+4.0%","+6.3%","+2.5%","+50.4%","+59.6%","+262.3%","+4.5%","+51.0%"],
    })
    st.dataframe(snap, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: ENERGY MARKET
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## Energy Market Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Historical Total Energy Delivered (GWh)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=hist_load_df["Year"], y=hist_load_df["GWh"] / 1000,
            name="Real-Time Load (TWh)",
            marker_color="#4A90D9",
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>%{y:.0f} TWh<extra></extra>"
        ))
        fig2.update_layout(title="Annual Real-Time Load (TWh)", yaxis_title="TWh")
        st.plotly_chart(styled_chart(fig2), use_container_width=True)

    with col2:
        st.subheader("Monthly LMP: On-Peak vs Off-Peak (2025)")
        df_2025 = lmp_monthly_df[lmp_monthly_df["Year"] == "2025"]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=months, y=df_2025[df_2025["Type"] == "Off-Peak"]["LMP"].values,
            name="Off-Peak", marker_color="#52B788",
        ))
        fig3.add_trace(go.Bar(
            x=months, y=df_2025[df_2025["Type"] == "On-Peak"]["LMP"].values,
            name="On-Peak", marker_color="#F4A261",
        ))
        fig3.update_layout(title="2025 Monthly LMP ($/MWh)", barmode="group", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig3), use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("2024 vs 2025 Monthly LMP Comparison")
        fig4 = go.Figure()
        avg_2024 = [(a+b)/2 for a, b in zip(lmp_monthly_2024, lmp_monthly_2024_peak)]
        avg_2025 = [(a+b)/2 for a, b in zip(lmp_monthly_2025, lmp_monthly_2025_peak)]
        fig4.add_trace(go.Scatter(x=months, y=avg_2024, name="2024 Avg LMP",
                                  line=dict(color="#81B29A", width=2, dash="dash")))
        fig4.add_trace(go.Scatter(x=months, y=avg_2025, name="2025 Avg LMP",
                                  line=dict(color="#F4A261", width=2.5),
                                  fill="tonexty", fillcolor="rgba(244,162,97,0.1)"))
        fig4.update_layout(title="Avg Monthly LMP: 2024 vs 2025 ($/MWh)", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig4), use_container_width=True)

    with col4:
        st.subheader("Price Distribution Context")
        price_ranges = ["<$0","$0–10","$10–20","$20–30","$30–40","$40–50",
                        "$50–75","$75–100","$100–200",">$200"]
        pct_2025 = [0.1, 1.1, 6.2, 19.3, 19.6, 13.5, 21.5, 8.4, 7.5, 2.8]
        fig5 = go.Figure(go.Bar(
            x=price_ranges, y=pct_2025, marker_color="#9B72CF",
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
        ))
        fig5.update_layout(title="2025 Hours by Price Range (%)", yaxis_title="% of Hours",
                           xaxis_tickangle=-30)
        st.plotly_chart(styled_chart(fig5), use_container_width=True)

    st.divider()
    st.subheader("Key Energy Market Statistics (2025)")
    ec1, ec2, ec3, ec4 = st.columns(4)
    with ec1:
        st.markdown(kpi("DA Avg LMP", "$47.11/MWh", "vs $31.41 in 2024", "warn"), unsafe_allow_html=True)
    with ec2:
        st.markdown(kpi("RT Avg LMP", "$46.93/MWh", "vs $31.32 in 2024", "warn"), unsafe_allow_html=True)
    with ec3:
        st.markdown(kpi("Peak Hour LMP", "$57.08/MWh", "vs $37.32 in 2024", "warn"), unsafe_allow_html=True)
    with ec4:
        st.markdown(kpi("Off-Peak LMP", "$38.08/MWh", "vs $26.08 in 2024", "warn"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: GENERATION MIX
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## Generation Mix & Installed Capacity")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Generation by Fuel Source — 2025 (GWh)")
        fig_pie = px.pie(
            gen_fuel, values="GWh_2025", names="Fuel",
            color="Fuel", color_discrete_map=FUEL_COLORS,
            hole=0.45,
        )
        fig_pie.update_traces(
            textposition="outside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} GWh<br>%{percent}<extra></extra>"
        )
        fig_pie.update_layout(title=f"Total: 873,339 GWh", showlegend=False)
        st.plotly_chart(styled_chart(fig_pie, height=450), use_container_width=True)

    with col2:
        st.subheader("Installed Capacity by Fuel — Dec 31, 2025 (MW)")
        fig_cap = px.pie(
            capacity_fuel, values="MW", names="Fuel",
            color="Fuel", color_discrete_map=FUEL_COLORS,
            hole=0.45,
        )
        fig_cap.update_traces(
            textposition="outside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} MW<br>%{percent}<extra></extra>"
        )
        fig_cap.update_layout(title="Total: 184,202 MW", showlegend=False)
        st.plotly_chart(styled_chart(fig_cap, height=450), use_container_width=True)

    st.divider()

    st.subheader("Monthly Generation by Fuel Source — 2025 (GWh)")
    fuels_to_show = ["Gas", "Nuclear", "Coal", "Wind", "Solar", "Hydro", "Oil", "Waste"]
    fig_area = go.Figure()
    for fuel in fuels_to_show:
        fig_area.add_trace(go.Bar(
            x=months, y=monthly_gen[fuel], name=fuel,
            marker_color=FUEL_COLORS.get(fuel, "#888"),
            hovertemplate=f"<b>{fuel}</b> %{{x}}: %{{y:,.0f}} GWh<extra></extra>"
        ))
    fig_area.update_layout(
        barmode="stack", title="Monthly Generation Stack (GWh)",
        yaxis_title="GWh", legend=dict(orientation="h", y=-0.15)
    )
    st.plotly_chart(styled_chart(fig_area, height=450), use_container_width=True)

    st.divider()

    st.subheader("Year-over-Year Generation Change by Fuel (2024 → 2025)")
    gen_sorted = gen_fuel.sort_values("Change_Pct")
    colors_change = ["#E07A5F" if x > 0 else "#52B788" for x in gen_sorted["Change_Pct"]]
    fig_bar = go.Figure(go.Bar(
        x=gen_sorted["Change_Pct"], y=gen_sorted["Fuel"],
        orientation="h",
        marker_color=colors_change,
        text=[f"{x:+.1f}%" for x in gen_sorted["Change_Pct"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Change: %{x:.1f}%<extra></extra>"
    ))
    fig_bar.update_layout(title="% Change in Generation Output vs 2024", xaxis_title="% Change")
    st.plotly_chart(styled_chart(fig_bar, height=380), use_container_width=True)

    st.divider()
    st.subheader("Detailed Generation Table: 2024 vs 2025")
    display_gen = gen_fuel.copy()
    display_gen["GWh_2024"] = display_gen["GWh_2024"].apply(lambda x: f"{x:,.0f}")
    display_gen["GWh_2025"] = display_gen["GWh_2025"].apply(lambda x: f"{x:,.0f}")
    display_gen["Change_Pct"] = display_gen["Change_Pct"].apply(lambda x: f"{x:+.1f}%")
    display_gen["Pct_2025"] = display_gen["Pct_2025"].apply(lambda x: f"{x:.1f}%")
    display_gen.columns = ["Fuel", "GWh (2024)", "GWh (2025)", "% of Total (2025)", "YoY Change"]
    st.dataframe(display_gen, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: ZONAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("## Zonal Analysis — PJM's 21 Control Zones")
    st.markdown("Each zone represents a utility service territory. Net exporters generate more than they consume locally; net importers rely on power flowing in from other zones.")

    col_map, col_info = st.columns([3, 1])

    with col_map:
        st.subheader("Zone Map: Net Generation/Load Balance")
        fig_map = go.Figure()
        exp = zones[zones["Net"] > 0]
        imp = zones[zones["Net"] < 0]
        fig_map.add_trace(go.Scattergeo(
            lat=exp["Lat"], lon=exp["Lon"],
            text=exp["Zone"],
            customdata=exp[["Full_Name", "Gen", "Load", "Net"]].values,
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=exp["Abs_Net"] / 1500 + 10,
                color="#52B788",
                opacity=0.85,
                line=dict(color="white", width=1),
            ),
            name="Net Exporter",
            hovertemplate=(
                "<b>%{text}</b><br>%{customdata[0]}<br>"
                "Generation: %{customdata[1]:,} GWh<br>"
                "Load: %{customdata[2]:,} GWh<br>"
                "Net Export: +%{customdata[3]:,} GWh<extra></extra>"
            )
        ))
        fig_map.add_trace(go.Scattergeo(
            lat=imp["Lat"], lon=imp["Lon"],
            text=imp["Zone"],
            customdata=imp[["Full_Name", "Gen", "Load", "Net"]].values,
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=imp["Abs_Net"] / 1500 + 10,
                color="#E07A5F",
                opacity=0.85,
                line=dict(color="white", width=1),
            ),
            name="Net Importer",
            hovertemplate=(
                "<b>%{text}</b><br>%{customdata[0]}<br>"
                "Generation: %{customdata[1]:,} GWh<br>"
                "Load: %{customdata[2]:,} GWh<br>"
                "Net Import: %{customdata[3]:,} GWh<extra></extra>"
            )
        ))
        fig_map.update_geos(
            scope="usa",
            projection_type="albers usa",
            showland=True, landcolor="#1e2130",
            showstates=True, statecolor="#2e3250",
            showcountries=False,
            bgcolor=PLOT_BG,
            center=dict(lat=39.5, lon=-80.0),
        )
        fig_map.update_layout(
            geo=dict(
                lataxis_range=[36, 43],
                lonaxis_range=[-92, -72],
            ),
            title="PJM Zones: Green = Net Exporter, Red = Net Importer (bubble = magnitude)",
            legend=dict(orientation="h", y=-0.05),
            paper_bgcolor=PLOT_BG,
            height=520,
            margin=dict(l=0, r=0, t=40, b=0),
            font=dict(color="#c9cdd8"),
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with col_info:
        st.subheader("System Totals")
        total_gen = zones["Gen"].sum()
        total_load = zones["Load"].sum()
        net_export = zones[zones["Net"] > 0]["Net"].sum()
        net_import = abs(zones[zones["Net"] < 0]["Net"].sum())
        st.markdown(kpi("Total Generation", f"{total_gen:,.0f} GWh"), unsafe_allow_html=True)
        st.markdown(kpi("Total Load", f"{total_load:,.0f} GWh"), unsafe_allow_html=True)
        st.markdown(kpi("Net Exporters", f"{len(zones[zones['Net'] > 0])} zones"), unsafe_allow_html=True)
        st.markdown(kpi("Net Importers", f"{len(zones[zones['Net'] < 0])} zones"), unsafe_allow_html=True)
        st.markdown("""
        <div class="callout">
        <b>Note:</b> PJM was a net exporter in 2025, sending 33,215 GWh more to neighboring grids than it received.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Generation vs Load by Zone (GWh, 2025)")
    zones_sorted = zones.sort_values("Gen", ascending=True)
    fig_zone_bar = go.Figure()
    fig_zone_bar.add_trace(go.Bar(
        y=zones_sorted["Zone"], x=zones_sorted["Gen"],
        name="Generation", orientation="h",
        marker_color="#4A90D9",
        hovertemplate="<b>%{y}</b> Gen: %{x:,.0f} GWh<extra></extra>"
    ))
    fig_zone_bar.add_trace(go.Bar(
        y=zones_sorted["Zone"], x=zones_sorted["Load"],
        name="Load", orientation="h",
        marker_color="#F4A261",
        hovertemplate="<b>%{y}</b> Load: %{x:,.0f} GWh<extra></extra>"
    ))
    fig_zone_bar.update_layout(
        barmode="group", title="Generation vs Load by Zone",
        xaxis_title="GWh",
        legend=dict(orientation="h", y=-0.08)
    )
    st.plotly_chart(styled_chart(fig_zone_bar, height=560), use_container_width=True)

    st.divider()
    st.subheader("Zonal Data Table (2025 GWh)")
    disp_zones = zones[["Zone", "Full_Name", "State", "Gen", "Load", "Net", "Net_Status"]].copy()
    disp_zones["Gen"] = disp_zones["Gen"].apply(lambda x: f"{x:,.0f}")
    disp_zones["Load"] = disp_zones["Load"].apply(lambda x: f"{x:,.0f}")
    disp_zones["Net"] = disp_zones["Net"].apply(lambda x: f"{x:+,.0f}")
    disp_zones.columns = ["Zone", "Full Name", "State", "Generation (GWh)", "Load (GWh)", "Net (GWh)", "Status"]
    st.dataframe(disp_zones, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: CAPACITY MARKET
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("## Capacity Market (RPM)")
    st.markdown(
        "PJM's capacity market (Reliability Pricing Model) ensures enough generation is available "
        "to meet future peak demand. Generators bid into Base Residual Auctions (BRAs) held ~3 years ahead."
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("BRA Clearing Prices — RTO System ($/MW-Day)")
        colors_bra = ["#E07A5F" if y >= "2025" else "#4A90D9" for y in bra["Delivery_Year"]]
        fig_bra = go.Figure(go.Bar(
            x=bra["Delivery_Year"], y=bra["Price"],
            marker_color=colors_bra,
            text=[f"${p:.2f}" for p in bra["Price"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MW-Day<extra></extra>"
        ))
        fig_bra.add_hline(y=28.92, line_dash="dash", line_color="#81B29A",
                          annotation_text="2024/25 low: $28.92", annotation_position="top left")
        fig_bra.update_layout(
            title="BRA Clearing Price Spike: $28.92 → $333.44/MW-Day",
            yaxis_title="$/MW-Day",
        )
        st.plotly_chart(styled_chart(fig_bra, height=400), use_container_width=True)

    with col2:
        st.subheader("Capacity Market Context")
        st.markdown("""
        <div class="callout-red">
        <b>+1,053%</b> increase in BRA clearing price from 2024/2025 to 2027/2028 ($28.92 → $333.44/MW-Day)
        </div>
        <div class="callout-red">
        <b>6,517 MW</b> short of reliability target in the 2027/2028 BRA
        </div>
        <div class="callout">
        <b>$14.9 billion</b> in RPM revenue for the 2025/2026 Delivery Year vs $2.6B in 2024/2025
        </div>
        <div class="callout">
        <b>$23.1 billion</b> total increase in BRA revenues driven by data center load growth across 2025/26, 2026/27, and 2027/28 BRAs
        </div>
        <div class="callout-green">
        <b>181,222 MW</b> total capacity entering delivery year June 1, 2025
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Installed Capacity by Fuel — 2025 Changes")
        cap_milestones = pd.DataFrame({
            "Fuel": ["Gas","Coal","Nuclear","Hydro","Solar","Wind","Oil","Waste","Battery"],
            "Jan_1":  [88760.5, 37793.7, 32179.9, 7674.7, 5046.5,  3594.8, 3965.9, 609.4, 21.5],
            "Dec_31": [88888.4, 37544.6, 32176.2, 8215.2, 8296.8,  4370.6, 4066.5, 609.4, 24.0],
        })
        cap_milestones["Change"] = cap_milestones["Dec_31"] - cap_milestones["Jan_1"]
        fig_cap_change = go.Figure()
        fig_cap_change.add_trace(go.Bar(
            x=cap_milestones["Fuel"], y=cap_milestones["Jan_1"] / 1000,
            name="Jan 1, 2025", marker_color="#4A4E69", opacity=0.8
        ))
        fig_cap_change.add_trace(go.Bar(
            x=cap_milestones["Fuel"], y=cap_milestones["Dec_31"] / 1000,
            name="Dec 31, 2025", marker_color="#F4A261", opacity=0.8
        ))
        fig_cap_change.update_layout(
            barmode="group", title="Installed Capacity Jan vs Dec 2025 (GW)",
            yaxis_title="GW"
        )
        st.plotly_chart(styled_chart(fig_cap_change), use_container_width=True)

    with col4:
        st.subheader("Reserve Margin (June 1, 2025)")
        required = 181222 + 205.1
        actual = 181222
        shortfall = 205.1
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=actual,
            delta={"reference": required, "valueformat": ",.0f", "prefix": "vs required "},
            title={"text": "UCAP (MW) — 205 MW short of reliability target"},
            gauge={
                "axis": {"range": [175000, 195000]},
                "bar": {"color": "#E07A5F"},
                "steps": [
                    {"range": [175000, 181017], "color": "#2e3250"},
                    {"range": [181017, 181427], "color": "#4A4E69"},
                ],
                "threshold": {"line": {"color": "#52B788", "width": 3}, "value": required},
            },
            number={"valueformat": ",.0f", "suffix": " MW"},
        ))
        fig_gauge.update_layout(paper_bgcolor=PLOT_BG, font=dict(color="#c9cdd8"), height=380)
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.divider()
    st.subheader("BRA Cleared Capacity (MW UCAP) by Delivery Year")
    cleared_mw = pd.DataFrame({
        "Delivery Year": ["2021/22","2022/23","2023/24","2024/25","2025/26","2026/27","2027/28"],
        "Cleared UCAP (MW)": [163627, 144477, 145067, 147482, 135684, 134205, 134478],
    })
    fig_cleared = go.Figure(go.Bar(
        x=cleared_mw["Delivery Year"], y=cleared_mw["Cleared UCAP (MW)"] / 1000,
        marker_color="#9B72CF",
        text=[f"{v/1000:.0f} GW" for v in cleared_mw["Cleared UCAP (MW)"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:.0f} GW cleared<extra></extra>"
    ))
    fig_cleared.update_layout(title="Total Cleared UCAP per BRA (GW)", yaxis_title="GW")
    st.plotly_chart(styled_chart(fig_cleared, height=350), use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: COST ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("## Wholesale Power Cost Analysis")
    st.markdown(
        "The total cost of wholesale power includes energy, capacity, and transmission components. "
        "In 2025 the total cost reached **$82.67/MWh**, a 51% increase over 2024."
    )

    cost_cols = st.columns(3)
    with cost_cols[0]:
        st.markdown(kpi("Energy Cost", "$49.28/MWh", "+59.6% vs $32.59 in 2024", "warn"), unsafe_allow_html=True)
    with cost_cols[1]:
        st.markdown(kpi("Capacity Cost", "$13.09/MWh", "+262.3% vs $3.61 in 2024", "warn"), unsafe_allow_html=True)
    with cost_cols[2]:
        st.markdown(kpi("Transmission Cost", "$18.53/MWh", "+4.5% vs $17.73 in 2024", "up"), unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cost Components: 2024 vs 2025")
        cost_melt = pd.melt(cost_df, id_vars="Category", var_name="Year", value_name="Cost")
        fig_cost = px.bar(
            cost_melt, x="Category", y="Cost", color="Year",
            barmode="group", text_auto=".2f",
            color_discrete_map={"2024": "#4A90D9", "2025": "#E07A5F"},
        )
        fig_cost.update_traces(texttemplate="$%{text}", textposition="outside")
        fig_cost.update_layout(title="$/MWh by Component: 2024 vs 2025", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig_cost), use_container_width=True)

    with col2:
        st.subheader("2025 Total Cost Composition")
        fig_pie_cost = px.pie(
            cost_df, values="2025", names="Category",
            color="Category",
            color_discrete_map={"Energy": "#F4A261", "Capacity": "#E07A5F", "Transmission": "#4A90D9"},
            hole=0.5,
        )
        fig_pie_cost.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>$%{value:.2f}/MWh<br>%{percent}<extra></extra>"
        )
        fig_pie_cost.update_layout(title="Total: $80.90/MWh (excl. other minor items)", showlegend=False)
        st.plotly_chart(styled_chart(fig_pie_cost), use_container_width=True)

    st.divider()
    st.subheader("What's Driving Costs Up?")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("""
        <div class="callout-red">
        <b>Capacity cost +262%:</b> The single biggest shock. Capacity went from 6.5% of the total cost in 2024 to 15.8% in 2025. The root cause is the data center load boom creating tight supply/demand in capacity auctions.
        </div>
        <div class="callout">
        <b>Energy cost +60%:</b> Driven by higher fuel costs and tighter supply. Gas and coal prices both increased in 2025. The real-time average LMP rose $17/MWh.
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="callout-green">
        <b>Transmission relatively stable:</b> Transmission cost rose only 4.5%, from $17.73 to $18.53/MWh — the least volatile component.
        </div>
        <div class="callout">
        <b>Impact on consumers:</b> Assuming ~810 TWh of annual load, the $27.15/MWh total increase in 2025 translates to roughly <b>$22 billion</b> in additional wholesale costs vs 2024.
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Historical Cost Breakdown — Key Years ($/MWh)")
    hist_cost = pd.DataFrame({
        "Year": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
        "Energy": [24.48, 19.57, 36.89, 73.53, 28.12, 32.59, 49.28],
        "Capacity": [5.89, 5.19, 3.72, 3.01, 4.44, 3.61, 13.09],
        "Transmission": [15.13, 15.01, 15.48, 16.64, 17.01, 17.73, 18.53],
    })
    fig_hist_cost = go.Figure()
    for col, color in [("Energy", "#F4A261"), ("Capacity", "#E07A5F"), ("Transmission", "#4A90D9")]:
        fig_hist_cost.add_trace(go.Bar(
            x=hist_cost["Year"], y=hist_cost[col],
            name=col, marker_color=color,
            hovertemplate=f"<b>{col}</b> %{{x}}: $%{{y:.2f}}/MWh<extra></extra>"
        ))
    fig_hist_cost.update_layout(
        barmode="stack",
        title="Total Wholesale Cost Stack ($/MWh)",
        yaxis_title="$/MWh",
        legend=dict(orientation="h", y=-0.12),
    )
    st.plotly_chart(styled_chart(fig_hist_cost, height=400), use_container_width=True)

st.divider()
st.markdown(
    "<div style='text-align:center;color:#6b7280;font-size:12px;'>"
    "Data Source: 2025 Annual State of the Market Report for PJM — Monitoring Analytics, LLC (Published March 12, 2026)"
    "</div>",
    unsafe_allow_html=True
)
