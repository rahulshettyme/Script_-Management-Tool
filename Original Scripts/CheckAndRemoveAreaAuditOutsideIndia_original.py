# EXPECTED_INPUT_COLUMNS: CA_ID, CA_Name, Latitude, Longitude, is_outside_india, area_audit_status, area_audit_api_response

# AI Updated Script - 2026-02-01 10:43:56 IST
import zipfile
from pathlib import Path
import time
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm
import json # Added for API response parsing

from GetAuthtoken import get_access_token

# ================= CONFIGURATION & MAPPING =================
# Script Name: CheckAndRemoveAreaAuditOutsideIndia
# CONFIG: isMultithreaded=True
# CONFIG: batchSize=10

# OUTPUT MAPPING CONFIGURATION:
# - UI 'Name' Column: Map from 'CA_Name'.
# - UI 'Response' Column: Map from 'cropAudited =  false / true' to key 'API response'. Logic: put the response attribute cropAudited and its value.
# - UI 'Status' Column Logic: 
#   Success if response attribute 'cropAudited' = false
#   Fail if  response attribute 'cropAudited' = true
# - Excel Output Definition:
#   - Column 'is_outside_india': Set to '' (Logic: depending on the result of Download Natural Earth Countries Data comparision)
#   - Column 'area_audit_status': Set to '' (Logic: Success if response attribute 'cropAudited' = false / Fail if response attribute 'cropAudited' = true)
#   - Column 'area_audit_api_response': Set to '' (Logic: put the response attribute cropAudited and its value)
# ==========================================================

# ================= LEGACY CODE PRESERVATION =================

DOWNLOADS_DIR = Path(r"C:\Users\rajasekhar.palleti\Downloads\ne_data")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

NE_COUNTRIES_URL = "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip"

_INDIA_GEOM = None  # cache


def _download_zip(url: str, zip_path: Path, extract_dir: Path) -> None:
    # Step 1 [API]: Download Natural Earth Countries Data (Run Once logic)
    extract_dir.mkdir(parents=True, exist_ok=True)
    if any(extract_dir.glob("*.shp")):
        return

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        with open(zip_path, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=f"Downloading {zip_path.name}"
        ) as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)


def _load_india_geom():
    """Load India polygon geometry using Shapely 2.x union_all()."""
    global _INDIA_GEOM
    if _INDIA_GEOM is not None:
        return _INDIA_GEOM

    countries_zip = DOWNLOADS_DIR / "ne_50m_admin_0_countries.zip"
    countries_dir = DOWNLOADS_DIR / "ne_50m_admin_0_countries"
    _download_zip(NE_COUNTRIES_URL, countries_zip, countries_dir)

    shp_files = list(countries_dir.glob("*.shp"))
    if not shp_files:
        raise RuntimeError("Admin 0 countries shapefile missing after download.")

    gdf = gpd.read_file(shp_files[0])
    gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")

    # Step 2 [LOGIC]: Read shapefile, filter for 'India' and union geometries
    for col in ("ADM0_A3", "ISO_A3", "GU_A3", "WB_A3", "SOVEREIGNT", "ADMIN", "NAME"):
        if col in gdf.columns:
            if col in ("ADM0_A3", "ISO_A3", "GU_A3", "WB_A3"):
                tmp = gdf[gdf[col].str.upper() == "IND"]
            else:
                tmp = gdf[gdf[col].str.contains("India", case=False, na=False)]
            if not tmp.empty:
                _INDIA_GEOM = tmp.union_all()
                return _INDIA_GEOM

    raise RuntimeError("India polygon not found in shapefile.")


