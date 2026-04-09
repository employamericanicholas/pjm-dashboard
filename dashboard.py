import os
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
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Montserrat:wght@600;700&display=swap');

    html, body, [class*="css"], .stApp, p, li, span, div {
        font-family: 'Lato', sans-serif !important;
        color: #0A0A0A;
    }
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #F9F7F5 !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #F9F7F5 !important;
    }
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        color: #191E3A !important;
    }
    .kpi-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #007BEA;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }
    .kpi-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; font-family: 'Montserrat', sans-serif !important; font-weight: 600; }
    .kpi-value { font-size: 26px; font-weight: 700; color: #191E3A; line-height: 1.1; font-family: 'Montserrat', sans-serif !important; }
    .kpi-delta-up { font-size: 12px; color: #EF8E48; margin-top: 4px; }
    .kpi-delta-down { font-size: 12px; color: #008A6A; margin-top: 4px; }
    .kpi-delta-warn { font-size: 12px; color: #BD2066; margin-top: 4px; }
    .callout { background: #EFF6FF; border-left: 4px solid #007BEA; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #191E3A; }
    .callout-red { background: #FEF2F2; border-left: 4px solid #BD2066; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #191E3A; }
    .callout-green { background: #F0FDF4; border-left: 4px solid #008A6A; border-radius: 4px; padding: 12px 16px; margin: 8px 0; font-size: 14px; color: #191E3A; }
    div[data-testid="stTab"] button { font-size: 14px; font-family: 'Montserrat', sans-serif !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

CHART_THEME = "plotly_white"
PLOT_BG = "#FFFFFF"
PAGE_BG = "#F9F7F5"
GRID_COLOR = "#EAE8E6"

# Employ America brand colors — primary
EA_BLUE        = "#007BEA"
EA_DARK_BLUE   = "#104591"
EA_DEEP_BLUE   = "#191E3A"
EA_GREEN       = "#008A6A"
EA_ORANGE      = "#EF8E48"
EA_WARM_WHITE  = "#F9F7F5"
# Employ America brand colors — extended (data visualization)
EA_LIGHT_BLUE  = "#DFE7E9"  # primary palette light blue
EA_VIZ_BLUE    = "#40B2FF"  # extended palette bright light blue
EA_DARK_NAVY   = "#123466"
EA_MED_BLUE    = "#296799"
EA_DARK_PURPLE = "#2E2A73"
EA_YELLOW      = "#EAC148"
EA_BRIGHT_ONG  = "#FF591F"
EA_PINK        = "#BD2066"
EA_PURPLE      = "#8A2B9C"

def styled_chart(fig, height=420):
    fig.update_layout(
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color="#222222", size=16),
        title_font=dict(size=18, color="#191E3A", family="Montserrat, sans-serif"),
        legend=dict(font=dict(size=15, color="#222222")),
        hoverlabel=dict(
            font=dict(size=15, color="#222222"),
            bgcolor="white",
            bordercolor="#aaaaaa",
        ),
        height=height,
        margin=dict(l=20, r=20, t=52, b=32),
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR,
        tickfont=dict(size=15, color="#222222"),
        title_font=dict(size=16, color="#222222"),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR,
        tickfont=dict(size=15, color="#222222"),
        title_font=dict(size=16, color="#222222"),
    )
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
    "Gas":     "#EF8E48",  # EA Orange
    "Nuclear": "#007BEA",  # EA Bright Blue
    "Coal":    "#0A0A0A",  # EA Black
    "Wind":    "#008A6A",  # EA Green
    "Solar":   "#EAC148",  # EA Yellow
    "Hydro":   "#104591",  # EA Blue (dark blue)
    "Oil":     "#FF591F",  # EA Bright Orange
    "Waste":   "#BD2066",  # EA Pink
    "Battery": "#8A2B9C",  # EA Bright Purple
    "Biofuel": "#2E2A73",  # EA Dark Purple
    "Other":   "#999999",
}

# EIA fuel code → display category
EIA_FUEL_MAP = {
    "NG": "Gas", "OG": "Gas", "BFG": "Gas", "PG": "Gas", "SG": "Gas", "LFG": "Biofuel",
    "NUC": "Nuclear",
    "BIT": "Coal", "SUB": "Coal", "LIG": "Coal", "RC": "Coal", "WC": "Coal", "PC": "Coal",
    "WND": "Wind",
    "SUN": "Solar",
    "WAT": "Hydro", "GEO": "Hydro",
    "DFO": "Oil", "RFO": "Oil", "JF": "Oil", "KER": "Oil",
    "MWH": "Battery",
    "AB": "Biofuel", "WDS": "Biofuel", "OBS": "Biofuel", "OBL": "Biofuel",
    "MSW": "Waste", "TDF": "Waste", "WH": "Waste",
}

@st.cache_data
def load_plant_data():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pjm_plants.csv")
    try:
        df = pd.read_csv(csv_path, dtype={"Plant Code": str})
    except FileNotFoundError:
        return pd.DataFrame()
    df["Fuel Type"] = df["Fuel Type"].map(EIA_FUEL_MAP).fillna("Other")
    df["Net Generation (MWh)"] = pd.to_numeric(df["Net Generation (MWh)"], errors="coerce").fillna(0)
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])
    # Sum generation by plant + fuel type
    group_cols = ["Plant Code", "Plant Name", "State", "Latitude", "Longitude", "Fuel Type"]
    if "Utility Name" in df.columns:
        group_cols.insert(2, "Utility Name")
    by_fuel = df.groupby(group_cols, as_index=False)["Net Generation (MWh)"].sum()
    # Total gen per plant
    totals = by_fuel.groupby("Plant Code", as_index=False)["Net Generation (MWh)"].sum()
    totals = totals.rename(columns={"Net Generation (MWh)": "Total MWh"})
    # Dominant fuel = highest-generation fuel type per plant
    idx = by_fuel.groupby("Plant Code")["Net Generation (MWh)"].idxmax()
    dominant = by_fuel.loc[idx, ["Plant Code", "Fuel Type"]].rename(columns={"Fuel Type": "Primary Fuel"})
    # One row per plant
    meta_cols = ["Plant Code", "Plant Name", "State", "Latitude", "Longitude"]
    if "Utility Name" in by_fuel.columns:
        meta_cols.insert(2, "Utility Name")
    meta = by_fuel.drop_duplicates("Plant Code")[meta_cols]
    return meta.merge(totals, on="Plant Code").merge(dominant, on="Plant Code")

@st.cache_data
def load_company_rankings():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pjm_plants.csv")
    try:
        df = pd.read_csv(csv_path, dtype={"Plant Code": str})
    except FileNotFoundError:
        return None
    if "Utility Name" not in df.columns:
        return None
    # Strict PJM BA filter — excludes TVA, MISO, Duke Carolinas, etc.
    # that are in PJM-adjacent states but not PJM's balancing authority
    if "BA Code" in df.columns:
        df = df[df["BA Code"].str.strip().str.upper() == "PJM"]
    df["Fuel Type"] = df["Fuel Type"].map(EIA_FUEL_MAP).fillna("Other")
    df["Net Generation (MWh)"] = pd.to_numeric(df["Net Generation (MWh)"], errors="coerce").fillna(0)
    # Company totals
    company = df.groupby("Utility Name", as_index=False)["Net Generation (MWh)"].sum()
    company = company.sort_values("Net Generation (MWh)", ascending=False).reset_index(drop=True)
    company["Rank"] = company.index + 1
    company["GWh"] = company["Net Generation (MWh)"] / 1000
    # Company x fuel breakdown
    by_fuel = df.groupby(["Utility Name", "Fuel Type"], as_index=False)["Net Generation (MWh)"].sum()
    by_fuel["GWh"] = by_fuel["Net Generation (MWh)"] / 1000
    return company, by_fuel

@st.cache_data
def load_ready_to_build():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pjm_ready_to_build.csv")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return pd.DataFrame()
    df["Latitude"]    = pd.to_numeric(df["Latitude"],    errors="coerce")
    df["Longitude"]   = pd.to_numeric(df["Longitude"],   errors="coerce")
    df["MW Capacity"] = pd.to_numeric(df["MW Capacity"], errors="coerce").fillna(0)
    return df.dropna(subset=["Latitude", "Longitude"])

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
    st.image("employ_america_logo.png")
    st.markdown("---")
    st.markdown("### PJM 2025 Market Dashboard")
    st.markdown("#### 2025 State of the Market")
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "📊 Overview",
    "⚡ Energy Market",
    "🔋 Generation Mix",
    "🗺️ Zonal Analysis",
    "🏭 Capacity Market",
    "💰 Cost Analysis",
    "📈 Historical Trends",
    "💬 Key Quotes",
    "🎯 Fun Facts",
    "🗺️ Generation Map",
    "🏆 Power Rankings",
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
            line=dict(color="#EF8E48", width=2.5),
            marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(244,162,97,0.12)",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MWh<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=[2025], y=[50.73],
            mode="markers", name="2025 (current)",
            marker=dict(size=12, color="#EF8E48", symbol="star"),
        ))
        fig.update_layout(title="Real-Time Load-Weighted Average LMP", showlegend=True)
        st.plotly_chart(styled_chart(fig), width='stretch')

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
    st.dataframe(snap, width='stretch', hide_index=True)

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
            marker_color="#007BEA",
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>%{y:.0f} TWh<extra></extra>"
        ))
        fig2.update_layout(title="Annual Real-Time Load (TWh)", yaxis_title="TWh")
        st.plotly_chart(styled_chart(fig2), width='stretch')

    with col2:
        st.subheader("Monthly LMP: On-Peak vs Off-Peak (2025)")
        df_2025 = lmp_monthly_df[lmp_monthly_df["Year"] == "2025"]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=months, y=df_2025[df_2025["Type"] == "Off-Peak"]["LMP"].values,
            name="Off-Peak", marker_color="#008A6A",
        ))
        fig3.add_trace(go.Bar(
            x=months, y=df_2025[df_2025["Type"] == "On-Peak"]["LMP"].values,
            name="On-Peak", marker_color="#EF8E48",
        ))
        fig3.update_layout(title="2025 Monthly LMP ($/MWh)", barmode="group", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig3), width='stretch')

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("2024 vs 2025 Monthly LMP Comparison")
        fig4 = go.Figure()
        avg_2024 = [(a+b)/2 for a, b in zip(lmp_monthly_2024, lmp_monthly_2024_peak)]
        avg_2025 = [(a+b)/2 for a, b in zip(lmp_monthly_2025, lmp_monthly_2025_peak)]
        fig4.add_trace(go.Scatter(x=months, y=avg_2024, name="2024 Avg LMP",
                                  line=dict(color="#008A6A", width=2, dash="dash")))
        fig4.add_trace(go.Scatter(x=months, y=avg_2025, name="2025 Avg LMP",
                                  line=dict(color="#EF8E48", width=2.5),
                                  fill="tonexty", fillcolor="rgba(244,162,97,0.1)"))
        fig4.update_layout(title="Avg Monthly LMP: 2024 vs 2025 ($/MWh)", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig4), width='stretch')

    with col4:
        st.subheader("Price Distribution Context")
        price_ranges = ["<$0","$0–10","$10–20","$20–30","$30–40","$40–50",
                        "$50–75","$75–100","$100–200",">$200"]
        pct_2025 = [0.1, 1.1, 6.2, 19.3, 19.6, 13.5, 21.5, 8.4, 7.5, 2.8]
        fig5 = go.Figure(go.Bar(
            x=price_ranges, y=pct_2025, marker_color="#104591",
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
        ))
        fig5.update_layout(title="2025 Hours by Price Range (%)", yaxis_title="% of Hours",
                           xaxis_tickangle=-30)
        st.plotly_chart(styled_chart(fig5), width='stretch')

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
            hole=0.42,
        )
        fig_pie.update_traces(
            textposition="inside",
            textinfo="percent",
            insidetextorientation="radial",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} GWh<br>%{percent}<extra></extra>"
        )
        fig_pie.update_layout(
            title="Total: 873,339 GWh",
            showlegend=True,
            legend=dict(orientation="v", x=1.0, font=dict(size=12)),
        )
        st.plotly_chart(styled_chart(fig_pie, height=460), width='stretch')

    with col2:
        st.subheader("Installed Capacity by Fuel — Dec 31, 2025 (MW)")
        fig_cap = px.pie(
            capacity_fuel, values="MW", names="Fuel",
            color="Fuel", color_discrete_map=FUEL_COLORS,
            hole=0.42,
        )
        fig_cap.update_traces(
            textposition="inside",
            textinfo="percent",
            insidetextorientation="radial",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} MW<br>%{percent}<extra></extra>"
        )
        fig_cap.update_layout(
            title="Total: 184,202 MW",
            showlegend=True,
            legend=dict(orientation="v", x=1.0, font=dict(size=12)),
        )
        st.plotly_chart(styled_chart(fig_cap, height=460), width='stretch')

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
    st.plotly_chart(styled_chart(fig_area, height=450), width='stretch')

    st.divider()

    st.subheader("Year-over-Year Generation Change by Fuel (2024 → 2025)")
    gen_sorted = gen_fuel.sort_values("Change_Pct")
    colors_change = ["#BD2066" if x > 0 else "#008A6A" for x in gen_sorted["Change_Pct"]]
    fig_bar = go.Figure(go.Bar(
        x=gen_sorted["Change_Pct"], y=gen_sorted["Fuel"],
        orientation="h",
        marker_color=colors_change,
        text=[f"{x:+.1f}%" for x in gen_sorted["Change_Pct"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Change: %{x:.1f}%<extra></extra>"
    ))
    fig_bar.update_layout(title="% Change in Generation Output vs 2024", xaxis_title="% Change")
    st.plotly_chart(styled_chart(fig_bar, height=380), width='stretch')

    st.divider()
    st.subheader("Detailed Generation Table: 2024 vs 2025")
    display_gen = gen_fuel.copy()
    display_gen["GWh_2024"] = display_gen["GWh_2024"].apply(lambda x: f"{x:,.0f}")
    display_gen["GWh_2025"] = display_gen["GWh_2025"].apply(lambda x: f"{x:,.0f}")
    display_gen["Change_Pct"] = display_gen["Change_Pct"].apply(lambda x: f"{x:+.1f}%")
    display_gen["Pct_2025"] = display_gen["Pct_2025"].apply(lambda x: f"{x:.1f}%")
    display_gen.columns = ["Fuel", "GWh (2024)", "GWh (2025)", "% of Total (2025)", "YoY Change"]
    st.dataframe(display_gen, width='stretch', hide_index=True)

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
                color="#008A6A",
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
                color="#BD2066",
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
            showland=True, landcolor="#e4ede4",
            showsubunits=True, subunitcolor="#aaaaaa",
            showcountries=False,
            bgcolor="#F9F7F5",
            center=dict(lat=39.5, lon=-81.0),
            lataxis_range=[36.2, 42.8],
            lonaxis_range=[-89.5, -73.5],
        )
        fig_map.update_layout(
            title="PJM Zones: Green = Net Exporter, Red = Net Importer (bubble = magnitude)",
            legend=dict(orientation="h", y=-0.05),
            paper_bgcolor=PLOT_BG,
            height=560,
            margin=dict(l=0, r=0, t=44, b=0),
            font=dict(color="#333333", size=14),
        )
        st.plotly_chart(fig_map, width='stretch')

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
        marker_color="#007BEA",
        hovertemplate="<b>%{y}</b> Gen: %{x:,.0f} GWh<extra></extra>"
    ))
    fig_zone_bar.add_trace(go.Bar(
        y=zones_sorted["Zone"], x=zones_sorted["Load"],
        name="Load", orientation="h",
        marker_color="#EF8E48",
        hovertemplate="<b>%{y}</b> Load: %{x:,.0f} GWh<extra></extra>"
    ))
    fig_zone_bar.update_layout(
        barmode="group", title="Generation vs Load by Zone",
        xaxis_title="GWh",
        legend=dict(orientation="h", y=-0.08)
    )
    st.plotly_chart(styled_chart(fig_zone_bar, height=560), width='stretch')

    st.divider()
    st.subheader("Zonal Data Table (2025 GWh)")
    disp_zones = zones[["Zone", "Full_Name", "State", "Gen", "Load", "Net", "Net_Status"]].copy()
    disp_zones["Gen"] = disp_zones["Gen"].apply(lambda x: f"{x:,.0f}")
    disp_zones["Load"] = disp_zones["Load"].apply(lambda x: f"{x:,.0f}")
    disp_zones["Net"] = disp_zones["Net"].apply(lambda x: f"{x:+,.0f}")
    disp_zones.columns = ["Zone", "Full Name", "State", "Generation (GWh)", "Load (GWh)", "Net (GWh)", "Status"]
    st.dataframe(disp_zones, width='stretch', hide_index=True)

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
        colors_bra = ["#BD2066" if y >= "2025" else "#007BEA" for y in bra["Delivery_Year"]]
        fig_bra = go.Figure(go.Bar(
            x=bra["Delivery_Year"], y=bra["Price"],
            marker_color=colors_bra,
            text=[f"${p:.2f}" for p in bra["Price"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MW-Day<extra></extra>"
        ))
        fig_bra.add_hline(y=28.92, line_dash="dash", line_color="#008A6A",
                          annotation_text="2024/25 low: $28.92", annotation_position="top left")
        fig_bra.update_layout(
            title="BRA Clearing Price Spike: $28.92 → $333.44/MW-Day",
            yaxis_title="$/MW-Day",
        )
        st.plotly_chart(styled_chart(fig_bra, height=400), width='stretch')

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
            name="Dec 31, 2025", marker_color="#EF8E48", opacity=0.8
        ))
        fig_cap_change.update_layout(
            barmode="group", title="Installed Capacity Jan vs Dec 2025 (GW)",
            yaxis_title="GW"
        )
        st.plotly_chart(styled_chart(fig_cap_change), width='stretch')

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
                "bar": {"color": "#BD2066"},
                "steps": [
                    {"range": [175000, 181017], "color": "#f0f0f0"},
                    {"range": [181017, 181427], "color": "#d8d8d8"},
                ],
                "threshold": {"line": {"color": "#008A6A", "width": 3}, "value": required},
            },
            number={"valueformat": ",.0f", "suffix": " MW"},
        ))
        fig_gauge.update_layout(paper_bgcolor=PLOT_BG, font=dict(color="#333333"), height=380)
        st.plotly_chart(fig_gauge, width='stretch')

    st.divider()
    st.subheader("BRA Cleared Capacity (MW UCAP) by Delivery Year")
    cleared_mw = pd.DataFrame({
        "Delivery Year": ["2021/22","2022/23","2023/24","2024/25","2025/26","2026/27","2027/28"],
        "Cleared UCAP (MW)": [163627, 144477, 145067, 147482, 135684, 134205, 134478],
    })
    fig_cleared = go.Figure(go.Bar(
        x=cleared_mw["Delivery Year"], y=cleared_mw["Cleared UCAP (MW)"] / 1000,
        marker_color="#104591",
        text=[f"{v/1000:.0f} GW" for v in cleared_mw["Cleared UCAP (MW)"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:.0f} GW cleared<extra></extra>"
    ))
    fig_cleared.update_layout(title="Total Cleared UCAP per BRA (GW)", yaxis_title="GW")
    st.plotly_chart(styled_chart(fig_cleared, height=350), width='stretch')

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
            barmode="group",
            color_discrete_map={"2024": "#007BEA", "2025": "#BD2066"},
        )
        fig_cost.update_traces(texttemplate="$%{y:.2f}", textposition="outside")
        fig_cost.update_layout(title="$/MWh by Component: 2024 vs 2025", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig_cost), width='stretch')

    with col2:
        st.subheader("2025 Total Cost Composition")
        fig_pie_cost = px.pie(
            cost_df, values="2025", names="Category",
            color="Category",
            color_discrete_map={"Energy": "#EF8E48", "Capacity": "#BD2066", "Transmission": "#007BEA"},
            hole=0.5,
        )
        fig_pie_cost.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>$%{value:.2f}/MWh<br>%{percent}<extra></extra>"
        )
        fig_pie_cost.update_layout(title="Total: $80.90/MWh (excl. other minor items)", showlegend=False)
        st.plotly_chart(styled_chart(fig_pie_cost), width='stretch')

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
    for col, color in [("Energy", "#EF8E48"), ("Capacity", "#BD2066"), ("Transmission", "#007BEA")]:
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
    st.plotly_chart(styled_chart(fig_hist_cost, height=400), width='stretch')

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: HISTORICAL TRENDS
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown("## Historical Trends")
    st.markdown("*Long-run perspective on PJM's evolution from 1998 to 2025.*")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Load-Weighted Average LMP (1998–2025)")
        fig_lmp_hist = go.Figure()
        fig_lmp_hist.add_trace(go.Scatter(
            x=lmp_historical["Year"], y=lmp_historical["LMP"],
            mode="lines+markers", name="Annual Avg LMP",
            line=dict(color="#EF8E48", width=2.5),
            marker=dict(size=5),
            fill="tozeroy", fillcolor="rgba(244,162,97,0.12)",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MWh<extra></extra>"
        ))
        fig_lmp_hist.add_annotation(x=2022, y=80.14, text="2022 peak<br>$80.14", showarrow=True, arrowhead=2, ax=40, ay=-30, font=dict(size=11))
        fig_lmp_hist.add_annotation(x=2025, y=50.73, text="2025<br>$50.73", showarrow=True, arrowhead=2, ax=-40, ay=-30, font=dict(size=11))
        fig_lmp_hist.update_layout(title="Real-Time LMP ($/MWh) — 28-Year History", yaxis_title="$/MWh")
        st.plotly_chart(styled_chart(fig_lmp_hist), width='stretch')

    with col2:
        st.subheader("Total Real-Time Load (2001–2025)")
        fig_load_hist = go.Figure(go.Bar(
            x=hist_load_df["Year"], y=hist_load_df["GWh"] / 1000,
            marker_color="#007BEA", opacity=0.85,
            hovertemplate="<b>%{x}</b><br>%{y:.0f} TWh<extra></extra>"
        ))
        fig_load_hist.add_annotation(x=2025, y=820, text="810.9 TWh (2025)", showarrow=True, arrowhead=2, ax=-50, ay=-30, font=dict(size=11))
        fig_load_hist.update_layout(title="Annual Energy Delivered (TWh)", yaxis_title="TWh")
        st.plotly_chart(styled_chart(fig_load_hist), width='stretch')

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Total Wholesale Cost Components (2019–2025)")
        hist_cost_7 = pd.DataFrame({
            "Year": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
            "Energy":       [24.48, 19.57, 36.89, 73.53, 28.12, 32.59, 49.28],
            "Capacity":     [5.89,  5.19,  3.72,  3.01,  4.44,  3.61,  13.09],
            "Transmission": [15.13, 15.01, 15.48, 16.64, 17.01, 17.73, 18.53],
        })
        fig_cost_hist7 = go.Figure()
        for col_name, color in [("Transmission", "#007BEA"), ("Capacity", "#BD2066"), ("Energy", "#EF8E48")]:
            fig_cost_hist7.add_trace(go.Bar(
                x=hist_cost_7["Year"], y=hist_cost_7[col_name],
                name=col_name, marker_color=color,
                hovertemplate=f"<b>{col_name}</b> %{{x}}: $%{{y:.2f}}/MWh<extra></extra>"
            ))
        fig_cost_hist7.update_layout(
            barmode="stack", title="Total Wholesale Cost Stack ($/MWh)",
            yaxis_title="$/MWh", legend=dict(orientation="h", y=-0.12)
        )
        st.plotly_chart(styled_chart(fig_cost_hist7), width='stretch')

    with col4:
        st.subheader("BRA Capacity Prices by Delivery Year")
        colors_bra7 = ["#007BEA" if y < "2025" else "#BD2066" for y in bra["Delivery_Year"]]
        fig_bra7 = go.Figure(go.Bar(
            x=bra["Delivery_Year"], y=bra["Price"],
            marker_color=colors_bra7,
            text=[f"${p:.0f}" for p in bra["Price"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>$%{y:.2f}/MW-Day<extra></extra>"
        ))
        fig_bra7.update_layout(title="BRA Clearing Price by Delivery Year ($/MW-Day)", yaxis_title="$/MW-Day")
        st.plotly_chart(styled_chart(fig_bra7), width='stretch')

    st.divider()
    st.subheader("Projected Reserve Margins (2025–2030)")
    reserve_proj = pd.DataFrame({
        "Year": ["2025/2026", "2026/2027", "2027/2028", "2028/2029", "2029/2030"],
        "Reserve_Margin_Pct": [19.9, 20.6, 17.6, 18.2, 14.4],
    })
    fig_reserve = go.Figure()
    fig_reserve.add_trace(go.Scatter(
        x=reserve_proj["Year"], y=reserve_proj["Reserve_Margin_Pct"],
        mode="lines+markers+text",
        name="Projected Reserve Margin",
        line=dict(color="#EF8E48", width=2.5),
        marker=dict(size=10),
        text=[f"{v:.1f}%" for v in reserve_proj["Reserve_Margin_Pct"]],
        textposition="top center",
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"
    ))
    fig_reserve.add_hline(y=17.8, line_dash="dash", line_color="#BD2066",
                          annotation_text="Required: 17.8%", annotation_position="bottom right")
    fig_reserve.update_layout(
        title="Projected Reserve Margin vs. Required (%) — Falling Below Target by 2029/30",
        yaxis_title="Reserve Margin (%)", yaxis_range=[10, 25]
    )
    st.plotly_chart(styled_chart(fig_reserve, height=380), width='stretch')

    st.divider()
    st.subheader("Year-Over-Year Key Metrics Summary")
    hist_summary = pd.DataFrame({
        "Metric": ["Avg LMP ($/MWh)", "Total Load (TWh)", "Total Cost/MWh ($)", "Capacity Cost/MWh ($)", "Congestion Cost ($M)", "Uplift Credits ($M)", "Gross Billings ($B)"],
        "2024": ["$33.74", "784.2", "$55.52", "$3.61", "$1,754", "$269", "$51.71"],
        "2025": ["$50.73", "810.9", "$82.67", "$13.09", "$3,174", "$765", "$80.49"],
        "YoY Change": ["+50.4%", "+3.4%", "+48.9%", "+262.3%", "+80.9%", "+183.4%", "+55.7%"],
    })
    st.dataframe(hist_summary, width='stretch', hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8: KEY QUOTES
# ══════════════════════════════════════════════════════════════════════════════
with tab8:
    st.markdown("## Key Quotes from the 2025 PJM State of the Market Report")
    st.markdown("*Direct quotes from Monitoring Analytics' independent assessment of PJM markets.*")

    quotes = [
        {"text": "The amount that PJM is short capacity grew from 208.7 MW in the 2026/2027 BRA to 6,516.6 MW in the 2027/2028 BRA.",
         "context": "Demonstrates the exponential growth of capacity shortfalls in a single year, driven by data center load forecasts.",
         "source": "Vol. 1 — Capacity Market"},
        {"text": "The total cost per MWh of wholesale power increased by $27.15 from $55.52 in 2024 to $82.67 in 2025, an increase of 48.9 percent.",
         "context": "The largest single-year cost increase since 2022, affecting every electricity consumer in the PJM footprint.",
         "source": "Vol. 1 — Table 9"},
        {"text": "In 2025, PJM had gross billings of $80.49 billion, an increase of 55.7 percent from $51.71 billion in 2024.",
         "context": "Nearly $29 billion added to the market's total settlement value in a single year — reflecting structural, not temporary, stress.",
         "source": "Vol. 1"},
        {"text": "Data center load growth is the core reliability issue facing PJM and the energy markets.",
         "context": "The explicit root cause identified by the Independent Market Monitor for almost every major market stress trend in 2025.",
         "source": "Vol. 1"},
        {"text": "Total Uplift Credits increased by $495.0 million, or 183.4 percent, from $268.6 million in 2024 to $764.8 million in 2025.",
         "context": "Uplift credits are payments to units that must run for reliability reasons despite being out-of-market. A near-tripling signals significant grid stress.",
         "source": "Vol. 1 — Table 1"},
        {"text": "In 2025, generation from coal units increased 19.0 percent, generation from natural gas units decreased 0.6 percent, generation from wind units increased 2.5 percent, and generation from solar units increased 41.2 percent compared to 2024.",
         "context": "Coal's unexpected resurgence alongside solar's explosion — two opposite energy trends happening simultaneously in the same market.",
         "source": "Vol. 1"},
        {"text": "The Polar Vortex 2025 (January 19–23, 2025) resulted in 44.3 percent of uplift credits in 2025.",
         "context": "A single five-day weather event in January generated 44% of the entire year's grid stress payments — $338 million in five days.",
         "source": "Vol. 2"},
        {"text": "The capacity market was short of meeting its reliability objective in the most recent capacity auctions.",
         "context": "A direct statement that PJM's auctions — the core mechanism designed to ensure future reliability — are failing their fundamental purpose.",
         "source": "Vol. 1"},
        {"text": "For the first time since the introduction of the RPM, wholesale power exceeded the cost of capacity. In the third quarter of 2025, significant increases in energy market costs resulted in the cost of transmission per MWh of wholesale power increasing above the cost of capacity for the first time.",
         "context": "A historic market reversal. Since PJM's capacity market launched, capacity had always been the dominant cost driver. Not anymore.",
         "source": "Vol. 1"},
        {"text": "PJM triggered shortage pricing on 147 five-minute intervals in 2025, across 28 days.",
         "context": "Shortage pricing is a rare emergency signal. At 28 days, it was occurring nearly every two weeks — a sign of structural grid adequacy stress.",
         "source": "Vol. 1"},
    ]

    for i, q in enumerate(quotes):
        col_q, col_ctx = st.columns([3, 2])
        with col_q:
            st.markdown(f"""
            <div style="background:#E8F0FB;border-left:5px solid #104591;border-radius:6px;
                        padding:16px 20px;margin:8px 0;font-size:15px;color:#333;font-style:italic;">
                "{q['text']}"
                <div style="font-size:12px;color:#888;margin-top:10px;font-style:normal;">
                    — {q['source']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_ctx:
            st.markdown(f"""
            <div style="background:#f0f5ff;border:1px solid #c5d8f0;border-radius:6px;
                        padding:14px 18px;margin:8px 0;font-size:13px;color:#444;">
                <b>Why it matters:</b><br>{q['context']}
            </div>
            """, unsafe_allow_html=True)
        if i < len(quotes) - 1:
            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9: FUN FACTS
# ══════════════════════════════════════════════════════════════════════════════
with tab9:
    st.markdown("## Fun Facts & Hidden Gems")
    st.markdown("*The most surprising findings buried in 500+ pages of market analysis — things you'd miss unless you read every word.*")

    facts = [
        {"number": "31×", "title": "Capacity shortage multiplied 31-fold in one year",
         "detail": "The shortfall grew from 208.7 MW to 6,516.6 MW between the 2026/2027 and 2027/2028 Base Residual Auctions. One year. Thirty-one times larger. Data center developers submitted massive new load forecasts that suddenly changed how much generation PJM needed to procure.",
         "color": "#BD2066"},
        {"number": "5 days", "title": "One polar vortex caused 44% of the entire year's grid stress payments",
         "detail": "The Polar Vortex of January 19–23, 2025 generated $338 million in uplift credits — 44.3% of the full year's $764.8M total. Five days in January cost as much as the remaining 360 days combined.",
         "color": "#007BEA"},
        {"number": "+19%", "title": "Coal made a major comeback",
         "detail": "After years of steady decline, coal generation surged 19% in 2025. High natural gas prices made coal economically competitive again. Coal's share of generation rose from 14.5% to 16.7%. The 'coal is dead' narrative got complicated.",
         "color": "#4A4E69"},
        {"number": "+41%", "title": "Solar generation exploded in a single year",
         "detail": "Solar output jumped 41.2% year-over-year (17,548 → 24,782 GWh). Installed solar capacity grew 64% during 2025 alone — from 5,047 MW to 8,297 MW. Solar is still only 2.8% of PJM's total generation, but it's accelerating faster than any other fuel type.",
         "color": "#EF8E48"},
        {"number": "1st time", "title": "Energy costs beat capacity for the first time in PJM history",
         "detail": "Since the Reliability Pricing Model launched, capacity costs had always been the dominant component. In Q3 2025, energy costs crossed above capacity costs for the first time ever — a historic reversal caused by fuel price spikes and tight supply.",
         "color": "#EF8E48"},
        {"number": "1,053%", "title": "Capacity auction prices jumped 10× in two years",
         "detail": "BRA clearing prices went from $28.92/MW-day (2024/2025) to $333.44/MW-day (2027/2028) — a 1,053% increase. For context, $28.92 was itself at a historic low. The $333.44 price is among the highest PJM has ever cleared.",
         "color": "#104591"},
        {"number": "$80.5B", "title": "PJM's total billings exceeded $80 billion in 2025",
         "detail": "PJM processed $80.49 billion in gross billings in 2025 — up $28.8 billion (55.7%) from $51.71 billion in 2024. That's roughly the annual GDP of a mid-sized U.S. state flowing through one grid operator's settlement system in a single year.",
         "color": "#008A6A"},
        {"number": "95.3%", "title": "The market was competitive on almost every day — despite the price spikes",
         "detail": "Even as prices reached record highs, PJM's energy market tested as competitive on 95.3% of days in 2025. The high prices were driven by real supply/demand conditions, not market power abuse. This is actually the market working — just painfully.",
         "color": "#008A6A"},
        {"number": "65M", "title": "PJM serves 65 million people across 13 states + DC",
         "detail": "PJM Interconnection is the world's largest competitive electricity market. It covers Delaware, Illinois, Indiana, Kentucky, Maryland, Michigan, New Jersey, North Carolina, Ohio, Pennsylvania, Tennessee, Virginia, West Virginia, and the District of Columbia.",
         "color": "#A8DADC"},
        {"number": "147", "title": "Shortage pricing triggered nearly every 2 weeks",
         "detail": "PJM triggered shortage pricing (prices spike to signal scarcity) on 147 five-minute intervals across 28 separate days in 2025. Shortage events are supposed to be rare emergencies. At 28 days, they happened roughly every other week — a sign of structural grid stress.",
         "color": "#BD2066"},
    ]

    for i in range(0, len(facts), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(facts):
                f = facts[i + j]
                with col:
                    st.markdown(f"""
                    <div style="background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;
                                padding:20px;margin:8px 0;min-height:190px;">
                        <div style="font-size:38px;font-weight:800;color:{f['color']};
                                    line-height:1.1;margin-bottom:6px;">{f['number']}</div>
                        <div style="font-size:15px;font-weight:600;color:#222;margin-bottom:10px;">
                            {f['title']}
                        </div>
                        <div style="font-size:13px;color:#555;line-height:1.5;">
                            {f['detail']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 10: GENERATION MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab10:
    st.markdown("## Individual Power Plant Map")
    st.markdown(
        "Each dot is one of ~3,800 power plants in the PJM region. "
        "Color = primary fuel type. Size = annual net generation. "
        "Source: EIA Form 860/923 (2023)."
    )

    df_plants_map = load_plant_data()

    if df_plants_map.empty:
        st.warning("Plant data file (pjm_plants.csv) not found. Run build_pjm_plants.py to generate it, then commit it to the repo.")
    else:
        df_rtb = load_ready_to_build()

        view_mode = st.radio(
            "Show on map:",
            ["All (operating + pipeline)", "Operating plants only", "Ready-to-build only"],
            horizontal=True, key="map_view_mode"
        )

        all_fuels = sorted(df_plants_map["Primary Fuel"].unique())
        sel_fuels = st.multiselect("Filter by fuel type:", all_fuels, default=all_fuels, key="plant_fuel_filter")

        show_operating = view_mode != "Ready-to-build only"
        show_rtb       = view_mode != "Operating plants only"

        df_show = df_plants_map[df_plants_map["Primary Fuel"].isin(sel_fuels)] if (show_operating and sel_fuels) else (df_plants_map if show_operating else pd.DataFrame())
        df_rtb_show = df_rtb[df_rtb["Fuel Category"].isin(sel_fuels)] if (show_rtb and not df_rtb.empty and sel_fuels) else (df_rtb if show_rtb else pd.DataFrame())

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Operating plants shown", f"{len(df_show):,}" if not df_show.empty else "—")
        col_b.metric("Generation (2023)", f"{df_show['Total MWh'].sum()/1e6:.0f} TWh" if not df_show.empty else "—")
        col_c.metric("Pipeline projects shown", f"{len(df_rtb_show):,}" if not df_rtb_show.empty else "—")
        col_d.metric("Pipeline capacity", f"{df_rtb_show['MW Capacity'].sum()/1000:.1f} GW" if not df_rtb_show.empty else "—")

        # Build scatter map — one trace per fuel type so legend works
        fig_plants = go.Figure()
        fuel_order = ["Gas", "Nuclear", "Coal", "Wind", "Solar", "Hydro", "Oil", "Waste", "Battery", "Biofuel", "Other"]

        # Layer 1: operating plants (circles) — only when df_show has data
        if not df_show.empty:
            max_mwh = df_show["Total MWh"].max() if df_show["Total MWh"].max() > 0 else 1
            op_group_titled = False
            for fuel in fuel_order:
                sub = df_show[df_show["Primary Fuel"] == fuel]
                if sub.empty:
                    continue
                color = FUEL_COLORS.get(fuel, "#999999")
                sizes = (sub["Total MWh"].clip(lower=0) / max_mwh * 16 + 4)
                group_title = dict(text="Operating Plants") if not op_group_titled else None
                op_group_titled = True
                fig_plants.add_trace(go.Scattergeo(
                    lat=sub["Latitude"],
                    lon=sub["Longitude"],
                    name=fuel,
                    legendgroup=fuel,
                    legendgrouptitle=group_title,
                    mode="markers",
                    marker=dict(
                        size=sizes,
                        color=color,
                        symbol="circle",
                        opacity=0.75,
                        line=dict(color="white", width=0.5),
                    ),
                    customdata=sub[["Plant Name", "State", "Total MWh"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                        f"Fuel: {fuel}<br>"
                        "Generation: %{customdata[2]:,.0f} MWh<extra></extra>"
                    ),
                ))

        # Layer 2: ready-to-build projects (stars)
        if not df_rtb_show.empty:
            max_mw = df_rtb_show["MW Capacity"].max() if df_rtb_show["MW Capacity"].max() > 0 else 1
            rtb_group_titled = False
            for fuel in fuel_order:
                sub = df_rtb_show[df_rtb_show["Fuel Category"] == fuel]
                if sub.empty:
                    continue
                color = FUEL_COLORS.get(fuel, "#999999")
                sizes = (sub["MW Capacity"].clip(lower=0) / max_mw * 14 + 7)
                group_title = dict(text="Ready to Build ★") if not rtb_group_titled else None
                rtb_group_titled = True
                fig_plants.add_trace(go.Scattergeo(
                    lat=sub["Latitude"],
                    lon=sub["Longitude"],
                    name=f"{fuel} (pipeline)",
                    legendgroup=f"rtb_{fuel}",
                    legendgrouptitle=group_title,
                    mode="markers",
                    marker=dict(
                        size=sizes,
                        color=color,
                        symbol="star",
                        opacity=0.92,
                        line=dict(color="white", width=1.2),
                    ),
                    customdata=sub[["Display Name", "State", "County", "MW Capacity", "Status"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b> (%{customdata[1]}, %{customdata[2]} County)<br>"
                        f"Fuel: {fuel}<br>"
                        "Capacity: %{customdata[3]:,.0f} MW<br>"
                        "Status: %{customdata[4]}<extra></extra>"
                    ),
                ))

        fig_plants.update_geos(
            scope="usa",
            projection_type="albers usa",
            showland=True, landcolor="#e8ede8",
            showsubunits=True, subunitcolor="#cccccc",
            showcoastlines=True, coastlinecolor="#aaaaaa",
            bgcolor="#F9F7F5",
            center=dict(lat=39.5, lon=-81.5),
            lataxis_range=[36.2, 43.2],
            lonaxis_range=[-90.0, -73.5],
        )
        fig_plants.update_layout(
            title="PJM Power Plants — Operating (circles) & Ready-to-Build Pipeline (stars)",
            paper_bgcolor=PLOT_BG,
            height=640,
            margin=dict(l=0, r=0, t=44, b=0),
            font=dict(color="#333333", size=14),
            legend=dict(
                title="Fuel Type",
                orientation="v",
                bgcolor="rgba(255,255,255,0.88)",
                bordercolor="#dddddd",
                borderwidth=1,
                groupclick="toggleitem",
            ),
        )
        st.plotly_chart(fig_plants, width='stretch')

        if not df_show.empty:
            st.divider()
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Generation by Fuel — EIA 2023")
                fuel_gen = df_show.groupby("Primary Fuel")["Total MWh"].sum().sort_values(ascending=True)
                fig_fuel_eia = go.Figure(go.Bar(
                    y=fuel_gen.index,
                    x=fuel_gen.values / 1e6,
                    orientation="h",
                    marker_color=[FUEL_COLORS.get(f, "#999999") for f in fuel_gen.index],
                    text=[f"{v/1e6:.1f} TWh" for v in fuel_gen.values],
                    textposition="outside",
                ))
                fig_fuel_eia.update_layout(xaxis_title="TWh", showlegend=False)
                st.plotly_chart(styled_chart(fig_fuel_eia, height=360), width='stretch')

            with col2:
                st.subheader("Plant Count by Fuel Type")
                fuel_count = df_show.groupby("Primary Fuel").size().sort_values(ascending=True)
                fig_count = go.Figure(go.Bar(
                    y=fuel_count.index,
                    x=fuel_count.values,
                    orientation="h",
                    marker_color=[FUEL_COLORS.get(f, "#999999") for f in fuel_count.index],
                    text=fuel_count.values,
                    textposition="outside",
                ))
                fig_count.update_layout(xaxis_title="Number of Plants", showlegend=False)
                st.plotly_chart(styled_chart(fig_count, height=360), width='stretch')

            st.divider()
            st.subheader("Top 20 Operating Plants by Generation (2023)")
            top20 = df_show.nlargest(20, "Total MWh")[["Plant Name", "State", "Primary Fuel", "Total MWh"]].copy()
            top20["Total MWh"] = top20["Total MWh"].apply(lambda x: f"{x:,.0f}")
            top20.columns = ["Plant Name", "State", "Fuel Type", "Net Generation (MWh)"]
            st.dataframe(top20, use_container_width=True, hide_index=True)

        if not df_rtb.empty:
            st.divider()
            st.subheader("Ready-to-Build Pipeline — PJM Interconnection Queue")
            st.markdown(
                "Projects with a signed interconnection agreement that are approved to build. "
                "**Note:** PJM's queue data lists project names, not developer company names. "
                "The 'Project Name' below is the developer's public commercial name. "
                "'Grid Owner' is the incumbent transmission company at the interconnection point — not the generator owner."
            )

            # Summary by status
            status_order = [
                "Under Construction",
                "Partially in Service - Under Construction",
                "Engineering and Procurement",
                "Suspended",
            ]
            status_summary = df_rtb.groupby("Status").agg(
                Projects=("Display Name", "count"),
                Total_MW=("MW Capacity", "sum"),
            ).reindex(status_order).dropna()
            status_summary["Total_MW"] = status_summary["Total_MW"].apply(lambda x: f"{x:,.0f} MW")
            status_summary.columns = ["# Projects", "Total Capacity"]
            st.dataframe(status_summary, use_container_width=True)

            st.markdown("**Full project list (sorted by capacity):**")
            rtb_display = df_rtb.sort_values("MW Capacity", ascending=False)[[
                "Display Name", "State", "County", "Fuel", "MW Capacity", "Status",
                "Transmission Owner", "Projected In Service Date",
            ]].copy()
            rtb_display["MW Capacity"] = rtb_display["MW Capacity"].apply(lambda x: f"{x:,.0f}")
            rtb_display.columns = [
                "Project Name", "State", "County", "Fuel", "MW Capacity",
                "Status", "Grid Owner", "Projected In-Service",
            ]
            st.dataframe(rtb_display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 11: POWER RANKINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab11:
    st.markdown("## 🏆 Power Rankings — Top Generators in PJM")
    st.markdown(
        "Which companies generated the most electricity in PJM? "
        "Ranked by total net generation (MWh) reported to EIA in 2023. "
        "Source: EIA Form 860/923."
    )

    rankings_result = load_company_rankings()

    if rankings_result is None:
        st.warning(
            "Company data not available. Re-run `build_pjm_plants.py` to regenerate "
            "`pjm_plants.csv` with Utility Name, then commit the updated CSV to the repo."
        )
    else:
        company_df, fuel_df = rankings_result

        top_n = st.slider("Show top N companies:", min_value=10, max_value=50, value=25, step=5)
        top = company_df.head(top_n).copy()

        # ── KPIs
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total companies", f"{len(company_df):,}")
        col_b.metric("Total generation (2023)", f"{company_df['GWh'].sum()/1000:.0f} TWh")
        col_c.metric("Top company share", f"{top.iloc[0]['GWh'] / company_df['GWh'].sum() * 100:.1f}%")

        # ── Main ranking bar chart
        fig_rank = go.Figure(go.Bar(
            y=top["Utility Name"],
            x=top["GWh"],
            orientation="h",
            marker=dict(
                color=top["GWh"],
                colorscale=[[0, EA_DARK_BLUE], [1, EA_BLUE]],
                showscale=False,
            ),
            text=[f"{v:,.0f} GWh" for v in top["GWh"]],
            textposition="outside",
            customdata=top[["Rank", "GWh"]].values,
            hovertemplate="<b>#%{customdata[0]} %{y}</b><br>%{customdata[1]:,.0f} GWh<extra></extra>",
        ))
        fig_rank.update_layout(
            title=f"Top {top_n} Power Generators in PJM — 2023 Net Generation (GWh)",
            xaxis_title="GWh",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(styled_chart(fig_rank, height=max(400, top_n * 26)), width='stretch')

        st.divider()

        # ── Fuel mix for top 10 companies
        st.subheader("Generation Mix — Top 10 Companies by Fuel Type")
        top10_names = company_df.head(10)["Utility Name"].tolist()
        fuel_top10 = fuel_df[fuel_df["Utility Name"].isin(top10_names)].copy()
        fuel_top10 = fuel_top10[fuel_top10["GWh"] > 0]

        fig_mix = px.bar(
            fuel_top10,
            y="Utility Name", x="GWh", color="Fuel Type",
            orientation="h",
            color_discrete_map=FUEL_COLORS,
            text=fuel_top10["GWh"].apply(lambda x: f"{x:,.0f}"),
        )
        fig_mix.update_traces(textposition="inside", insidetextanchor="middle")
        fig_mix.update_layout(
            title="Top 10 Companies — Generation by Fuel (GWh, 2023)",
            xaxis_title="GWh",
            yaxis=dict(autorange="reversed", categoryorder="total ascending"),
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(styled_chart(fig_mix, height=480), width='stretch')

        st.divider()

        # ── Full ranked table
        st.subheader("Full Rankings Table")
        table = company_df[["Rank", "Utility Name", "GWh"]].copy()
        table["GWh"] = table["GWh"].apply(lambda x: f"{x:,.0f}")
        table["Share of PJM Total"] = (
            company_df["Net Generation (MWh)"] / company_df["Net Generation (MWh)"].sum() * 100
        ).apply(lambda x: f"{x:.2f}%")
        table.columns = ["Rank", "Company", "Net Generation (GWh)", "Share of PJM Total"]
        st.dataframe(table, use_container_width=True, hide_index=True)

st.divider()
st.markdown(
    "<div style='text-align:center;color:#6b7280;font-size:12px;'>"
    "Data Source: 2025 Annual State of the Market Report for PJM — Monitoring Analytics, LLC (Published March 12, 2026)"
    "</div>",
    unsafe_allow_html=True
)
