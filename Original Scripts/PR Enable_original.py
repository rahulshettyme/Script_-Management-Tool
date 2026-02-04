# Author: Rahul Shetty

import requests, json, openpyxl, time
from RS_access_token_generate import get_bearer_token
from datetime import datetime

start_time = datetime.now()

# ==============================
# 📄 Load Excel (Primary decides the path)
# ==============================
file_path = r"C:\Users\cropin\Documents\Important\Excel file\PR Enable.xlsx"
print(f"📂 Loading Excel: {file_path}")

wk = openpyxl.load_workbook(file_path)
sh = wk["Plot_details"]       # ✅ Sheet: Plot_details
rows = sh.max_row

# ==============================
# 🔐 Get Access Token
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
for r in range(2, env_sheet.max_row + 1):
    param = str(env_sheet.cell(row=r, column=1).value).strip()
    if param.lower() == env_key.lower():
        env_url = str(env_sheet.cell(row=r, column=2).value).strip()
        break

print(f"🌍 Using Base URL: {env_url}")

# Combine base URL with endpoint
API_URL = f"{env_url}/services/farm/api/croppable-areas/plot-risk/batch"


# ==============================
# 🚀 Process Excel and Send API
# ==============================
for r in range(2, rows + 1):
    croppable_area_id = sh.cell(row=r, column=1).value  # croppableAreaId
    ca_name = sh.cell(row=r, column=2).value
    farmer_id = sh.cell(row=r, column=3).value  # farmerId

    # Stop when croppableAreaId is empty
    if croppable_area_id is None or str(croppable_area_id).strip() == "":
        print(f"🛑 Empty row encountered at Row {r}. Stopping execution.")
        break

    payload = [{
        "croppableAreaId": int(croppable_area_id),
        "farmerId": None if farmer_id in [None, ""] else farmer_id
    }]

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        resp_json = response.json()
    except Exception as e:
        print(f"❌ Error at row {r}: {e}")
        sh.cell(row=r, column=4).value = "Failed"
        sh.cell(row=r, column=5).value = str(e)
        sh.cell(row=r, column=6).value = ""
        sh.cell(row=r, column=7).value = ""
        continue

    # Store full response
    sh.cell(row=r, column=7).value = json.dumps(resp_json, ensure_ascii=False)

    # ==============================
    # ✅ Extract details from nested srPlotDetails
    # ==============================
    sr_details = {}
    if isinstance(resp_json.get("srPlotDetails"), dict):
        # Typically only one key inside srPlotDetails (e.g. "5913503")
        sr_details = list(resp_json["srPlotDetails"].values())[0]

    error_val = sr_details.get("error")
    message_val = sr_details.get("message", "")
    srplot_id_val = sr_details.get("srPlotId", "")

    # Determine Success / Failure
    if error_val:
        status_val = "Failed"
    else:
        status_val = "Success"

    # Update Excel
    sh.cell(row=r, column=4).value = status_val
    sh.cell(row=r, column=5).value = message_val
    sh.cell(row=r, column=6).value = srplot_id_val

    # Console output
    print(f"➡️ Row {r} | CA_ID: {croppable_area_id} | Status: {status_val} | Message: {message_val} | SRPlotID: {srplot_id_val}")

# ==============================
# 💾 Save Excel
# ==============================
wk.save(file_path)
print(f"\n✅ Excel file '{file_path}' updated successfully.")
print("🏁 Execution completed.")

end_time = datetime.now()
elapsed_time = end_time - start_time

print(f"Start Time : {start_time}")
print(f"End Time   : {end_time}")
print(f"Elapsed    : {elapsed_time}")