def process_india_check_and_area_audit_removal(
    input_path,
    ca_id_column,
    latitude_column,
    longitude_column,
    area_audit_delete_url,
    token,
    sleep_between_calls
):
    input_path = Path(input_path)
    output_path = input_path.with_name(
        f"{input_path.stem}_india_check_area_audit_processed.xlsx"
    )

    print("📂 Reading input Excel:", input_path)
    df = pd.read_excel(input_path)

    # Step 3 [LOGIC]: Read input Excel, convert lat/lon
    required_cols = [latitude_column, longitude_column, ca_id_column]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}")

    df[latitude_column] = pd.to_numeric(df[latitude_column], errors="coerce")
    df[longitude_column] = pd.to_numeric(df[longitude_column], errors="coerce")

    # -------- Add result columns --------
    df["is_outside_india"] = "INVALID"
    df["area_audit_status"] = ""
    df["area_audit_api_response"] = ""

    # -------- Load India geometry (Step 1 & 2 execution) --------
    india_geom = _load_india_geom()

    # Step 4 [LOGIC]: Create spatial points, check if point is within India
    geometries = [
        Point(lon, lat) if pd.notna(lat) and pd.notna(lon) else None
        for lat, lon in zip(df[latitude_column], df[longitude_column])
    ]

    gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")
    valid_mask = gdf["geometry"].notna()

    inside_mask = (
        gdf.loc[valid_mask, "geometry"].within(india_geom)
        | gdf.loc[valid_mask, "geometry"].touches(india_geom)
    )

    df.loc[valid_mask & inside_mask, "is_outside_india"] = "NO"
    df.loc[valid_mask & ~inside_mask, "is_outside_india"] = "YES" # Point is outside India

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Step 5 [API]: Area audit removal
    for index, row in df.iterrows():
        if row["is_outside_india"] != "YES":
            df.at[index, "area_audit_status"] = "SKIPPED"
            continue

        ca_id = row[ca_id_column]
        if pd.isna(ca_id) or str(ca_id).strip() == "":
            df.at[index, "area_audit_status"] = "Fail"
            df.at[index, "area_audit_api_response"] = "Missing CA ID"
            continue

        delete_url = area_audit_delete_url.format(ca_id=ca_id)
        print(f"🗑️ Deleting area audit for CA_ID: {ca_id}")

        try:
            response = requests.delete(delete_url, headers=headers, timeout=30)
            
            # Default values
            status = f"Fail (HTTP {response.status_code})"
            api_response_value = response.text 
            
            if response.status_code in (200, 204):
                
                if response.text:
                    try:
                        response_json = response.json()
                        crop_audited_status = response_json.get('cropAudited')

                        # Determine Status based on required logic (Success if False, Fail if True)
                        if crop_audited_status is False:
                            status = "Success"
                        elif crop_audited_status is True:
                            status = "Fail"
                        else:
                            # 200/204, but cannot determine final audit status based on payload key
                            status = "Fail (Audit Key Missing/Undefined)" 
                        
                        # Determine API Response value based on required format
                        if crop_audited_status is not None:
                            api_response_value = f"cropAudited = {crop_audited_status}"
                        else:
                            api_response_value = f"cropAudited = N/A (Key not found)"

                    except json.JSONDecodeError:
                        # 200/204 but not JSON (e.g., 204 No Content)
                        status = "Success (204 No Content)"
                        api_response_value = "cropAudited = N/A (204 No Content)"
                else:
                    # Pure 204 No Content case
                    status = "Success (204 No Content)"
                    api_response_value = "cropAudited = N/A (204 No Content)"
            
            # Apply results
            df.at[index, "area_audit_status"] = status
            df.at[index, "area_audit_api_response"] = api_response_value

        except requests.RequestException as e:
            df.at[index, "area_audit_status"] = "Fail (Connection Error)"
            df.at[index, "area_audit_api_response"] = str(e)

        time.sleep(sleep_between_calls)

    # Step 6 [LOGIC]: Save output
    print("💾 Writing final output:", output_path)
    df.to_excel(output_path, index=False)
    print("✅ Processing completed successfully")

    return output_path


# ================= MAIN =================

if __name__ == "__main__":

    INPUT_EXCEL = r"C:\Users\rajasekhar.palleti\Downloads\Andhra Pradesh  North Andhra.xlsx"
    CA_ID_COLUMN = "croppable_area_id"
    LATITUDE_COLUMN = "latitude"
    LONGITUDE_COLUMN = "longitude"
    SLEEP_BETWEEN_CALLS = 0.5  # seconds

    AREA_AUDIT_DELETE_URL = "https://cloud.cropin.in/services/farm/api/croppable-areas/{ca_id}/area-audit"

    print("🔐 Fetching access token...")
    token = get_access_token("mdlz", "9898989898", "9898989898", "prod1")

    if not token:
        print("❌ Failed to retrieve access token. Process terminated.")
        exit()

    print("✅ Access token retrieved. Starting execution...")

    process_india_check_and_area_audit_removal(
        INPUT_EXCEL,
        CA_ID_COLUMN,
        LATITUDE_COLUMN,
        LONGITUDE_COLUMN,
        AREA_AUDIT_DELETE_URL,
        token,
        SLEEP_BETWEEN_CALLS
    )