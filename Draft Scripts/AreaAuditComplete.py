# EXPECTED_INPUT_COLUMNS: CAName, ID, Coordinates, audited_area, latitude, longitude, geoinfo, successStatus, Response

# AI Updated Script - 2026-01-27 11:52:53 IST
# Author: Rahul Shetty
import requests, json, openpyxl, ast, time, subprocess
from RS_access_token_generate import get_bearer_token
from datetime import datetime

# CONFIG: isMultithreaded=False (Preserving sequential execution due to Excel modification)

start_time = datetime.now()

# ==============================
# 📄 Load Excel (Primary decides the path)
# ==============================
file_path = r"C:\Users\cropin\Documents\Important\Excel file\Auto Area Complete.xlsx"
print(f"📂 Loading Excel: {file_path}")

wk = openpyxl.load_workbook(file_path)
sh = wk["Area_Audit_Details"]
rows = sh.max_row

# ==============================
# 🔐 Get Access Token (pass Excel path here)
# ==============================
print("🔄 Requesting access token...")
token = get_bearer_token(file_path)
if not token:
    print("❌ Failed to retrieve token. Exiting.")
    exit()

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# ==============================
# Step 1 [LOGIC]: Detect Mode Automatically
# ==============================
any_coords = False
any_geo = False

for idx in range(4, rows + 1):
    ca_name = sh.cell(row=idx, column=1).value
    ca_id = sh.cell(row=idx, column=2).value
    coords = sh.cell(row=idx, column=3).value
    geo = sh.cell(row=idx, column=7).value

    if not ca_name or not ca_id:
        continue

    if coords:
        any_coords = True
    if geo:
        any_geo = True

# Decide mode
if not any_coords and not any_geo:
    mode = 1  # 1: generate coords
elif any_coords:
    mode = 2  # 2: use coords
else:
    mode = 3  # 3: use geo

print(f"🚦 Selected Mode: {mode}")

# ==============================
# Step 2 & 3 [LOGIC]: Mode 1 → Run Secondary Script & Reload
# ==============================
if mode == 1:
    print("▶️ Running RS_generate_coordinates.py to fill missing Coordinates...")
    # Step 2: Runs 'RS_generate_coordinates.py' as a subprocess
    subprocess.run(["python", "RS_generate_coordinates.py"], check=True)
    print("✅ Coordinates generated.")
    # Step 3: Reloads the Excel workbook
    wk = openpyxl.load_workbook(file_path)  # reload updated Excel
    sh = wk["Area_Audit_Details"]

# ==============================
# 🌐 Fetch env_url (base URL) directly from Excel
# ==============================
env_sheet = wk["Environment_Details"]
env_url = None

# Step 1: read the environment key
env_key = None
for r in range(2, env_sheet.max_row + 1):
    param = str(env_sheet.cell(row=r, column=1).value).strip()
    if param.lower() == "environment":
        env_key = str(env_sheet.cell(row=r, column=2).value).strip()
        break

# Step 2: fetch URL corresponding to that environment key
env_url = None
for r in range(2, env_sheet.max_row + 1):
    param = str(env_sheet.cell(row=r, column=1).value).strip()
    if param.lower() == env_key.lower():
        env_url = str(env_sheet.cell(row=r, column=2).value).strip()
        break

print(f"🌍 Using Base URL: {env_url}")

# Combine base URL with endpoints
putCAurl = f"{env_url}/services/farm/api/croppable-areas/area-audit"
geo_area_url = f"{env_url}/services/utilservice/api/geojson/area"
user_info = f"{env_url}/services/user/api/users/user-info"

# ==============================
# Step 4 [API]: Get Company Area Unit Preference (Run Once)
# ==============================

user_info_resp = requests.get(user_info,headers=headers)
user_info_resp.raise_for_status() # Ensure success before parsing unit_data
unit_data = user_info_resp.json()
company_unit = unit_data['companyPreferences']['areaUnits']
print(f"🎯 Company unit preference is {company_unit}")

