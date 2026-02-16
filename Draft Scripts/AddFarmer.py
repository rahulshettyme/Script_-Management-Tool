# AI Generated - 2026-02-14 22:21:01 IST
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Farmer Name, Farmer Code, Phone Number, AssignedTo, UserID, Address, Address Component (non mandatory), Status, Farmer ID, Response
# OUTPUT MAPPING CONFIGURATION:
# - UI Output Definition:
# - UI Column 'Farmer Name': Set to 'Farmer Name' (Logic: from excel column 'Farmer Name')
# - UI Column 'Status': Set to '' (Logic: 'Pass' if Farmer create response in 200, else 'Fail')
# - UI Column 'Farmer ID': Set to '' (Logic: attribute 'id' from response of farmer create if status is pass, else 'NA')
# - Excel Output Definition:
#    - Column 'UserID': Set to 'user response id' (Logic: id from user fetch is user found)
#    - Column 'Status': Set to 'Pass or Fail' (Logic: 'Pass' if Farmer create response in 200, else 'Fail')
#    - Column 'Farmer ID': Set to 'id' (Logic: id from farmer create response if farmer created successfully)
#    - Column 'Response': Set to '' (Logic: 'Farmer Created Successfully' if farmer creation is success
# or 'User not Found' is user find is failed
# Actual response if farmer creation failed)

import requests
import json
import thread_utils
import builtins
import components.geofence_utils as geofence_utils
import components.master_search as master_search

# Module-level caches for thread-safe access
_geocode_cache = {}
_lock = thread_utils.create_lock() # Lock for _geocode_cache
_user_cache = {}

# Flag to determine if UserID is provided or needs lookup
_use_provided_user_ids = False

def run(data, token, env_config):
    """
    Main entry point for the script.
    Processes each row of data in parallel.
    """
    builtins.token = token
    builtins.env_config = env_config

    # Check if the first row has UserID provided to determine lookup mode
    global _use_provided_user_ids
    _use_provided_user_ids = bool(data and data[0].get('UserID'))

    return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)

