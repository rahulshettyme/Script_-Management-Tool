# CONFIG: isMultithreaded = True
# CONFIG: batchSize = 10
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Farmer Name, Farmer Code, Phone Number, AssignedTo User ID, Address

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
    from datetime import datetime, timedelta

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
    global _geocode_cache, _use_provided_user_ids
    _geocode_cache = {}
    _use_provided_user_ids = False

    def excel_to_iso_date(val, col_name=None):
        """
    Converts Excel serial dates or date strings to ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z).
    Applies safeguards to prevent non-date columns from being incorrectly converted.
    """
        if val is None or val == '':
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = col_name and any((keyword in col_name.lower() for keyword in date_keywords))
        if isinstance(val, (int, float)):
            if is_date_column:
                try:
                    if val > 59:
                        val -= 1
                    dt = datetime(1899, 12, 30) + timedelta(days=val)
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except OverflowError:
                    pass
            return val
        elif isinstance(val, str):
            val_strip = val.strip()
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'):
                try:
                    dt = datetime.strptime(val_strip, fmt)
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except ValueError:
                    continue
            return val_strip
        return val

    def _user_run(data, token, env_config):
        """
    Main function to initiate parallel processing of farmer data.
    """
        builtins.token = token
        builtins.env_config = env_config
        global _use_provided_user_ids
        _use_provided_user_ids = bool(data and data[0].get('AssignedTo User ID') is not None)
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)

    def process_row(row):
        """
    Processes a single row of farmer data: geocodes address, validates phone,
    and creates a farmer via API.
    """
        row['Status'] = 'Fail'
        row['Response'] = ''
        row['Farmer ID'] = 'NA'
        row['Farmer Name'] = row.get('Farmer Name', '')
        farmer_name = row.get('Farmer Name')
        farmer_code = row.get('Farmer Code')
        phone_number_raw = str(row.get('Phone Number', '')).strip()
        assigned_to_user_id = row.get('AssignedTo User ID')
        address_str = row.get('Address')
        if not farmer_name:
            row['Response'] = 'Farmer Name is missing.'
            print(f'[{farmer_code or 'N/A'}] Farmer Name is missing.')
            return row
        if not farmer_code:
            row['Response'] = 'Farmer Code is missing.'
            print(f'[{farmer_name}] Farmer Code is missing.')
            return row
        if not phone_number_raw:
            row['Response'] = 'Phone Number is missing.'
            print(f'[{farmer_name}] Phone Number is missing.')
            return row
        if not assigned_to_user_id:
            row['Response'] = 'AssignedTo User ID is missing.'
            print(f'[{farmer_name}] AssignedTo User ID is missing.')
            return row
        parts = []
        if ' ' in phone_number_raw:
            parts = phone_number_raw.split(' ')
        elif '-' in phone_number_raw:
            parts = phone_number_raw.split('-')
        if len(parts) != 2 or not parts[0].isdigit() or (not parts[1].isdigit()):
            row['Response'] = 'Invalid phone number format. Required in 91 9876543210'
            print(f'[{farmer_name}] Invalid phone number format: {phone_number_raw}')
            return row
        country_code = '+' + parts[0]
        mobile_number = parts[1]
        address_component_payload = None
        if address_str:
            with _lock:
                if address_str in _geocode_cache:
                    address_component = _geocode_cache[address_str]
                    print(f'[GEOFENCE] {address_str} → CACHE HIT')
                else:
                    try:
                        geocode_result = geofence_utils.get_boundary(address_str, builtins.env_config.get('Geocoding_api_key'))
                        address_component = geofence_utils.parse_address_component(geocode_result) if geocode_result else None
                        _geocode_cache[address_str] = address_component
                    except requests.exceptions.RequestException as e:
                        row['Response'] = f'Geocoding API error: {e}'
                        print(f'[GEOFENCE] {address_str} → API ERROR: {e}')
                        return row
                    except Exception as e:
                        row['Response'] = f'Geocoding processing error: {e}'
                        print(f'[GEOFENCE] {address_str} → PROCESSING ERROR: {e}')
                        return row
            if address_component:
                address_component_payload = {'country': address_component.get('country'), 'formattedAddress': address_component.get('formattedAddress'), 'houseNo': address_component.get('houseNumber', ''), 'buildingName': address_component.get('buildingName', ''), 'administrativeAreaLevel1': address_component.get('administrativeAreaLevel1'), 'locality': address_component.get('locality'), 'administrativeAreaLevel2': address_component.get('administrativeAreaLevel2'), 'sublocalityLevel1': address_component.get('sublocalityLevel1', ''), 'sublocalityLevel2': address_component.get('sublocalityLevel2', ''), 'landmark': address_component.get('landmark', ''), 'postalCode': address_component.get('postalCode'), 'placeId': address_component.get('placeId'), 'latitude': address_component.get('latitude'), 'longitude': address_component.get('longitude')}
                row['Address Component (non mandatory)'] = json.dumps(address_component_payload)
                print(f'[GEOFENCE] {address_str} → lat={address_component.get('latitude', 'N/A'):.6f}, lng={address_component.get('longitude', 'N/A'):.6f}')
            else:
                row['Response'] = f'Failed to geocode address: {address_str}'
                print(f'[GEOFENCE] {address_str} → Result: Not Found')
                address_component_payload = None
        else:
            row['Address Component (non mandatory)'] = None
            print(f'[GEOFENCE] No address provided for geocoding.')
        farmer_payload = {'data': {'mobileNumber': mobile_number, 'countryCode': country_code}, 'firstName': farmer_name, 'farmerCode': farmer_code, 'assignedTo': [{'id': int(assigned_to_user_id), 'name': f'User_{assigned_to_user_id}'}], 'address': address_component_payload}
        standard_input_output_columns = ['Farmer Name', 'Farmer Code', 'Phone Number', 'AssignedTo User ID', 'Address', 'Address Component (non mandatory)', 'Status', 'Response', 'Farmer ID']
        for key, value in row.items():
            if key not in standard_input_output_columns:
                farmer_payload['data'][key] = str(value) if not isinstance(value, (int, float, bool)) else value
        create_farmer_url = f'{builtins.env_config.get('apiBaseUrl')}/services/farm/api/farmers'
        headers = {'Authorization': f'Bearer {builtins.token}'}
        files = {'dto': (None, json.dumps(farmer_payload), 'application/json')}
        try:
            response = _log_post(create_farmer_url, headers=headers, files=files)
            response.raise_for_status()
            response_json = response.json()
            if response.ok:
                row['Status'] = 'Pass'
                row['Response'] = 'Farmer Created Successfully'
                farmer_id = response_json.get('id')
                if farmer_id:
                    row['Farmer ID'] = str(farmer_id)
                else:
                    row['Farmer ID'] = 'NA (ID not found in response)'
                    row['Response'] += ' (ID not found in response)'
                print(f'[{farmer_name}] Farmer created successfully. ID: {row['Farmer ID']}')
            else:
                error_key = (response_json.get('error') or {}).get('errorKey') or response_json.get('message') or response.text
                row['Response'] = f'Failed to create farmer: {error_key}'
                row['Farmer ID'] = 'NA'
                print(f'[{farmer_name}] Failed to create farmer. Status: {response.status_code}, Response: {error_key}')
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_detail = 'Unknown error'
            try:
                error_json = e.response.json()
                if status_code == 400:
                    error_key = (error_json.get('error') or {}).get('errorKey')
                    error_detail = error_key if error_key else error_json.get('message', e.response.text)
                else:
                    error_detail = error_json.get('message', e.response.text)
            except json.JSONDecodeError:
                error_detail = e.response.text
            row['Response'] = f'API Error {status_code}: {error_detail}'
            row['Farmer ID'] = 'NA'
            print(f'[{farmer_name}] API call failed. Status: {status_code}, Error: {error_detail}')
        except requests.exceptions.RequestException as e:
            row['Response'] = f'Request failed: {e}'
            row['Farmer ID'] = 'NA'
            print(f'[{farmer_name}] Request failed: {e}')
        except Exception as e:
            row['Response'] = f'An unexpected error occurred: {e}'
            row['Farmer ID'] = 'NA'
            print(f'[{farmer_name}] Unexpected error: {e}')
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
_geocode_cache = None
_use_provided_user_ids = None
