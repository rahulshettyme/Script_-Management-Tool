# CONFIG: isMultithreaded = True
# CONFIG: batchSize = 5
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Farmer Name, Farmer ID

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

    def excel_to_iso_date(val, col_name=None):
        """
    Converts an Excel serial date or a date string to ISO 8601 format (YYYY-MM-DDT00:00:00.000Z).
    Only converts numeric values if col_name indicates a date.
    """
        if col_name and any((keyword in col_name.lower() for keyword in ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest'])):
            if isinstance(val, (int, float)):
                try:
                    dt_object = datetime(1899, 12, 30) + timedelta(days=float(val))
                    return dt_object.isoformat(timespec='milliseconds') + 'Z'
                except (ValueError, TypeError):
                    pass
            if isinstance(val, str):
                try:
                    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%b %d, %Y'):
                        try:
                            dt_object = datetime.strptime(val, fmt)
                            return dt_object.isoformat(timespec='milliseconds') + 'Z'
                        except ValueError:
                            continue
                except (ValueError, TypeError):
                    pass
        return val

    def process_row(row):
        """
    Processes a single row of data to fetch farmer details, update additional attributes,
    and then update the farmer via an API call.
    """
        row['Status'] = 'Fail'
        row['Response'] = ''
        farmer_name = row.get('Farmer Name')
        farmer_id = row.get('Farmer ID')
        if not farmer_id:
            row['Response'] = 'Farmer ID is missing or empty in the input.'
            print(f'[ERROR] Skipping row for Farmer Name: {farmer_name} - {row['Response']}')
            return row
        headers = {'Authorization': f'Bearer {builtins.token}', 'Content-Type': 'application/json'}
        fetch_farmer_url = f'{base_url}/services/farm/api/farmers/{farmer_id}'
        try:
            fetch_resp = _log_get(fetch_farmer_url, headers=headers)
            fetch_resp.raise_for_status()
            farmer_data = fetch_resp.json()
            print(f'[FARMER_LOOKUP] Farmer ID: {farmer_id}, Name: {farmer_name} -> Found: {farmer_data.get('firstName')} {farmer_data.get('lastName', '')}')
        except requests.exceptions.RequestException as e:
            row['Response'] = f"Failed to fetch farmer details for ID '{farmer_id}': {str(e)}"
            print(f'[FARMER_LOOKUP] Farmer ID: {farmer_id} -> Failed to fetch details: {str(e)}')
            return row
        except json.JSONDecodeError:
            row['Response'] = f"Failed to decode JSON from fetch farmer details API for ID '{farmer_id}': {fetch_resp.text}"
            print(f'[FARMER_LOOKUP] Farmer ID: {farmer_id} -> Failed to decode JSON: {fetch_resp.text}')
            return row
        current_farmer_data_attributes = (farmer_data.get('data') or {}).copy()
        standard_cols = ['Farmer Name', 'Farmer ID', 'Status', 'Response']
        for key, value in row.items():
            if key not in standard_cols:
                processed_value = excel_to_iso_date(value, key)
                current_farmer_data_attributes[key] = processed_value
        farmer_data['data'] = current_farmer_data_attributes
        update_farmer_url = f'{base_url}/services/farm/api/farmers'
        files = {'dto': (None, json.dumps(farmer_data), 'application/json')}
        try:
            update_resp = _log_put(update_farmer_url, headers={'Authorization': f'Bearer {builtins.token}'}, files=files)
            if update_resp.status_code in [200, 201]:
                row['Status'] = 'Pass'
                row['Response'] = ''
                print(f"Successfully updated farmer ID '{farmer_id}' ({farmer_name}) with additional attributes.")
            else:
                row['Status'] = 'Fail'
                try:
                    error_response = update_resp.json()
                    row['Response'] = f'API Error ({update_resp.status_code}): {error_response.get('message', json.dumps(error_response))}'
                except json.JSONDecodeError:
                    row['Response'] = f'API Error ({update_resp.status_code}, Non-JSON response): {update_resp.text}'
                print(f"Failed to update farmer ID '{farmer_id}' ({farmer_name}). Status Code: {update_resp.status_code}, Response: {row['Response']}")
        except requests.exceptions.RequestException as e:
            row['Response'] = f"Network or connection error while updating farmer ID '{farmer_id}': {str(e)}"
            print(f"Connection error updating farmer ID '{farmer_id}': {str(e)}")
        return row

    def _user_run(data, token, env_config):
        """
    Main function to orchestrate the processing of farmer data in parallel.
    This function initializes the environment for parallel processing.
    """
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)
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
