"""
PJM Ready-to-Build Interconnection Queue Processor
Reads PJMReadytoBuild.xlsx, geocodes by county centroid (US Census gazetteer),
and saves pjm_ready_to_build.csv for the dashboard.
"""

import io
import zipfile
import requests
import pandas as pd

XLSX_PATH  = r"C:\Users\Nicholas Birkhead\ClaudeProjects\PJMReadytoBuild.xlsx"
OUTPUT_CSV = r"C:\Users\Nicholas Birkhead\ClaudeProjects\pjm_ready_to_build.csv"

GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2023_Gazetteer/2023_Gaz_counties_national.zip"
)

# PJM fuel → dashboard fuel category
FUEL_MAP = {
    "Natural Gas":    "Gas",
    "Solar":          "Solar",
    "Solar; Storage": "Solar",
    "Storage":        "Battery",
    "Wind":           "Wind",
    "Offshore Wind":  "Wind",
    "Hydro":          "Hydro",
    "Oil":            "Oil",
    "Nuclear":        "Nuclear",
    "Coal":           "Coal",
}


def load_county_centroids() -> pd.DataFrame:
    print(f"Downloading Census county gazetteer from:\n  {GAZETTEER_URL}")
    try:
        resp = requests.get(GAZETTEER_URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        print(f"  Downloaded {len(resp.content)/1024:.0f} KB")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return pd.DataFrame()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    txt_name = next(n for n in zf.namelist() if n.endswith(".txt"))
    print(f"  Reading: {txt_name}")
    with zf.open(txt_name) as f:
        counties = pd.read_csv(f, sep="\t", dtype=str)

    counties.columns = [c.strip() for c in counties.columns]
    print(f"  County columns: {list(counties.columns)}")
    print(f"  Rows: {len(counties)}")

    # Normalise
    counties["state"] = counties["USPS"].str.strip().str.upper()
    # NAME is like "Adams" — strip "County" suffix if present
    counties["county_clean"] = (
        counties["NAME"].str.strip()
        .str.replace(r"\s+County$", "", regex=True)
        .str.replace(r"\s+Parish$", "", regex=True)
        .str.upper()
    )
    counties["lat"] = pd.to_numeric(counties["INTPTLAT"].str.strip(), errors="coerce")
    counties["lon"] = pd.to_numeric(counties["INTPTLONG"].str.strip(), errors="coerce")
    return counties[["state", "county_clean", "lat", "lon"]]


def load_queue() -> pd.DataFrame:
    print(f"\nReading: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH, sheet_name="ReadytoBuild", dtype=str)
    print(f"  Rows: {len(df)}")

    # Normalise key columns
    df["State"]  = df["State"].str.strip().str.upper()
    df["County"] = df["County"].str.strip()
    df["Fuel"]   = df["Fuel"].str.strip()

    # Map fuel to dashboard category
    df["Fuel Category"] = df["Fuel"].map(FUEL_MAP).fillna("Other")

    # Numeric MW
    df["MW Capacity"] = pd.to_numeric(df["MW Capacity"], errors="coerce")
    df["MW Energy"]   = pd.to_numeric(df["MW Energy"],   errors="coerce")

    # Use Commercial Name if available, else fall back to Name
    df["Display Name"] = df["Commercial Name"].where(df["Commercial Name"].notna(), df["Name"])

    return df


def clean_county(val: str) -> str:
    """Strip common suffixes for matching."""
    if pd.isna(val):
        return ""
    return (
        str(val).strip()
        .replace(" County", "").replace(" Parish", "")
        .replace(" City", "").replace(" city", "")
        .upper()
    )


def main():
    print("=" * 60)
    print("PJM Ready-to-Build Geocoder")
    print("=" * 60)

    counties = load_county_centroids()
    if counties.empty:
        print("FAILED to load county centroids.")
        return

    df = load_queue()

    # Build county key for matching
    df["county_clean"] = df["County"].apply(clean_county)

    # Merge on state + county
    merged = df.merge(counties, left_on=["State", "county_clean"],
                      right_on=["state", "county_clean"], how="left")

    matched = merged["lat"].notna().sum()
    print(f"\nGeocoded: {matched} / {len(merged)} projects matched to a county centroid")

    # Report unmatched
    unmatched = merged[merged["lat"].isna()][["Project ID", "Display Name", "State", "County"]].drop_duplicates()
    if len(unmatched) > 0:
        print(f"\nUnmatched counties ({len(unmatched)}):")
        print(unmatched.to_string(index=False))

    # Add small random jitter so multiple projects in the same county don't perfectly overlap
    import numpy as np
    rng = np.random.default_rng(42)
    merged["Latitude"]  = merged["lat"]  + rng.uniform(-0.12, 0.12, len(merged))
    merged["Longitude"] = merged["lon"] + rng.uniform(-0.15, 0.15, len(merged))

    # Select output columns
    out = merged[[
        "Project ID", "Display Name", "State", "County",
        "Fuel", "Fuel Category", "MW Capacity", "MW Energy",
        "Status", "Transmission Owner",
        "Projected In Service Date",
        "Latitude", "Longitude",
    ]].copy()

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved to: {OUTPUT_CSV}")
    print(f"Final shape: {out.shape}")
    print(f"\nStatus breakdown:")
    print(out["Status"].value_counts().to_string())
    print(f"\nFuel category breakdown:")
    print(out["Fuel Category"].value_counts().to_string())
    print(f"\nSample:")
    print(out[["Display Name","State","County","Fuel Category","MW Capacity","Status","Latitude","Longitude"]].head(10).to_string())
    print("\nDone.")


if __name__ == "__main__":
    main()