# ==============================
# 🚀 Process Rows
# ==============================
for idx in range(4, rows + 1):
    ca_name = sh.cell(row=idx, column=1).value
    ca_id = sh.cell(row=idx, column=2).value
    cell_coordinates = sh.cell(row=idx, column=3)
    cell_areaAudit = sh.cell(row=idx, column=4)
    cell_latitude = sh.cell(row=idx, column=5)
    cell_longitude = sh.cell(row=idx, column=6)
    cell_geoinfo = sh.cell(row=idx, column=7)
    cell_SuccessOrFail = sh.cell(row=idx, column=8)
    cell_Response = sh.cell(row=idx, column=9)

    if not ca_name or not ca_id:
        print(f"🛑 Empty row at Row {idx}. Skipping.")
        continue

    print(f"\n🔹 Processing Row {idx} (Data {idx - 3}) | CA ID: {ca_id}")

    try:
        # Step 5 [LOGIC]: Extracts CA ID, name, coordinates, and geo-information based on detected mode.
        if mode == 2:  # Coordinates available
            coords = ast.literal_eval(cell_coordinates.value)
            geoinfo = None
        elif mode == 3:  # Geo available → convert to Coords
            geoinfo = json.loads(cell_geoinfo.value)
            # Conversion logic: extract coords from geoinfo
            coords = geoinfo["features"][0]["geometry"]["coordinates"][0]
            cell_coordinates.value = str(coords)  # save back coords
        else:  # Mode 1 (Coordinates should now be populated due to reload)
            coords = ast.literal_eval(cell_coordinates.value)
            geoinfo = None

        # Build payload for Step 6
        payload = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "coordinates": [coords],
                    "type": "MultiPolygon"
                }
            }]
        }

        # Step 6 [API]: Calculate Area and Center Coordinates (POST /geojson/area)
        geo_resp = requests.post(geo_area_url, headers=headers, json=payload)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        latitude = geo_data['latitude']
        longitude = geo_data['longitude']

        # Step 7 [LOGIC]: Converts 'auditedArea' to HECTARE if company unit preference is HECTARE.
        if company_unit == 'ACRE':
            # Assumes API response (geo_data['auditedArea']) is inherently in ACRES if preference is ACRE
            audited_area = geo_data['auditedArea']
        elif company_unit == 'HECTARE':
            # Conversion: ACRE to HECTARE (1 Hectare = 2.471 Acres)
            audited_area = geo_data['auditedArea']/2.471
        else:
            print(f"Warning: Unknown unit '{company_unit}'. Audited area defaulted to None.")
            audited_area = None
            
        geoinfo = json.dumps(payload)

        # Step 8 [LOGIC]: Writes calculated audited area, latitude, longitude, and geo-information back to the Excel row.
        cell_areaAudit.value = audited_area
        cell_latitude.value = latitude
        cell_longitude.value = longitude
        cell_geoinfo.value = geoinfo

        print(f"✅ GeoAPI | Area: {audited_area}, Lat: {latitude}, Lon: {longitude}")

        # Build CA payload for Step 9
        ca_data = {
            "id": ca_id,
            "cropAudited": True,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "auditedArea": {"count": float(audited_area)},
            "usableArea": {"count": float(audited_area)},
            "areaAudit": {
                "geoInfo": json.loads(geoinfo),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "channel": "mobile"
            }
        }

        # Step 9 [API]: Update Croppable Area Audit Information (PUT /area-audit)
        put_resp = requests.put(putCAurl, json=ca_data, headers=headers)

        if put_resp.status_code == 200:
            cell_SuccessOrFail.value = "Success"
            print(f"🎯 Success for CA ID {ca_id}")
        else:
            cell_SuccessOrFail.value = "Failed"
            resp_json = put_resp.json()
            title_msg = resp_json["title"]
            cell_Response.value = put_resp.text
            print(f"⚠️ Failed for CA ID {ca_id} | {put_resp.status_code} | {title_msg}")

    except Exception as e:
        print(f"❌ Error in Row {idx}: {str(e)}")
        cell_SuccessOrFail.value = "Failed"
        cell_Response.value = str(e)

    time.sleep(0.5)

# ==============================
# Step 10 [LOGIC]: Save Excel
# ==============================
wk.save(file_path)
print("\n📥 Excel updated & saved.")
print("🏁 Execution completed.")

end_time = datetime.now()
elapsed_time = end_time - start_time

print(f"Start Time : {start_time}")
print(f"End Time   : {end_time}")
print(f"Elapsed    : {elapsed_time}")