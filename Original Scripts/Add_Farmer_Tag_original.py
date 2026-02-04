# AI Updated - 2026-02-03 15:39:33 IST
import json
import requests
import time

"""
Script Name: Add Farmer Tag

UI Output Definition:
- UI Column 'Farmer Name': Set to '' (Logic: from excel)
- UI Column 'Farmer ID': Set to '' (Logic: from excel)
- UI Column 'Tag Name': Set to '' (Logic: from excel)
- UI Column 'Status': Set to '' (Logic: Pass if farmer update API status code is 200, else Fail)

Excel Output Definition:
- Column 'Tag ID': Set to '' (Logic: attribute 'id' from tag API response)
- Column 'Status': Set to '' (Logic: 'Fail' if tag not found or if status code of farmer update is not 200,
'Pass' if status of farmer update is 200)
- Column 'Response': Set to '' (Logic: 'Tag not found' if tag not found or
whole response of farmer update if status code is not 200,
'Tag updated to farmer' if farmer update response code is 200)
"""

def run(rows, token, env_config):
    processed_rows = []
    
    # Config
    base_url = env_config.get('apiBaseUrl')
    if not base_url:
         env_name = env_config.get('environment', 'Prod')
         ENV_MAP = { "QA1": "https://qa1.cropin.in", "QA2": "https://qa2.cropin.in", "Prod": "" }
         base_url = ENV_MAP.get(env_name)
    
    # If base_url is still empty (e.g., for Prod if not provided via apiBaseUrl), subsequent requests will fail.
    # This behavior is expected if a valid URL is strictly required via config.

    headers = { 'Authorization': f'Bearer {token}' }
    
    # 1. Fetch Master Tags (Step 1 from instructions)
    print("Fetching Tags...")
    tag_map = {}
    try:
        resp = requests.get(f"{base_url}/services/master/api/filter?type=FARMER", headers=headers)
        if resp.status_code == 200:
            for t in resp.json().get('data', []):
                tag_map[t.get('name', '').lower()] = t.get('id')
        else:
            # Enhanced error message for tag fetch failure
            print(f"Failed to fetch tags: Status Code {resp.status_code}, Response: {resp.text}")
            # Consider if the entire script should abort if master data cannot be fetched
            # For now, it will proceed, and individual rows will fail if tags aren't found in the empty map.
    except Exception as e:
        print(f"Failed to fetch tags due to exception: {e}")

    # Optional: Fetch Farmers List for Code->ID resolution if needed
    id_map = {}
    code_map = {}
    need_farmer_list = any('Farmer Code' in r or 'Farmer ID' in r for r in rows)
    if need_farmer_list:
        print("Fetching Farmers List for resolution...")
        try:
             fr = requests.get(f"{base_url}/services/farm/api/farmers/dropdownList", headers=headers)
             if fr.status_code == 200:
                 data = fr.json()
                 # Handle both direct array and {'data': [...]} wrapper
                 farmers = data if isinstance(data, list) else data.get('data', [])
                 for f in farmers:
                     fid = f.get('id')
                     fcode = f.get('farmerCode') or f.get('code')
                     if fid: id_map[str(fid).strip()] = fid
                     if fcode: code_map[str(fcode).strip().lower()] = fid
                 print(f"Loaded {len(farmers)} farmers for lookup (IDs: {len(id_map)}, Codes: {len(code_map)}).")
             else:
                 # Enhanced error message for farmer fetch failure
                 print(f"Farmer fetch failed: Status Code {fr.status_code}, Response: {fr.text}")
        except Exception as e:
            print(f"Farmer fetch failed due to exception: {e}")

    update_url = f"{base_url}/services/farm/api/farmers"

    for row in rows:
        new_row = row.copy() # Start with a copy of the input row to preserve original data
        
        # Initialize all expected output columns to ensure they are always present
        new_row['Tag ID'] = ''
        new_row['Status'] = ''
        new_row['Response'] = '' # Renamed from API_Response as per instructions
        
        try:
            # Inputs from Excel columns (case-sensitive as per original code, stripped)
            f_name = str(row.get('Farmer Name') or '').strip()
            f_id_raw = str(row.get('Farmer ID') or '').strip()
            f_code = str(row.get('Farmer Code') or '').strip()
            tag_name = str(row.get('Tag Name') or '').strip()
            
            # Ensure UI Output Definition columns are present in new_row
            new_row['Farmer Name'] = f_name
            new_row['Farmer ID'] = f_id_raw
            new_row['Tag Name'] = tag_name

            if not tag_name:
                new_row['Status'] = 'Fail'
                new_row['Response'] = 'Missing Tag Name'
                processed_rows.append(new_row)
                continue
            
            # Resolve Target ID (Farmer ID)
            target_id = None
            if f_id_raw:
                target_id = id_map.get(f_id_raw)
            
            if not target_id and f_code:
                target_id = code_map.get(f_code.lower())
            
            if not target_id:
                new_row['Status'] = 'Fail'
                new_row['Response'] = f"Farmer ID/Code not found or resolved. Provided ID: '{f_id_raw}', Code: '{f_code}'."
                processed_rows.append(new_row)
                continue
                
            # Resolve Tag ID (from Step 1 'Fetch Master Tags')
            tag_id = tag_map.get(tag_name.lower())
            if not tag_id:
                new_row['Status'] = 'Fail'
                new_row['Response'] = f"Tag not found: {tag_name}" # Specific response for tag not found
                processed_rows.append(new_row)
                continue
            
            new_row['Tag ID'] = tag_id # Populate 'Tag ID' column as per Excel Output Definition
                
            # 2. GET Farmer Details (Step 2 from instructions)
            f_resp = requests.get(f"{update_url}/{target_id}", headers=headers)
            if f_resp.status_code != 200:
                 new_row['Status'] = 'Fail'
                 new_row['Response'] = f"Failed to fetch farmer details for ID '{target_id}'. Status Code: {f_resp.status_code}, Response: {f_resp.text}"
                 processed_rows.append(new_row)
                 continue
                 
            farmer_data = f_resp.json()
            if not farmer_data:
                new_row['Status'] = 'Fail'
                new_row['Response'] = 'Empty Farmer Data received from API when fetching details.'
                processed_rows.append(new_row)
                continue
            
            # 3. Logic: Update Tags (Step 3 from instructions)
            # Ensure 'data' object exists and 'tags' list within it
            if 'data' not in farmer_data: 
                farmer_data['data'] = {}
            current_tags = farmer_data['data'].get('tags', [])
            
            # Ensure current_tags is a list of integers
            tag_ids = []
            if isinstance(current_tags, list):
                for t in current_tags:
                    try: tag_ids.append(int(t))
                    except ValueError: pass # Skip non-integer values gracefully
            elif isinstance(current_tags, str):
                 for t in current_tags.split(','):
                     try: tag_ids.append(int(t.strip()))
                     except ValueError: pass # Skip non-integer values gracefully
                     
            if tag_id not in tag_ids: # Only add if tag is not already present
                tag_ids.append(tag_id)
                farmer_data['data']['tags'] = tag_ids
                
                # 4. PUT Update (Multipart) (Step 4 from instructions)
                # Payload Type: DTO_FILE - requires multipart/form-data
                files = { 'dto': ('body.json', json.dumps(farmer_data), 'application/json') }
                
                put_resp = requests.put(update_url, headers=headers, files=files)
                
                if put_resp.status_code in [200, 201]:
                    new_row['Status'] = 'Pass'
                    new_row['Response'] = 'Tag updated to farmer' # Specific success message
                else:
                    new_row['Status'] = 'Fail'
                    new_row['Response'] = put_resp.text # Whole response for API failure
            else:
                # Tag already exists, so no PUT API call was made.
                # Per logical interpretation, the desired state is achieved.
                new_row['Status'] = 'Pass'
                new_row['Response'] = f"Tag '{tag_name}' (ID: {tag_id}) already exists on farmer."
                
        except Exception as e:
            # Catch any unexpected exceptions during processing of a row
            new_row['Status'] = 'Fail'
            new_row['Response'] = str(e)
            
        processed_rows.append(new_row)
        
    return processed_rows