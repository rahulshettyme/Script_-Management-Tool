# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Farmer Name, Farmer Code, Phone Number, AssignedTo, UserID, Address, Address Component (non mandatory), Status, Farmer ID, Response

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
    import components.master_search as master_search

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
        # print(f'[API_DEBUG] 📦 PAYLOAD ({payload_type}): {payload}')
        # print(f'[API_DEBUG] ----------------------------------------------------------------')
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
    global _geocode_cache, _user_cache
    _geocode_cache = {}
    _user_cache = {}

    def _user_run(data, token, env_config):
        """
    Main function to orchestrate the processing of farmer data.
    Initializes builtins.token and builtins.env_config for thread_utils.
    """
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)

    def process_row(row):
        """
    Processes a single row of farmer data from the Excel sheet.
    """
        row['Status'] = 'Fail'
        row['Response'] = 'Processing started'
        row['UserID'] = 'NA'
        row['Farmer ID'] = 'NA'
        api_base_url = builtins.env_config.get('apiBaseUrl')
        geocoding_api_key = builtins.env_config.get('Geocoding_api_key')
        headers = {'Authorization': f'Bearer {builtins.token}'}
        address_input = row.get('Address')
        if not address_input:
            row['Response'] = 'Address is mandatory but not provided.'
            return row
        address_component_payload = None
        with _lock:
            if address_input in _geocode_cache:
                address_component_payload = _geocode_cache[address_input]
                print(f"[GEOFENCE] Cache hit for '{address_input}' → Result: {address_component_payload.get('formattedAddress', 'N/A')}")
            else:
                try:
                    geocode_result = geofence_utils.get_boundary(address_input, geocoding_api_key)
                    if geocode_result:
                        address_component = geofence_utils.parse_address_component(geocode_result)
                        if address_component:
                            latitude = address_component.get('latitude')
                            longitude = address_component.get('longitude')
                            print(f"[GEOFENCE] '{address_input}' → lat={latitude:.6f}, lng={longitude:.6f}")
                            address_component_payload = {'formattedAddress': address_component.get('formattedAddress'), 'postalCode': address_component.get('postalCode'), 'locality': address_component.get('locality'), 'data': None, 'administrativeAreaLevel5': address_component.get('administrativeAreaLevel5'), 'administrativeAreaLevel4': address_component.get('administrativeAreaLevel4'), 'administrativeAreaLevel3': address_component.get('administrativeAreaLevel3'), 'administrativeAreaLevel2': address_component.get('administrativeAreaLevel2'), 'administrativeAreaLevel1': address_component.get('administrativeAreaLevel1'), 'country': address_component.get('country'), 'latitude': latitude, 'longitude': longitude, 'placeId': address_component.get('placeId'), 'sublocalityLevel1': address_component.get('sublocalityLevel1', ''), 'sublocalityLevel2': address_component.get('sublocalityLevel2', ''), 'sublocalityLevel3': address_component.get('sublocalityLevel3'), 'sublocalityLevel4': address_component.get('sublocalityLevel4'), 'sublocalityLevel5': address_component.get('sublocalityLevel5'), 'houseNo': address_component.get('houseNo', ''), 'buildingName': address_component.get('buildingName', ''), 'landmark': address_component.get('landmark', '')}
                            _geocode_cache[address_input] = address_component_payload
                        else:
                            row['Response'] = f"GEOFENCE: Failed to parse address components for '{address_input}'."
                            return row
                    else:
                        row['Response'] = f"GEOFENCE: Could not get boundary data for '{address_input}'. Check address or API key."
                        return row
                except Exception as e:
                    row['Response'] = f"GEOFENCE: Error processing address '{address_input}': {str(e)}"
                    return row
        if address_component_payload:
            row['Address Component (non mandatory)'] = json.dumps(address_component_payload)
        else:
            row['Response'] = 'GEOFENCE: No valid address component generated, cannot proceed.'
            return row
        assigned_to_name = row.get('AssignedTo')
        if not assigned_to_name:
            row['Response'] = 'AssignedTo name is mandatory but not provided.'
            return row
        user_id = None
        with _lock:
            user_lookup_result = master_search.search('user', assigned_to_name, builtins.env_config, _user_cache)
        if not user_lookup_result['found']:
            row['Response'] = user_lookup_result['message']
            print(f"[USER_LOOKUP] '{assigned_to_name}' → Result: Not Found")
            return row
        user_id = user_lookup_result['value']
        row['UserID'] = user_id
        print(f"[USER_LOOKUP] '{assigned_to_name}' → ID: {user_id}")
        farmer_name = row.get('Farmer Name')
        farmer_code = row.get('Farmer Code')
        phone_raw = str(row.get('Phone Number', '')).strip()
        if not all([farmer_name, farmer_code, phone_raw]):
            row['Response'] = 'Farmer Name, Farmer Code, and Phone Number are mandatory.'
            return row
        parts = []
        if ' ' in phone_raw:
            parts = phone_raw.split(' ')
        elif '-' in phone_raw:
            parts = phone_raw.split('-')
        else:
            row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
            return row
        if len(parts) != 2:
            row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
            return row
        country_code = '+' + parts[0]
        mobile_number = parts[1]
        address_for_api = {'country': address_component_payload.get('country'), 'formattedAddress': address_component_payload.get('formattedAddress'), 'houseNo': address_component_payload.get('houseNo', ''), 'buildingName': address_component_payload.get('buildingName', ''), 'administrativeAreaLevel1': address_component_payload.get('administrativeAreaLevel1'), 'locality': address_component_payload.get('locality'), 'administrativeAreaLevel2': address_component_payload.get('administrativeAreaLevel2'), 'sublocalityLevel1': address_component_payload.get('sublocalityLevel1', ''), 'sublocalityLevel2': address_component_payload.get('sublocalityLevel2', ''), 'landmark': address_component_payload.get('landmark', ''), 'postalCode': address_component_payload.get('postalCode'), 'placeId': address_component_payload.get('placeId'), 'latitude': address_component_payload.get('latitude'), 'longitude': address_component_payload.get('longitude')}
        address_for_api = {k: v for k, v in address_for_api.items() if v is not None}
        payload = {'data': {'mobileNumber': mobile_number, 'countryCode': country_code}, 'firstName': farmer_name, 'farmerCode': farmer_code, 'assignedTo': [{'id': user_id, 'name': assigned_to_name}], 'address': address_for_api}
        try:
            url = f'{api_base_url}/services/farm/api/farmers'
            files = {'dto': (None, json.dumps(payload), 'application/json')}
            response = _log_post(url, headers=headers, files=files)
            if response.ok:
                response_json = response.json()
                row['Status'] = 'Pass'
                row['Response'] = 'Farmer Created Successfully'
                row['Farmer ID'] = response_json.get('id', 'NA')
            else:
                row['Status'] = 'Fail'
                try:
                    error_json = response.json()
                    if response.status_code == 400:
                        row['Response'] = error_json.get('title', json.dumps(error_json))
                    else:
                        row['Response'] = error_json.get('message', json.dumps(error_json))
                except json.JSONDecodeError:
                    row['Response'] = f'API Error {response.status_code}: {response.text}'
        except requests.exceptions.RequestException as e:
            row['Status'] = 'Fail'
            row['Response'] = f'API Request Failed: {str(e)}'
        except Exception as e:
            row['Status'] = 'Fail'
            row['Response'] = f'An unexpected error occurred during API call: {str(e)}'
        return row
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
