# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: User Name, Phone Number, userRoleId, Address, email

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json
    import requests
    import json
    import thread_utils
    import builtins
    import components.geofence_utils as geofence_utils

    def _log_req(method, url, **kwargs):

        def _debug_jwt(token_str):
            try:
                if not token_str or len(token_str) < 10:
                    return 'Invalid/Empty Token'
                if token_str.startswith('Bearer '):
                    token_str = token_str.replace('Bearer ', '')
                parts = token_str.split('.')
                if len(parts) < 2:
                    return 'Not a JWT'
                payload = parts[1]
                pad = len(payload) % 4
                if pad:
                    payload += '=' * (4 - pad)
                import base64
                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                claims = json.loads(decoded)
                user = claims.get('preferred_username') or claims.get('sub')
                iss = claims.get('iss', '')
                tenant = iss.split('/')[-1] if '/' in iss else 'Unknown'
                return f'User: {user} | Tenant: {tenant}'
            except Exception as e:
                return f'Decode Error: {e}'
        headers = kwargs.get('headers', {})
        auth_header = headers.get('Authorization', 'None')
        token_meta = _debug_jwt(auth_header)
        print(f'[API_DEBUG] ----------------------------------------------------------------')
        print(f'[API_DEBUG] 🚀 REQUEST: {method} {url}')
        print(f'[API_DEBUG] 🔑 TOKEN META: {token_meta}')
        payload = kwargs.get('json') or kwargs.get('data')
        if not payload:
            files = kwargs.get('files')
            if files and isinstance(files, dict):
                if 'dto' in files:
                    val = files['dto']
                    if isinstance(val, (list, tuple)) and len(val) > 1:
                        payload = f'[Multipart DTO] {val[1]}'
                    else:
                        payload = f'[Multipart DTO] {val}'
                else:
                    payload = f'[Multipart Files] Keys: {list(files.keys())}'
        if not payload:
            payload = 'No Payload'
        payload_type = 'JSON' if kwargs.get('json') else 'Data'
        if payload_type == 'Data' and isinstance(payload, str):
            try:
                json.loads(payload)
                payload_type = 'Data (JSON)'
            except:
                pass
        if not kwargs.get('json') and (not kwargs.get('data')) and (not payload_type == 'Data (JSON)'):
            payload_type = 'Unknown/Multipart'
        try:
            if method == 'GET':
                resp = requests.get(url, **kwargs)
            elif method == 'POST':
                resp = requests.post(url, **kwargs)
            elif method == 'PUT':
                resp = requests.put(url, **kwargs)
            elif method == 'DELETE':
                resp = requests.delete(url, **kwargs)
            else:
                resp = requests.request(method, url, **kwargs)
            body_preview = 'Binary/No Content'
            try:
                if not resp.text or not resp.text.strip():
                    body_preview = '[Empty Response]'
                else:
                    try:
                        json_obj = resp.json()
                        body_preview = json.dumps(json_obj, indent=2)
                    except:
                        body_preview = resp.text[:4000]
            except:
                pass
            status_icon = '✅' if 200 <= resp.status_code < 300 else '❌'
            print(f'[API_DEBUG] {status_icon} RESPONSE [{resp.status_code}]')
            print(f'[API_DEBUG] 📄 BODY:\n{body_preview}')
            print(f'[API_DEBUG] ----------------------------------------------------------------\n')
            return resp
        except Exception as e:
            print(f'[API_DEBUG] ❌ EXCEPTION: {e}')
            print(f'[API_DEBUG] ----------------------------------------------------------------\n')
            raise e

    def _log_get(url, **kwargs):
        return _log_req('GET', url, **kwargs)

    def _log_post(url, **kwargs):
        return _log_req('POST', url, **kwargs)

    def _log_put(url, **kwargs):
        return _log_req('PUT', url, **kwargs)

    def _log_delete(url, **kwargs):
        return _log_req('DELETE', url, **kwargs)

    def _safe_iloc(row, idx):
        try:
            if isinstance(row, dict):
                keys = list(row.keys())
                if 0 <= idx < len(keys):
                    val = row[keys[idx]]
                    return val.strip() if isinstance(val, str) else val
                return None
            elif isinstance(row, list):
                if 0 <= idx < len(row):
                    return row[idx]
                return None
            return row.iloc[idx]
        except:
            return None
    import sys
    sys.argv = [sys.argv[0]]
    builtins.data = data
    builtins.data_df = pd.DataFrame(data)
    import os
    valid_token_path = os.path.join(os.getcwd(), 'valid_token.txt')
    if os.path.exists(valid_token_path):
        try:
            with open(valid_token_path, 'r') as f:
                forced_token = f.read().strip()
            if len(forced_token) > 10:
                print(f'[API_DEBUG] ⚠️ OVERRIDE: Using token from valid_token.txt')
                token = forced_token
        except Exception:
            pass
    builtins.token = token
    builtins.base_url = env_config.get('apiBaseUrl')
    base_url = builtins.base_url
    env_key = env_config.get('environment')
    file_path = 'Uploaded_File.xlsx'
    builtins.file_path = file_path
    env_url = base_url
    builtins.env_url = base_url

    class MockCell:

        def __init__(self, row_data, key):
            self.row_data = row_data
            self.key = key

        @property
        def value(self):
            return self.row_data.get(self.key)

        @value.setter
        def value(self, val):
            self.row_data[self.key] = val

    class MockSheet:

        def __init__(self, data):
            self.data = data

        def cell(self, row, column, value=None):
            idx = row - 2
            if not 0 <= idx < len(self.data):
                return MockCell({}, 'dummy')
            row_data = self.data[idx]
            keys = list(row_data.keys())
            if 1 <= column <= len(keys):
                key = keys[column - 1]
            elif 'output_columns' in dir(builtins) and 0 <= column - 1 < len(builtins.output_columns):
                key = builtins.output_columns[column - 1]
            else:
                key = f'Column_{column}'
            cell = MockCell(row_data, key)
            if value is not None:
                cell.value = value
            return cell

        @property
        def max_row(self):
            return len(self.data) + 1

    class MockWorkbook:

        def __init__(self, data_or_builtins):
            if hasattr(data_or_builtins, 'data'):
                self.data = data_or_builtins.data
            else:
                self.data = data_or_builtins

        def __getitem__(self, key):
            return MockSheet(self.data)

        @property
        def sheetnames(self):
            return ['Sheet1', 'Environment_Details', 'Plot_details', 'Sheet']

        def save(self, path):
            import json
            print(f'[MOCK] Excel saved to {path}')
            try:
                print('[OUTPUT_DATA_DUMP]')
                print(json.dumps(self.data))
                print('[/OUTPUT_DATA_DUMP]')
            except:
                pass

        @property
        def active(self):
            return MockSheet(self.data)
    wk = MockWorkbook(builtins)
    builtins.wk = wk
    builtins.wb = wk
    wb = wk
    global _geocode_cache
    _geocode_cache = {}

    def _user_run(data, token, env_config):
        """
    Orchestrates the parallel processing of user data for creation.
    """
        builtins.token = token
        builtins.env_config = env_config
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)

    def process_row(row):
        """
    Processes a single row of data from the Excel sheet to create a user.
    """
        row['Status'] = 'Fail'
        row['Response'] = ''
        row['Farmer Name'] = row.get('User Name')
        row['Farmer ID'] = 'NA'
        row['UserID'] = 'NA'
        user_name = row.get('User Name')
        phone_number_raw = str(row.get('Phone Number', '')).strip()
        user_role_id = row.get('userRoleId')
        address_raw = row.get('Address')
        email = row.get('email')
        if not all([user_name, phone_number_raw, user_role_id, address_raw, email]):
            row['Response'] = 'Missing mandatory input data (User Name, Phone Number, userRoleId, Address, email)'
            return row
        country_code = None
        mobile_number = None
        if ' ' in phone_number_raw:
            parts = phone_number_raw.split(' ')
        elif '-' in phone_number_raw:
            parts = phone_number_raw.split('-')
        else:
            row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
            return row
        if len(parts) != 2:
            row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
            return row
        country_code = '+' + parts[0]
        mobile_number = parts[1]
        try:
            user_role_id = int(user_role_id)
        except (ValueError, TypeError):
            row['Response'] = 'Invalid userRoleId format. Must be an integer.'
            return row
        location_payload = None
        with _lock:
            if address_raw in _geocode_cache:
                location_payload = _geocode_cache[address_raw]
                print(f'[GEOFENCE] {address_raw} -> Cache Hit. lat={location_payload.get('latitude', 0):.6f}, lng={location_payload.get('longitude', 0):.6f}')
            else:
                print(f'[GEOFENCE] {address_raw} -> Cache Miss. Calling API...')
                geocode_api_key = builtins.env_config.get('Geocoding_api_key')
                if not geocode_api_key:
                    row['Response'] = 'Geocoding API key (Geocoding_api_key) is missing in environment configuration.'
                    return row
                boundary_data = geofence_utils.get_boundary(address_raw, geocode_api_key)
                if not boundary_data:
                    row['Response'] = f'Geocoding failed for address: "{address_raw}". No boundary data found.'
                    return row
                address_component_parsed = geofence_utils.parse_address_component(boundary_data)
                geo_bounds_data = boundary_data.get('geometry', {}).get('bounds') or boundary_data.get('geometry', {}).get('viewport')
                parsed_bounds = None
                if geo_bounds_data:
                    parsed_bounds = {'northeast': {'lat': geo_bounds_data['northeast']['lat'], 'lng': geo_bounds_data['northeast']['lng']}, 'southwest': {'lat': geo_bounds_data['southwest']['lat'], 'lng': geo_bounds_data['southwest']['lng']}}
                geojson_polygon = boundary_data.get('geojson_polygon')
                geo_location = boundary_data.get('geometry', {}).get('location', {})
                lat = geo_location.get('lat')
                lng = geo_location.get('lng')
                if not all([lat is not None, lng is not None, parsed_bounds, geojson_polygon]):
                    row['Response'] = f'Geocoding failed to extract critical data (lat, lng, bounds, geoInfo) for address: "{address_raw}".'
                    return row
                location_payload = {'bounds': parsed_bounds, 'country': address_component_parsed.get('country'), 'placeId': boundary_data.get('place_id'), 'latitude': lat, 'longitude': lng, 'geoInfo': geojson_polygon, 'name': address_component_parsed.get('formattedAddress', address_component_parsed.get('country'))}
                _geocode_cache[address_raw] = location_payload
                print(f'[GEOFENCE] {address_raw} -> lat={lat:.6f}, lng={lng:.6f}')
        if location_payload:
            row['Address Component (non mandatory)'] = json.dumps(location_payload)
        else:
            if not row['Response']:
                row['Response'] = f'Failed to process address component for "{address_raw}".'
            return row
        api_base_url = builtins.env_config.get('apiBaseUrl')
        company_id = builtins.env_config.get('companyId')
        if not api_base_url or not company_id:
            row['Response'] = 'API base URL or Company ID is missing in environment configuration.'
            return row
        url = f'{api_base_url}/services/user/api/users/images'
        headers = {'Authorization': f'Bearer {builtins.token}'}
        try:
            country_iso_code = builtins.env_config.get('defaultCountryIsoCode', 'IN')
            payload_data = {'companyId': company_id, 'data': {'countryIsoCode': country_iso_code}, 'images': {}, 'contactNumber': mobile_number, 'name': user_name, 'userRoleId': user_role_id, 'countryCode': country_code, 'email': email, 'locations': location_payload, 'preferences': {'data': {}, 'timeZone': 'IST', 'language': 'en', 'currency': 'INR', 'areaUnits': 'ACRE', 'locale': 'en-IN'}}
            files = {'dto': (None, json.dumps(payload_data), 'application/json')}
            response = _log_post(url, headers=headers, files=files)
            if response.ok:
                response_json = response.json()
                user_id = response_json.get('id')
                row['UserID'] = user_id
                row['Status'] = 'Pass'
                row['Response'] = 'Farmer Created Successfully'
                row['Farmer ID'] = user_id
            else:
                row['Status'] = 'Fail'
                row['Farmer ID'] = 'NA'
                try:
                    error_json = response.json()
                    error_key = error_json.get('errorKey', error_json.get('message', f'API Error: {response.status_code} - {response.text}'))
                    row['Response'] = error_key
                except json.JSONDecodeError:
                    row['Response'] = f'API Error: {response.status_code} - {response.text}'
                print(f"Failed to create user '{user_name}': {row['Response']}")
        except requests.exceptions.RequestException as e:
            row['Status'] = 'Fail'
            row['Farmer ID'] = 'NA'
            row['Response'] = f'Network or API request error: {e}'
            print(f"Request exception for user '{user_name}': {e}")
        except Exception as e:
            row['Status'] = 'Fail'
            row['Farmer ID'] = 'NA'
            row['Response'] = f'An unexpected error occurred: {e}'
            print(f"Unexpected error for user '{user_name}': {e}")
        return row
    "\nOUTPUT MAPPING CONFIGURATION:\n- UI Output Definition:\n- UI Column 'Farmer Name': Set to 'Farmer Name' (Logic: from excel column 'Farmer Name')\n- UI Column 'Status': Set to '' (Logic: 'Pass' if Farmer create response in 200, else 'Fail')\n- UI Column 'Farmer ID': Set to '' (Logic: attribute 'id' from response of farmer create if status is pass, else 'NA')\n- Excel Output Definition:\n   - Column 'UserID': Set to 'user response id' (Logic: id from user fetch is user found)\n   - Column 'Status': Set to 'Pass or Fail' (Logic: 'Pass' if Farmer create response in 200, else 'Fail')\n   - Column 'Farmer ID': Set to 'id' (Logic: id from farmer create response if farmer created successfully)\n   - Column 'Response': Set to '' (Logic: 'Farmer Created Successfully' if farmer creation is success\nor 'User not Found' if user find is failed)\n"
    _lock = thread_utils.create_lock()
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
