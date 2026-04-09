"""
EIA Power Plant Data Processor for PJM Region
Downloads EIA Form 860 (plant locations) and Form 923 (generation)
for 2023 and produces pjm_plants.csv
"""

import os
import io
import sys
import zipfile
import requests
import pandas as pd

OUTPUT_PATH = r"C:\Users\Nicholas Birkhead\ClaudeProjects\pjm_plants.csv"

# PJM states (used as a fallback filter if BA code match is incomplete)
PJM_STATES = {"PA", "NJ", "MD", "DE", "DC", "VA", "WV", "OH", "IN", "IL", "KY", "NC", "TN", "MI"}

# PJM balancing authority codes in EIA data
PJM_BA_CODES = {"PJM"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_zip(url: str, label: str) -> zipfile.ZipFile:
    """Download a ZIP from url and return an in-memory ZipFile."""
    print(f"Downloading {label} from:\n  {url}")
    try:
        resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        print(f"  Downloaded {len(resp.content)/1_048_576:.1f} MB")
        return zipfile.ZipFile(io.BytesIO(resp.content))
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return None


def find_file_in_zip(zf: zipfile.ZipFile, keywords: list[str], extensions: tuple = (".xlsx", ".xls")) -> str | None:
    """Return the first zip member whose name contains all keywords (case-insensitive)."""
    names = zf.namelist()
    print(f"  Files in archive: {names}")
    for name in names:
        lower = name.lower()
        if any(lower.endswith(ext) for ext in extensions):
            if all(kw.lower() in lower for kw in keywords):
                return name
    return None


# ---------------------------------------------------------------------------
# Step 1 – EIA-860 Plant Location
# ---------------------------------------------------------------------------

def load_eia860_plants(zf: zipfile.ZipFile) -> pd.DataFrame:
    """
    Read the plant-level file from EIA-860.
    Typical name: '2___Plant_Y2023.xlsx'
    Key columns: Plant Code, Plant Name, State, Latitude, Longitude,
                 Balancing Authority Code, Balancing Authority Name
    """
    # Try several keyword combos
    candidates = [
        ["plant", "y2023"],
        ["2___plant"],
        ["plant"],
    ]
    fname = None
    for kws in candidates:
        fname = find_file_in_zip(zf, kws)
        if fname:
            break

    if fname is None:
        print("  Could not locate plant file in EIA-860 ZIP.")
        return pd.DataFrame()

    print(f"  Reading plant file: {fname}")
    with zf.open(fname) as f:
        # Row 1 is usually a header/description row; actual headers on row 2 (0-indexed row 1)
        df = pd.read_excel(f, sheet_name=0, header=1, dtype=str)

    print(f"  Raw columns: {list(df.columns)}")
    print(f"  Raw shape: {df.shape}")

    # Normalise column names
    df.columns = [str(c).strip() for c in df.columns]

    # Rename to standard names (handle slight variations across years)
    rename_map = {
        "Plant Code": "Plant Code",
        "Utility ID": "Utility ID",
        "Utility Name": "Utility Name",
        "Plant Name": "Plant Name",
        "State": "State",
        "Latitude": "Latitude",
        "Longitude": "Longitude",
        "Balancing Authority Code": "BA Code",
        "Balancing Authority Name": "BA Name",
        # Sometimes spelled differently
        "BA Code": "BA Code",
        "BA Name": "BA Name",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Keep only useful columns that exist
    keep = [c for c in ["Plant Code", "Utility Name", "Plant Name", "State", "Latitude", "Longitude", "BA Code", "BA Name"] if c in df.columns]
    df = df[keep].copy()

    # Drop rows with no Plant Code
    df = df.dropna(subset=["Plant Code"])
    df["Plant Code"] = df["Plant Code"].str.strip().str.split(".").str[0]  # remove .0 suffix

    # Filter to PJM
    mask = pd.Series(False, index=df.index)
    if "BA Code" in df.columns:
        mask = mask | df["BA Code"].str.strip().str.upper().isin(PJM_BA_CODES)
    if "State" in df.columns:
        mask = mask | df["State"].str.strip().str.upper().isin(PJM_STATES)

    df_pjm = df[mask].copy()
    print(f"  PJM plants (860): {len(df_pjm)}")
    return df_pjm


# ---------------------------------------------------------------------------
# Step 2 – EIA-923 Generation
# ---------------------------------------------------------------------------

def load_eia923_generation(zf: zipfile.ZipFile) -> pd.DataFrame:
    """
    Read the generation fuel file from EIA-923.
    Typical name: 'EIA923_Schedules_2_3_4_5_M_12_2023_Final.xlsx' or similar.
    We want 'Page 1 Generation and Fuel Data' sheet.
    Columns of interest: Plant Id, Reported Prime Mover, Reported Fuel Type Code,
                         plus 12 monthly net generation columns.
    """
    candidates = [
        ["schedules_2_3_4_5"],
        ["schedules_2_3"],
        ["f923"],
        ["generation"],
    ]
    fname = None
    for kws in candidates:
        fname = find_file_in_zip(zf, kws)
        if fname:
            break

    # Fallback: pick the largest .xlsx (generation file is always the biggest)
    if fname is None:
        xlsx_files = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if xlsx_files:
            sizes = {n: zf.getinfo(n).file_size for n in xlsx_files}
            fname = max(sizes, key=sizes.get)
            print(f"  Fallback: using largest xlsx: {fname}")

    if fname is None:
        print("  Could not locate generation file in EIA-923 ZIP.")
        return pd.DataFrame()

    print(f"  Reading 923 file: {fname}")
    with zf.open(fname) as f:
        xl = pd.ExcelFile(f)
        print(f"  Sheets: {xl.sheet_names}")

        # Find the generation/fuel sheet
        gen_sheet = None
        for s in xl.sheet_names:
            sl = s.lower()
            if "generation" in sl or "page 1" in sl or "gen fuel" in sl:
                gen_sheet = s
                break
        if gen_sheet is None:
            gen_sheet = xl.sheet_names[0]
        print(f"  Using sheet: {gen_sheet}")

        # Header is typically on row 5 (0-indexed 4) for EIA-923
        for header_row in [4, 5, 1, 0]:
            df = pd.read_excel(xl, sheet_name=gen_sheet, header=header_row, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]
            # Check that we have a plant id column
            plant_col_candidates = [c for c in df.columns if "plant" in c.lower() and ("id" in c.lower() or "code" in c.lower())]
            if plant_col_candidates:
                print(f"  Found header at row {header_row}; plant col: {plant_col_candidates[0]}")
                break
        else:
            print("  WARNING: Could not determine header row for 923.")

    print(f"  Raw 923 columns: {list(df.columns)[:20]}")
    print(f"  Raw 923 shape: {df.shape}")

    # Find plant id column
    plant_id_col = next((c for c in df.columns if "plant" in c.lower() and "id" in c.lower()), None)
    if plant_id_col is None:
        plant_id_col = next((c for c in df.columns if "plant" in c.lower() and "code" in c.lower()), None)
    if plant_id_col is None:
        print("  ERROR: Cannot find plant ID column in 923 data.")
        return pd.DataFrame()

    # Find fuel type column
    fuel_col = next((c for c in df.columns if "fuel type" in c.lower() or "reported fuel" in c.lower()), None)
    if fuel_col is None:
        fuel_col = next((c for c in df.columns if "fuel" in c.lower()), None)

    # Find prime mover column
    pm_col = next((c for c in df.columns if "prime mover" in c.lower()), None)

    # Find net generation columns (monthly)
    # Typically: 'Net Generation\n(Megawatthours)' or 'Netgen January' etc.
    netgen_cols = [c for c in df.columns if "net gen" in c.lower() or "netgen" in c.lower()]
    if not netgen_cols:
        netgen_cols = [c for c in df.columns if "megawatt" in c.lower() or "mwh" in c.lower()]

    print(f"  Plant ID col: {plant_id_col}")
    print(f"  Fuel col: {fuel_col}")
    print(f"  Prime mover col: {pm_col}")
    print(f"  Net gen cols ({len(netgen_cols)}): {netgen_cols[:5]}...")

    # Build working dataframe
    keep_cols = [plant_id_col]
    if fuel_col:
        keep_cols.append(fuel_col)
    if pm_col:
        keep_cols.append(pm_col)
    keep_cols += netgen_cols

    df = df[[c for c in keep_cols if c in df.columns]].copy()
    df = df.rename(columns={plant_id_col: "Plant Code"})
    if fuel_col:
        df = df.rename(columns={fuel_col: "Fuel Type"})
    if pm_col:
        df = df.rename(columns={pm_col: "Prime Mover"})

    # Drop rows without plant code
    df = df.dropna(subset=["Plant Code"])
    df["Plant Code"] = df["Plant Code"].astype(str).str.strip().str.split(".").str[0]

    # Convert net gen columns to numeric and sum across months
    for c in netgen_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if netgen_cols:
        df["Net Generation (MWh)"] = df[[c for c in netgen_cols if c in df.columns]].sum(axis=1, skipna=True)
    else:
        df["Net Generation (MWh)"] = 0.0

    # Aggregate by Plant Code + Fuel Type (sum generation)
    group_cols = ["Plant Code"]
    if "Fuel Type" in df.columns:
        group_cols.append("Fuel Type")
    if "Prime Mover" in df.columns:
        group_cols.append("Prime Mover")

    df_agg = df.groupby(group_cols, as_index=False)["Net Generation (MWh)"].sum()
    print(f"  923 aggregated shape: {df_agg.shape}")
    return df_agg


# ---------------------------------------------------------------------------
# Step 3 – Join & Save
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("EIA PJM Plant Data Builder")
    print("=" * 60)

    # --- EIA-860 ---
    url_860 = "https://www.eia.gov/electricity/data/eia860/xls/eia8602023.zip"
    zf_860 = download_zip(url_860, "EIA-860 (2023)")
    if zf_860 is None:
        # Try alternate URL pattern
        url_860_alt = "https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602023.zip"
        zf_860 = download_zip(url_860_alt, "EIA-860 (2023) [alt]")

    df_plants = pd.DataFrame()
    if zf_860:
        df_plants = load_eia860_plants(zf_860)
    else:
        print("FAILED to download EIA-860. Cannot continue without plant locations.")
        sys.exit(1)

    # --- EIA-923 ---
    url_923 = "https://www.eia.gov/electricity/data/eia923/xls/f923_2023.zip"
    zf_923 = download_zip(url_923, "EIA-923 (2023)")
    if zf_923 is None:
        url_923_alt = "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2023.zip"
        zf_923 = download_zip(url_923_alt, "EIA-923 (2023) [alt]")

    df_gen = pd.DataFrame()
    if zf_923:
        df_gen = load_eia923_generation(zf_923)

    # --- Join ---
    if df_gen.empty:
        print("\nWARNING: No generation data. Saving plant-only CSV.")
        df_final = df_plants
    else:
        print("\nJoining plant locations with generation data...")
        # Filter generation to PJM plant codes only
        pjm_codes = set(df_plants["Plant Code"].astype(str))
        df_gen_pjm = df_gen[df_gen["Plant Code"].astype(str).isin(pjm_codes)].copy()
        print(f"  Generation rows matching PJM plants: {len(df_gen_pjm)}")

        df_final = df_plants.merge(df_gen_pjm, on="Plant Code", how="left")
        print(f"  Final joined shape: {df_final.shape}")

    # --- Save ---
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to: {OUTPUT_PATH}")
    print(f"Final shape: {df_final.shape}")
    print(f"Columns: {list(df_final.columns)}")
    print(f"\nSample rows:")
    print(df_final.head(5).to_string())

    # Summary stats
    if "Net Generation (MWh)" in df_final.columns:
        total_gen = df_final["Net Generation (MWh)"].sum()
        print(f"\nTotal PJM Net Generation 2023: {total_gen/1e9:.2f} TWh")
    if "Fuel Type" in df_final.columns:
        print("\nBreakdown by Fuel Type (top 10 by generation):")
        print(df_final.groupby("Fuel Type")["Net Generation (MWh)"].sum()
                      .sort_values(ascending=False).head(10).to_string())

    unique_plants = df_final["Plant Code"].nunique()
    print(f"\nUnique PJM plants: {unique_plants}")
    print("\nDone.")


if __name__ == "__main__":
    main()
