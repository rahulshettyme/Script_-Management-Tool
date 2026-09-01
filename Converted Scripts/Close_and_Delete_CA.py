# CONFIG: isMultithreaded = False
# CONFIG: batchSize = 1
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: CA Name, CA ID, Reason for Closing

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json
    import requests
    import json
    from datetime import datetime, timedelta
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
    global _closePlotReason_list
    _closePlotReason_list = []

    class Builtins:

        def __init__(self):
            self.token = None
            self.env_config = {}

    def excel_to_iso_date(val, col_name=None):
        """
    Converts an Excel date serial number or a date string to ISO 8601 format (YYYY-MM-DDT00:00:00.000Z).
    Handles Excel serial numbers (starting from 1900-01-01) and common string formats.
    Returns None if conversion fails or if input is empty/None.
    """
        if val is None or (isinstance(val, str) and (not val.strip())):
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = col_name and any((keyword in col_name.lower() for keyword in date_keywords))
        if isinstance(val, (int, float)):
            if is_date_column:
                try:
                    base_date = datetime(1899, 12, 30)
                    dt = base_date + timedelta(days=val)
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except Exception as e:
                    print(f"DEBUG: Could not convert Excel serial date {val} for column '{col_name}': {e}")
                    return None
            else:
                return val
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            try:
                if '-' in val and len(val.split('-')[0]) == 4:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                elif '/' in val and len(val.split('/')[2].split(' ')[0]) == 4:
                    dt = datetime.strptime(val.split(' ')[0], '%m/%d/%Y')
                elif '/' in val and len(val.split('/')[0]) <= 2 and (len(val.split('/')[2].split(' ')[0]) == 4):
                    dt = datetime.strptime(val.split(' ')[0], '%d/%m/%Y')
                else:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                return dt.isoformat(timespec='milliseconds') + 'Z'
            except ValueError:
                print(f"DEBUG: Could not parse string date '{val}' for column '{col_name}'.")
                return None
        return val

    def process_row(row: dict) -> dict:
        """
    Processes a single row of data to close and delete a Croppable Area (CA).
    """
        row['Status'] = 'Failed'
        row['Response'] = ''
        row['Close Status'] = ''
        row['Delete Status'] = ''
        row['projectId'] = ''
        row['projectAssetId'] = ''
        row['Reason for Closing_id'] = ''
        ca_name = row.get('CA Name', '')
        ca_id = row.get('CA ID')
        if not ca_id:
            row['Response'] = 'CA ID is missing or empty. Cannot proceed with closing or deleting.'
            print(f"[SKIP] CA Name: '{ca_name}' - {row['Response']}")
            return {'CA Name': ca_name, 'CA ID': '', 'Status': 'Failed'}
        reason_for_closing_name = row.get('Reason for Closing')
        if not reason_for_closing_name or not str(reason_for_closing_name).strip():
            reason_for_closing_name = 'Others'
            print(f"[REASON_LOOKUP] CA ID: '{ca_id}' - 'Reason for Closing' is empty, defaulting to '{reason_for_closing_name}'.")
        reason_lookup_result = master_search.lookup_from_cache(_closePlotReason_list, 'name', reason_for_closing_name, 'id')
        reason_id = None
        if reason_lookup_result['found']:
            reason_id = reason_lookup_result['value']
            row['Reason for Closing_id'] = reason_id
            print(f"[REASON_LOOKUP] CA ID: '{ca_id}' - '{reason_for_closing_name}' → ID: {reason_id}")
        else:
            row['Response'] = f"Reason for Closing '{reason_for_closing_name}' not found in master data. {reason_lookup_result['message']}"
            print(f"[REASON_LOOKUP] CA ID: '{ca_id}' - '{reason_for_closing_name}' → Not Found. {reason_lookup_result['message']}")
        close_ca_url = f'{builtins.env_config.get('apiBaseUrl')}/services/farm/api/croppable-areas/closed'
        close_ca_headers = {'Authorization': f'Bearer {builtins.token}', 'Accept': 'application/json'}
        if not reason_id:
            row['Response'] = f"Cannot close CA '{ca_id}': Reason for Closing ID is missing for '{reason_for_closing_name}'."
            print(f"[CLOSE_CA_SKIP] CA ID: '{ca_id}' - {row['Response']}")
            return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        close_ca_params = {'ids': ca_id, 'reasonId': reason_id}
        print(f"[API_CALL] CA ID: '{ca_id}' - Calling Close_CA (GET {close_ca_url}) with params: {close_ca_params}")
        try:
            close_response = _log_get(close_ca_url, headers=close_ca_headers, params=close_ca_params)
            if close_response.ok:
                close_data = close_response.json()
                if isinstance(close_data, list) and close_data:
                    closed_ca_details = close_data[0]
                    row['Close Status'] = closed_ca_details.get('status', 'N/A')
                    row['projectId'] = closed_ca_details.get('projectId')
                    row['projectAssetId'] = closed_ca_details.get('projectAssetId')
                    print(f"[CLOSE_CA_SUCCESS] CA ID: '{ca_id}' - Status: {row['Close Status']}, Project ID: {row['projectId']}, Project Asset ID: {row['projectAssetId']}")
                    if row['Close Status'] != 'CLOSED':
                        row['Response'] = f"CA '{ca_id}' closed successfully, but final status reported as '{row['Close Status']}' instead of 'CLOSED'."
                    else:
                        row['Response'] = f"CA '{ca_id}' closed successfully."
                else:
                    row['Response'] = f"Close_CA API returned an empty or invalid response for CA ID '{ca_id}'."
                    print(f"[CLOSE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
                    return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
            else:
                error_message = close_response.text
                row['Response'] = f'Close_CA API call failed with status {close_response.status_code}: {error_message}'
                print(f"[CLOSE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
                return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        except requests.exceptions.RequestException as e:
            row['Response'] = f'Close_CA API request failed: {e}'
            print(f"[CLOSE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
            return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        project_id = row.get('projectId')
        project_asset_id = row.get('projectAssetId')
        if not project_id:
            row['Response'] += f" Cannot delete CA '{ca_id}': projectId not found from Close_CA response."
            print(f"[DELETE_CA_SKIP] CA ID: '{ca_id}' - projectId is missing.")
            return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        if not project_asset_id:
            row['Response'] += f" Cannot delete CA '{ca_id}': projectAssetId not found from Close_CA response."
            print(f"[DELETE_CA_SKIP] CA ID: '{ca_id}' - projectAssetId is missing.")
            return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        if row['Close Status'] != 'CLOSED':
            row['Response'] += f" Skipping Delete_CA: CA '{ca_id}' is not in 'CLOSED' status (current status: {row['Close Status']})."
            print(f"[DELETE_CA_SKIP] CA ID: '{ca_id}' - CA not 'CLOSED'.")
            return {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': 'Failed'}
        delete_ca_url = f'{builtins.env_config.get('apiBaseUrl')}/services/farm/api/projects/{project_id}/project-assets/selected-ids'
        delete_ca_params = {'ids': project_asset_id, 'croppableAreaIds': ca_id}
        delete_ca_headers = {'Authorization': f'Bearer {builtins.token}'}
        print(f"[API_CALL] CA ID: '{ca_id}' - Calling Delete_CA (DELETE {delete_ca_url}) with params: {delete_ca_params}")
        try:
            delete_response = _log_delete(delete_ca_url, headers=delete_ca_headers, params=delete_ca_params)
            if delete_response.ok:
                delete_data = delete_response.json()
                if delete_data.get('deletable') == 1:
                    row['Delete Status'] = 'Success'
                    row['Status'] = 'Success'
                    row['Response'] += f" CA '{ca_id}' deleted successfully."
                    print(f"[DELETE_CA_SUCCESS] CA ID: '{ca_id}' - Response: {delete_data}")
                else:
                    row['Delete Status'] = 'Failed'
                    row['Status'] = 'Failed'
                    row['Response'] += f" CA '{ca_id}' deletion reported as non-deletable (deletable: {delete_data.get('deletable', 'N/A')}, nonDeletable: {delete_data.get('nonDeletable', 'N/A')})."
                    print(f"[DELETE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
            else:
                error_message = delete_response.text
                row['Delete Status'] = 'Failed'
                row['Status'] = 'Failed'
                row['Response'] += f' Delete_CA API call failed with status {delete_response.status_code}: {error_message}'
                print(f"[DELETE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
        except requests.exceptions.RequestException as e:
            row['Delete Status'] = 'Failed'
            row['Status'] = 'Failed'
            row['Response'] += f' Delete_CA API request failed: {e}'
            print(f"[DELETE_CA_FAIL] CA ID: '{ca_id}' - {row['Response']}")
        ui_output = {'CA Name': ca_name, 'CA ID': str(ca_id), 'Status': row['Status']}
        return ui_output

    def _user_run(data, token, env_config):
        """
    Main function to process the Excel data.
    """
        builtins.token = token
        builtins.env_config = env_config
        results = []
        global _closePlotReason_list
        print(f"[MASTER_FETCH] Fetching all 'closePlotReason' master data...")
        _closePlotReason_list = master_search.fetch_all('closePlotReason', builtins.env_config)
        if not _closePlotReason_list:
            print("[MASTER_FETCH] WARNING: No 'closePlotReason' master data fetched. All lookups will fail for this master type.")
        else:
            print(f"[MASTER_FETCH] Fetched {len(_closePlotReason_list)} 'closePlotReason' items.")
        for row_data in data:
            result_row = process_row(row_data)
            results.append(result_row)
        return results
    builtins = Builtins()
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
_closePlotReason_list = None