def process_row(row):
    """
    Processes a single row of data from the Excel file.
    """
    # Initialize output columns
    row['Status'] = ''
    row['Response'] = ''
    row['Farmer ID'] = 'NA'

    # Step 1 [GEO]: Geocoding Address
    address = row.get('Address')
    if not address:
        row['Status'] = 'Fail'
        row['Response'] = 'Address is missing for geocoding.'
        return row

    address_component_parsed = None
    with _lock: # Ensure thread-safe access to cache
        if address in _geocode_cache:
            address_component_parsed = _geocode_cache[address]
            print(f"[GEOFENCE] {address} (cached) → lat={address_component_parsed.get('latitude')}, lng={address_component_parsed.get('longitude')}")
        else:
            geocode_result = geofence_utils.get_boundary(address, builtins.env_config.get('Geocoding_api_key'))
            if not geocode_result:
                row['Status'] = 'Fail'
                row['Response'] = f'Geocoding failed for address: {address}'
                return row
            
            address_component_parsed = geofence_utils.parse_address_component(geocode_result)
            _geocode_cache[address] = address_component_parsed
            print(f"[GEOFENCE] {address} → lat={address_component_parsed.get('latitude')}, lng={address_component_parsed.get('longitude')}")
            
    # Extract only the required fields as per the example JSON for 'Address Component (non mandatory)'
    output_address_component = {
        "formattedAddress": address_component_parsed.get("formattedAddress"),
        "postalCode": address_component_parsed.get("postalCode"),
        "locality": address_component_parsed.get("locality"),
        "data": None, # From example
        "administrativeAreaLevel5": None, # From example
        "administrativeAreaLevel4": None, # From example
        "administrativeAreaLevel3": None, # From example
        "administrativeAreaLevel2": address_component_parsed.get("administrativeAreaLevel2"),
        "administrativeAreaLevel1": address_component_parsed.get("administrativeAreaLevel1"),
        "country": address_component_parsed.get("country"),
        "latitude": address_component_parsed.get("latitude"),
        "longitude": address_component_parsed.get("longitude"),
        "placeId": address_component_parsed.get("placeId"),
        "sublocalityLevel1": address_component_parsed.get("sublocalityLevel1", ""), # From example
        "sublocalityLevel2": address_component_parsed.get("sublocalityLevel2", ""), # From example
        "sublocalityLevel3": None, # From example
        "sublocalityLevel4": None, # From example
        "sublocalityLevel5": None, # From example
        "houseNo": address_component_parsed.get("houseNo", ""), # From example
        "buildingName": address_component_parsed.get("buildingName", ""), # From example
        "landmark": address_component_parsed.get("landmark", "") # From example
    }
    row['Address Component (non mandatory)'] = json.dumps(output_address_component)

    # Step 2 [MASTER]: User Lookup for AssignedTo
    assigned_to_name = row.get('AssignedTo')
    if not assigned_to_name:
        row['Status'] = 'Fail'
        row['Response'] = 'AssignedTo name is missing.'
        return row

    user_id = None
    if _use_provided_user_ids:
        # STRICT MODE: Use provided ID, fail if missing.
        user_id = row.get('UserID')
        if not user_id:
            row['Status'] = 'Fail'
            row['Response'] = 'UserID is empty (Strict Mode)'
            print(f"[USER_LOOKUP] {assigned_to_name} → ID: Not Found (Strict Mode)")
            return row
        print(f"[USER_LOOKUP] {assigned_to_name} → ID: {user_id} (Provided)")
    else:
        # FALLBACK MODE: Perform Search
        result = master_search.search('user', assigned_to_name, builtins.env_config, _user_cache)
        if not result['found']:
            row['Status'] = 'Fail'
            row['Response'] = result['message']
            print(f"[USER_LOOKUP] {assigned_to_name} → ID: Not Found")
            return row
        user_id = result['value']
        print(f"[USER_LOOKUP] {assigned_to_name} → ID: {user_id}")

    row['UserID'] = user_id

    # Step 3 [API]: Create Farmer
    farmer_name = row.get('Farmer Name')
    farmer_code = row.get('Farmer Code')
    phone_raw = str(row.get('Phone Number', '')).strip()

    if not all([farmer_name, farmer_code, phone_raw, user_id, assigned_to_name, address_component_parsed]):
        row['Status'] = 'Fail'
        row['Response'] = 'Missing one or more required fields (Farmer Name, Farmer Code, Phone Number, AssignedTo, Address Component).'
        return row

    # Phone number validation
    country_code = None
    mobile_number = None
    if ' ' in phone_raw:
        parts = phone_raw.split(' ')
    elif '-' in phone_raw:
        parts = phone_raw.split('-')
    else:
        row['Status'] = 'Fail'
        row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
        return row

    if len(parts) != 2:
        row['Status'] = 'Fail'
        row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
        return row

    country_code = "+" + parts[0]
    mobile_number = parts[1]

    # Construct the API payload
    payload_data = {
        "data": {
            "mobileNumber": mobile_number,
            "countryCode": country_code
        },
        "firstName": farmer_name,
        "farmerCode": farmer_code,
        "assignedTo": [
            {
                "id": user_id,
                "name": assigned_to_name
            }
        ],
        "address": {
            "country": output_address_component.get("country"),
            "formattedAddress": output_address_component.get("formattedAddress"),
            "houseNo": output_address_component.get("houseNo"),
            "buildingName": output_address_component.get("buildingName"),
            "administrativeAreaLevel1": output_address_component.get("administrativeAreaLevel1"),
            "locality": output_address_component.get("locality"),
            "administrativeAreaLevel2": output_address_component.get("administrativeAreaLevel2"),
            "sublocalityLevel1": output_address_component.get("sublocalityLevel1"),
            "sublocalityLevel2": output_address_component.get("sublocalityLevel2"),
            "landmark": output_address_component.get("landmark"),
            "postalCode": output_address_component.get("postalCode"),
            "placeId": output_address_component.get("placeId"),
            "latitude": output_address_component.get("latitude"),
            "longitude": output_address_component.get("longitude")
        }
    }

    api_url = f"{builtins.env_config.get('apiBaseUrl')}/services/farm/api/farmers"
    headers = {'Authorization': f'Bearer {builtins.token}'}

    try:
        # For Payload Type: DTO_FILE, use the 'files' parameter
        files = {
            'dto': (None, json.dumps(payload_data), 'application/json')
        }
        response = requests.post(api_url, headers=headers, files=files)

        if response.ok: # Handles 200 OK and 201 Created
            response_json = response.json()
            row['Status'] = 'Pass'
            row['Response'] = 'Farmer Created Successfully'
            row['Farmer ID'] = response_json.get('id', 'NA')
        else:
            row['Status'] = 'Fail'
            row['Farmer ID'] = 'NA'
            if response.status_code == 400:
                try:
                    error_json = response.json()
                    row['Response'] = error_json.get('title', response.text)
                except json.JSONDecodeError:
                    row['Response'] = response.text
            else:
                row['Response'] = response.text

    except requests.exceptions.RequestException as e:
        row['Status'] = 'Fail'
        row['Response'] = f"API request failed: {e}"
        row['Farmer ID'] = 'NA'
    
    return row