# CONFIG: isMultithreaded = False
# CONFIG: batchSize = 1
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# CONFIG: groupByColumn = 'name'
# EXPECTED_INPUT_COLUMNS: name, nickName, expectedHarvestDays, cropName, expectedYield, expectedYieldUnits, refrenceAreaUnits, Location, cropStagename, cropStagedaysAfterSowing

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json
    import requests
    import json
    from datetime import datetime, timedelta
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
    global _crop_cache, _crop_stages_cache_step3, _geocode_cache, _crop_stages_cache_step1, _created_crop_stages
    _crop_stages_cache_step1 = None
    _created_crop_stages = []
    _crop_stages_cache_step3 = None
    _crop_cache = None
    _geocode_cache = {}

    def excel_to_iso_date(val, col_name=None):
        """
    Converts an Excel date serial number or a date string to ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z).
    Handles both numeric Excel serial dates and common date string formats.
    Only converts numeric values if col_name indicates a date column.
    """
        if val is None or val == '':
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = col_name and any((keyword in col_name.lower() for keyword in date_keywords))
        if isinstance(val, (int, float)):
            if is_date_column:
                try:
                    if val > 60:
                        dt = datetime(1899, 12, 30) + timedelta(days=val)
                    else:
                        dt = datetime(1899, 12, 31) + timedelta(days=val)
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except Exception as e:
                    print(f'Warning: Could not convert Excel serial date {val} for column {col_name}: {e}')
                    return None
            else:
                return val
        elif isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
                try:
                    dt = datetime.strptime(val, fmt)
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except ValueError:
                    pass
            print(f"Warning: Could not parse date string '{val}' for column {col_name}. Skipping conversion.")
            return None
        return val

    def _user_run(data, token, env_config):
        """
    Main function to process the data for adding crop varieties.
    This function performs initial master data fetches and then processes rows
    in groups to create varieties.
    """
        global _crop_stages_cache_step1, _new_crop_stages_to_add, _created_crop_stages, _crop_stages_cache_step3, _crop_cache, _geocode_cache
        _crop_stages_cache_step1 = None
        _new_crop_stages_to_add = set()
        _created_crop_stages = []
        _crop_stages_cache_step3 = None
        _crop_cache = None
        _geocode_cache = {}
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        api_base_url = env_config.get('apiBaseUrl')
        print(f'[MASTER_DATA] Fetching existing crop stages...')
        try:
            response = _log_get(f'{api_base_url}/services/farm/api/crop-stages', headers=headers)
            response.raise_for_status()
            _crop_stages_cache_step1 = response.json()
            print(f'[MASTER_DATA] Crop stages fetched. Count: {len(_crop_stages_cache_step1)}')
        except requests.exceptions.RequestException as e:
            print(f'[ERROR] Failed to fetch existing crop stages (Step 1): {e}')
            results_on_error = []
            for row in data:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f'Failed to fetch master crop stages: {e}'
                results_on_error.append({'name': row.get('name'), 'varietyID': 'NA', 'cropStagename': row.get('cropStagename'), 'Status': 'Fail'})
            return results_on_error
        existing_crop_stage_names = {cs['name'].lower() for cs in _crop_stages_cache_step1 if cs.get('name')}
        all_excel_crop_stage_names = set()
        for row in data:
            crop_stage_name_from_excel = row.get('cropStagename')
            if crop_stage_name_from_excel:
                all_excel_crop_stage_names.add(str(crop_stage_name_from_excel).strip())
        for name in all_excel_crop_stage_names:
            if name.lower() not in existing_crop_stage_names:
                _new_crop_stages_to_add.add(name)
        print(f'[MASTER_DATA] Identified {len(_new_crop_stages_to_add)} unique crop stages to add.')
        for new_stage_name in _new_crop_stages_to_add:
            print(f"[API] Adding new crop stage: '{new_stage_name}'...")
            payload = {'name': new_stage_name}
            try:
                response = _log_post(f'{api_base_url}/services/farm/api/crop-stages', headers=headers, json=payload)
                response.raise_for_status()
                created_stage = response.json()
                _created_crop_stages.append(created_stage)
                print(f"[API] Successfully added crop stage: '{new_stage_name}' with ID: {created_stage.get('id')}")
            except requests.exceptions.RequestException as e:
                error_detail = response.json().get('title', response.text) if response.content else response.text
                print(f"[ERROR] Failed to add crop stage '{new_stage_name}': {error_detail}")
        print(f'[MASTER_DATA] Re-fetching all crop stages after potential additions...')
        try:
            response = _log_get(f'{api_base_url}/services/farm/api/crop-stages', headers=headers)
            response.raise_for_status()
            _crop_stages_cache_step3 = response.json()
            print(f'[MASTER_DATA] All crop stages fetched. Count: {len(_crop_stages_cache_step3)}')
        except requests.exceptions.RequestException as e:
            print(f'[ERROR] Failed to re-fetch crop stages (Step 3): {e}')
            results_on_error = []
            for row in data:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f'Failed to re-fetch master crop stages: {e}'
                results_on_error.append({'name': row.get('name'), 'varietyID': 'NA', 'cropStagename': row.get('cropStagename'), 'Status': 'Fail'})
            return results_on_error
        print(f'[MASTER_DATA] Fetching crops...')
        try:
            response = _log_get(f'{api_base_url}/services/farm/api/crops?size=1000', headers=headers)
            response.raise_for_status()
            _crop_cache = response.json()
            print(f'[MASTER_DATA] Crops fetched. Count: {len(_crop_cache)}')
        except requests.exceptions.RequestException as e:
            print(f'[ERROR] Failed to fetch crops (Step 4): {e}')
            results_on_error = []
            for row in data:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f'Failed to fetch master crops: {e}'
                results_on_error.append({'name': row.get('name'), 'varietyID': 'NA', 'cropStagename': row.get('cropStagename'), 'Status': 'Fail'})
            return results_on_error
        grouped_data = {}
        for row in data:
            variety_name = str(row.get('name', 'UNKNOWN_VARIETY')).strip()
            if variety_name not in grouped_data:
                grouped_data[variety_name] = []
            grouped_data[variety_name].append(row)
        final_results = []
        for variety_name, variety_rows in grouped_data.items():
            processed_rows_for_group = process_variety_group(variety_rows, token, env_config, api_base_url)
            final_results.extend(processed_rows_for_group)
        return final_results

    def process_variety_group(variety_rows, token, env_config, api_base_url):
        """
    Processes a group of rows belonging to the same variety name.
    Makes a single API call for variety creation and updates all original rows in the group
    with the API call result.
    """
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        first_row = variety_rows[0]
        variety_name = str(first_row.get('name', '')).strip()
        nick_name = str(first_row.get('nickName', '')).strip()
        expected_harvest_days = first_row.get('expectedHarvestDays')
        crop_name = str(first_row.get('cropName', '')).strip()
        expected_yield = first_row.get('expectedYield')
        expected_yield_units = str(first_row.get('expectedYieldUnits', '')).strip()
        reference_area_units = str(first_row.get('refrenceAreaUnits', '')).strip()
        location_name = str(first_row.get('Location', '')).strip()
        if not variety_name:
            for row in variety_rows:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f"Missing required field: 'name' for variety."
            return _format_output_rows(variety_rows)
        if not crop_name:
            for row in variety_rows:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f"Missing required field: 'cropName' for variety '{variety_name}'."
            return _format_output_rows(variety_rows)
        crop_id = None
        if _crop_cache:
            for crop in _crop_cache:
                if crop.get('name', '').lower() == crop_name.lower():
                    crop_id = crop.get('id')
                    break
        if not crop_id:
            for row in variety_rows:
                row['Status'] = 'Fail'
                row['varietyID'] = 'NA'
                row['API Response'] = f"Crop '{crop_name}' not found in master data for variety '{variety_name}'."
            print(f"[CROP_LOOKUP] {crop_name} → ID: Not Found for variety '{variety_name}'")
            return _format_output_rows(variety_rows)
        print(f"[CROP_LOOKUP] {crop_name} → ID: {crop_id} for variety '{variety_name}'")
        location_payload = None
        if location_name:
            print(f"[GEOFENCE] Processing location: {location_name} for variety '{variety_name}'")
            if location_name in _geocode_cache:
                address_component = _geocode_cache[location_name]
            else:
                geocode_result = geofence_utils.get_boundary(location_name, env_config.get('Geocoding_api_key'))
                if geocode_result:
                    address_component = geofence_utils.parse_address_component(geocode_result)
                    _geocode_cache[location_name] = address_component
                else:
                    address_component = None
            if address_component:
                bounds = (address_component.get('geometry') or {}).get('bounds')
                if not bounds:
                    bounds = (address_component.get('geometry') or {}).get('viewport')
                geojson_polygon = address_component.get('geojson_polygon')
                location_payload = {'bounds': bounds, 'country': address_component.get('country'), 'administrativeAreaLevel3': address_component.get('administrativeAreaLevel3'), 'administrativeAreaLevel2': address_component.get('administrativeAreaLevel2'), 'administrativeAreaLevel1': address_component.get('administrativeAreaLevel1'), 'placeId': address_component.get('placeId'), 'latitude': address_component.get('latitude'), 'longitude': address_component.get('longitude'), 'geoInfo': geojson_polygon, 'name': address_component.get('formattedAddress')}
                lat_log = location_payload.get('latitude', 'N/A')
                lng_log = location_payload.get('longitude', 'N/A')
                print(f'[GEOFENCE] {location_name} → lat={lat_log:.6f}, lng={lng_log:.6f}')
            else:
                for row in variety_rows:
                    row['Status'] = 'Fail'
                    row['varietyID'] = 'NA'
                    row['API Response'] = f"Geocoding failed for location '{location_name}' for variety '{variety_name}'."
                print(f"[GEOFENCE] {location_name} → Failed for variety '{variety_name}'")
                return _format_output_rows(variety_rows)
        else:
            print(f"[GEOFENCE] No location provided for variety '{variety_name}'. Skipping geofencing for yield location.")
        payload_crop_stages = []
        processed_stage_names = set()
        for row in variety_rows:
            stage_name_excel = str(row.get('cropStagename', '')).strip()
            days_after_sowing_excel = row.get('cropStagedaysAfterSowing')
            if not stage_name_excel:
                print(f"Warning: Empty 'cropStagename' found for a row in variety '{variety_name}'. Skipping this stage.")
                continue
            if stage_name_excel.lower() in processed_stage_names:
                print(f"Info: Duplicate crop stage '{stage_name_excel}' for variety '{variety_name}'. Skipping additional entry in payload.")
                continue
            found_stage = None
            if _crop_stages_cache_step3:
                for cs in _crop_stages_cache_step3:
                    if cs.get('name', '').lower() == stage_name_excel.lower():
                        found_stage = cs
                        break
            if found_stage:
                final_days_after_sowing = None
                if days_after_sowing_excel is not None and days_after_sowing_excel != '':
                    try:
                        final_days_after_sowing = int(float(days_after_sowing_excel))
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid 'cropStagedaysAfterSowing' value '{days_after_sowing_excel}' for stage '{stage_name_excel}' in variety '{variety_name}'. Using master data value if available.")
                        final_days_after_sowing = found_stage.get('daysAfterSowing')
                else:
                    final_days_after_sowing = found_stage.get('daysAfterSowing')
                payload_crop_stages.append({'id': found_stage.get('id'), 'name': found_stage.get('name'), 'daysAfterSowing': final_days_after_sowing})
                processed_stage_names.add(stage_name_excel.lower())
            else:
                print(f"Warning: Crop stage '{stage_name_excel}' not found in master data (even after creation) for variety '{variety_name}'. This stage will be ignored.")
        payload = {'name': variety_name, 'nickName': nick_name, 'expectedHarvestDays': expected_harvest_days if expected_harvest_days is not None else None, 'cropId': crop_id, 'cropStages': payload_crop_stages, 'data': {}, 'processStandardDeduction': None, 'cropPrice': None, 'seedGrades': [], 'harvestGrades': [], 'id': None, 'varietyAdditionalAttributeList': []}
        if expected_yield is not None and expected_yield != '':
            yield_per_location = {'data': {}, 'expectedYield': expected_yield, 'expectedYieldUnits': expected_yield_units if expected_yield_units else None, 'refrenceAreaUnits': reference_area_units if reference_area_units else None}
            if location_payload:
                yield_per_location['locations'] = location_payload
            payload['data']['yieldPerLocation'] = [yield_per_location]
        else:
            pass
        print(f"[API] Attempting to add variety: '{variety_name}' (Crop ID: {crop_id})")
        variety_id = 'NA'
        api_response_message = ''
        try:
            response = _log_post(f'{api_base_url}/services/farm/api/varieties', headers=headers, json=payload)
            if response.ok:
                response_json = response.json()
                variety_id = response_json.get('id')
                api_response_message = json.dumps(response_json)
                print(f"[API] Successfully added variety '{variety_name}'. ID: {variety_id}")
                status = 'Pass'
            else:
                status = 'Fail'
                error_detail = response.json().get('title', response.text) if response.content else response.text
                api_response_message = error_detail
                print(f"[ERROR] Failed to add variety '{variety_name}'. Status Code: {response.status_code}, Error: {error_detail}")
        except requests.exceptions.RequestException as e:
            status = 'Fail'
            api_response_message = f'API call failed: {e}'
            print(f"[ERROR] Failed to add variety '{variety_name}'. Exception: {e}")
        for row in variety_rows:
            row['varietyID'] = variety_id
            row['Status'] = status
            row['API Response'] = api_response_message
        return _format_output_rows(variety_rows)

    def _format_output_rows(input_rows):
        """
    Helper function to format the list of input_rows into the final UI output structure.
    """
        output_list = []
        for row in input_rows:
            output_list.append({'name': row.get('name'), 'varietyID': row.get('varietyID', 'NA'), 'cropStagename': row.get('cropStagename'), 'Status': row.get('Status', 'Fail')})
        return output_list
    _new_crop_stages_to_add = set()
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
