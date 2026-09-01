# CONFIG: isMultithreaded = True
# CONFIG: batchSize = 10
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Asset Name, Farmer_ID, Soil Type, Irrigation Type, Address, Declared Area

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
    import components.master_search as master_search
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
    global _soiltype_list, _geocode_cache, _irrigationtype_list
    _soiltype_list = []
    _irrigationtype_list = []
    _geocode_cache = {}

    def excel_to_iso_date(val, col_name=None):
        """
    Converts Excel serial dates or common date strings to ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z).
    Handles Excel's epoch (1900-01-01) for numeric values.
    Only converts numeric values if the column name indicates a date.
    """
        if val is None or val == '':
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = False
        if col_name and any((keyword in col_name.lower() for keyword in date_keywords)):
            is_date_column = True
        if isinstance(val, (int, float)):
            if not is_date_column:
                return val
            try:
                excel_epoch = datetime(1899, 12, 30)
                dt_object = excel_epoch + timedelta(days=val)
                return dt_object.isoformat(timespec='milliseconds') + 'Z'
            except Exception:
                pass
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y'):
                try:
                    dt_object = datetime.strptime(val, fmt)
                    return dt_object.isoformat(timespec='milliseconds') + 'Z'
                except ValueError:
                    continue
        return val

    def _user_run(data, token, env_config):
        """
    Main function to orchestrate the asset creation process.
    Initializes module-level caches and runs rows in parallel.
    """
        builtins.token = token
        builtins.env_config = env_config
        global _soiltype_list
        global _irrigationtype_list
        if not _soiltype_list:
            _soiltype_list = master_search.fetch_all('soiltype', builtins.env_config)
            print(f'[MASTER_INIT] Fetched {len(_soiltype_list)} soil types.')
            if not _soiltype_list:
                print('[MASTER_INIT_ERROR] Failed to fetch soil types. This might lead to lookup failures.')
        if not _irrigationtype_list:
            _irrigationtype_list = master_search.fetch_all('irrigationtype', builtins.env_config)
            print(f'[MASTER_INIT] Fetched {len(_irrigationtype_list)} irrigation types.')
            if not _irrigationtype_list:
                print('[MASTER_INIT_ERROR] Failed to fetch irrigation types. This might lead to lookup failures.')
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)

    def process_row(row):
        """
    Processes each row of data to create an asset.
    """
        row['Status'] = 'Fail'
        row['Response'] = ''
        row['Asset ID'] = 'NA'
        row['Address Component (non mandatory)'] = ''
        asset_name = row.get('Asset Name')
        farmer_id = row.get('Farmer_ID')
        soil_type_name = row.get('Soil Type')
        irrigation_type_name = row.get('Irrigation Type')
        address_str = row.get('Address')
        declared_area = row.get('Declared Area')
        if not asset_name:
            row['Response'] = 'Asset Name is mandatory.'
            return row
        if not farmer_id:
            row['Response'] = 'Farmer_ID is mandatory.'
            return row
        try:
            farmer_id = int(farmer_id)
        except ValueError:
            row['Response'] = 'Farmer_ID must be a valid number.'
            return row
        if not soil_type_name:
            row['Response'] = 'Soil Type is mandatory.'
            return row
        if not irrigation_type_name:
            row['Response'] = 'Irrigation Type is mandatory.'
            return row
        if not address_str:
            row['Response'] = 'Address is mandatory.'
            return row
        if declared_area is None or declared_area == '':
            row['Response'] = 'Declared Area is mandatory.'
            return row
        try:
            declared_area = float(declared_area)
        except ValueError:
            row['Response'] = 'Declared Area must be a valid number.'
            return row
        soil_type_id = None
        result_soil_type = master_search.lookup_from_cache(_soiltype_list, 'name', soil_type_name, 'id')
        if not result_soil_type['found']:
            row['Response'] = f"Soil Type '{soil_type_name}' not found."
            print(f"[MASTER] Soil Type: '{soil_type_name}' → ID: Not Found")
            return row
        soil_type_id = result_soil_type['value']
        row['Soil Type_id'] = soil_type_id
        print(f"[MASTER] Soil Type: '{soil_type_name}' → ID: {soil_type_id}")
        irrigation_type_id = None
        result_irrigation_type = master_search.lookup_from_cache(_irrigationtype_list, 'name', irrigation_type_name, 'id')
        if not result_irrigation_type['found']:
            row['Response'] = f"Irrigation Type '{irrigation_type_name}' not found."
            print(f"[MASTER] Irrigation Type: '{irrigation_type_name}' → ID: Not Found")
            return row
        irrigation_type_id = result_irrigation_type['value']
        row['Irrigation Type_id'] = irrigation_type_id
        print(f"[MASTER] Irrigation Type: '{irrigation_type_name}' → ID: {irrigation_type_id}")
        address_component_payload = {}
        geocoding_api_key = builtins.env_config.get('Geocoding_api_key')
        if not geocoding_api_key:
            row['Response'] = 'Geocoding_api_key not found in environment configuration.'
            print('[GEO_ERROR] Geocoding_api_key is missing.')
            return row
        with _lock:
            if address_str in _geocode_cache:
                address_component_parsed = _geocode_cache[address_str]
                print(f"[GEOFENCE] Cached: '{address_str}' → lat={address_component_parsed.get('latitude'):.6f}, lng={address_component_parsed.get('longitude'):.6f}")
            else:
                geocode_result = geofence_utils.get_boundary(address_str, geocoding_api_key)
                if not geocode_result:
                    row['Response'] = f"Address geocoding failed for '{address_str}'."
                    print(f"[GEOFENCE_ERROR] '{address_str}' → Geocoding returned no result.")
                    return row
                address_component_parsed = geofence_utils.parse_address_component(geocode_result)
                _geocode_cache[address_str] = address_component_parsed
                print(f"[GEOFENCE] Live API: '{address_str}' → lat={address_component_parsed.get('latitude'):.6f}, lng={address_component_parsed.get('longitude'):.6f}")
        address_component_payload = {'formattedAddress': address_component_parsed.get('formattedAddress'), 'postalCode': address_component_parsed.get('postalCode'), 'locality': address_component_parsed.get('locality'), 'administrativeAreaLevel5': address_component_parsed.get('administrativeAreaLevel5'), 'administrativeAreaLevel4': address_component_parsed.get('administrativeAreaLevel4'), 'administrativeAreaLevel3': address_component_parsed.get('administrativeAreaLevel3'), 'administrativeAreaLevel2': address_component_parsed.get('administrativeAreaLevel2'), 'administrativeAreaLevel1': address_component_parsed.get('administrativeAreaLevel1'), 'country': address_component_parsed.get('country'), 'latitude': address_component_parsed.get('latitude'), 'longitude': address_component_parsed.get('longitude'), 'placeId': address_component_parsed.get('placeId'), 'sublocalityLevel1': address_component_parsed.get('sublocalityLevel1'), 'sublocalityLevel2': address_component_parsed.get('sublocalityLevel2'), 'sublocalityLevel3': address_component_parsed.get('sublocalityLevel3'), 'sublocalityLevel4': address_component_parsed.get('sublocalityLevel4'), 'sublocalityLevel5': address_component_parsed.get('sublocalityLevel5'), 'houseNo': address_component_parsed.get('streetNumber'), 'buildingName': address_component_parsed.get('premise'), 'landmark': address_component_parsed.get('landmark'), 'data': None}
        for k in ['sublocalityLevel1', 'sublocalityLevel2', 'houseNo', 'buildingName', 'landmark']:
            if address_component_payload.get(k) is None:
                address_component_payload[k] = ''
        row['Address Component (non mandatory)'] = json.dumps(address_component_payload)
        api_url = f'{base_url}/services/farm/api/assets'
        headers = {'Authorization': f'Bearer {builtins.token}'}
        payload = {'declaredArea': {'count': declared_area}, 'name': asset_name, 'ownerId': farmer_id, 'soilType': {'id': soil_type_id}, 'irrigationType': {'id': irrigation_type_id}, 'address': address_component_payload, 'data': {}}
        standard_columns = ['Asset Name', 'Farmer_ID', 'Soil Type', 'Irrigation Type', 'Address', 'Declared Area', 'Status', 'Response', 'Asset ID', 'Soil Type_id', 'Irrigation Type_id', 'Address Component (non mandatory)']
        for key, value in row.items():
            if key not in standard_columns:
                payload['data'][key] = excel_to_iso_date(value, key)
        try:
            files = {'dto': (None, json.dumps(payload), 'application/json')}
            response = _log_post(api_url, headers=headers, files=files)
            response_json = response.json()
            if response.ok:
                row['Status'] = 'Pass'
                row['Response'] = 'Asset Created Successfully'
                row['Asset ID'] = response_json.get('id') or 'NA'
            else:
                row['Status'] = 'Fail'
                error_message = f'Failed to create asset. Status Code: {response.status_code}. '
                if response.status_code == 400:
                    row['Response'] = response_json.get('title', response_json.get('message', 'Bad Request'))
                else:
                    row['Response'] = error_message + json.dumps(response_json)
                print(f"[API_ERROR] Create Asset failed for '{asset_name}': {row['Response']}")
        except requests.exceptions.RequestException as e:
            row['Response'] = f'API request failed: {e}'
            print(f"[API_ERROR] Request exception for '{asset_name}': {e}")
        except json.JSONDecodeError:
            row['Response'] = f'API response was not valid JSON: {response.text}'
            print(f"[API_ERROR] JSON decode error for '{asset_name}': {response.text}")
        except Exception as e:
            row['Response'] = f'An unexpected error occurred: {e}'
            print(f"[GENERAL_ERROR] Unexpected error for '{asset_name}': {e}")
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
