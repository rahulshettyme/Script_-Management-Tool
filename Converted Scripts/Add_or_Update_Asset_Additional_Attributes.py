# CONFIG: isMultithreaded = True
# CONFIG: batchSize = 5
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = True
# EXPECTED_INPUT_COLUMNS: Asset Name, Asset ID

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
    Converts Excel serial dates or common date strings to ISO 8601 format (YYYY-MM-DDT00:00:00.000Z).
    Only converts numeric values if col_name indicates a date.
    """
        if val is None or val == '':
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = col_name and any((keyword in col_name.lower() for keyword in date_keywords))
        if isinstance(val, (int, float)):
            if is_date_column:
                try:
                    if val > 59:
                        dt = datetime(1899, 12, 30) + timedelta(days=int(val) - 1)
                    else:
                        dt = datetime(1899, 12, 30) + timedelta(days=int(val))
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except Exception:
                    return str(val)
            else:
                return str(val)
        if isinstance(val, str):
            val = val.strip()
            if any((char in val for char in ['-', '/'])):
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        dt = datetime.strptime(val, fmt)
                        return dt.isoformat(timespec='milliseconds') + 'Z'
                    except ValueError:
                        pass
                try:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    return dt.isoformat(timespec='milliseconds') + 'Z'
                except ValueError:
                    pass
            return val
        return str(val)

    def process_row(row):
        output_row = {'Asset Name': row.get('Asset Name', ''), 'Asset ID': row.get('Asset ID', ''), 'Status': 'Fail', 'Response': ''}
        asset_id_raw = row.get('Asset ID')
        if not asset_id_raw:
            output_row['Response'] = 'Asset ID is missing in the input row.'
            print(f"Skipping row for Asset Name: '{output_row['Asset Name']}' due to missing Asset ID.")
            return output_row
        try:
            asset_id = int(asset_id_raw)
        except ValueError:
            output_row['Response'] = f"Invalid Asset ID format: '{asset_id_raw}'. Must be a number."
            print(f"Skipping row for Asset Name: '{output_row['Asset Name']}' due to invalid Asset ID: '{asset_id_raw}'.")
            return output_row
        headers = {'Authorization': f'Bearer {builtins.token}'}
        fetch_asset_url = f'{base_url}/services/farm/api/assets/{asset_id}'
        print(f'[FETCH ASSET] Attempting to fetch details for Asset ID: {asset_id}')
        try:
            fetch_response = _log_get(fetch_asset_url, headers=headers)
            fetch_response.raise_for_status()
            asset_details = fetch_response.json()
            print(f'[FETCH ASSET] Asset ID: {asset_id} → Status: {fetch_response.status_code}')
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_message = e.response.text
            output_row['Response'] = f'Failed to fetch asset details (Status: {status_code}): {error_message}'
            print(f'[FETCH ASSET] Asset ID: {asset_id} → Failed: {status_code} - {error_message}')
            return output_row
        except requests.exceptions.RequestException as e:
            output_row['Response'] = f'Request to fetch asset details failed: {e}'
            print(f'[FETCH ASSET] Asset ID: {asset_id} → Request failed: {e}')
            return output_row
        updated_asset_payload = asset_details.copy()
        current_additional_attributes = updated_asset_payload.get('data')
        if not isinstance(current_additional_attributes, dict):
            updated_asset_payload['data'] = {}
        standard_columns = {'Asset Name', 'Asset ID', 'Status', 'Response'}
        print(f'  [Additional Attributes] Merging new attributes for Asset ID: {asset_id}')
        for key, value in row.items():
            if key not in standard_columns:
                converted_value = excel_to_iso_date(value, key)
                updated_asset_payload['data'][key] = converted_value
                print(f"    - Processed attribute '{key}': Original='{value}', Converted='{converted_value}'")
        update_asset_url = f'{base_url}/services/farm/api/assets'
        print(f'[UPDATE ASSET] Attempting to update Asset ID: {asset_id}')
        try:
            files = {'dto': (None, json.dumps(updated_asset_payload), 'application/json')}
            update_response = _log_put(update_asset_url, headers=headers, files=files)
            if update_response.status_code in [200, 201]:
                output_row['Status'] = 'Pass'
                output_row['Response'] = ''
                print(f'[UPDATE ASSET] Asset ID: {asset_id} → Successfully updated (Status: {update_response.status_code})')
            else:
                output_row['Status'] = 'Fail'
                try:
                    error_response_json = update_response.json()
                    output_row['Response'] = f'API Error (Status: {update_response.status_code}): {json.dumps(error_response_json)}'
                except json.JSONDecodeError:
                    output_row['Response'] = f'API Error (Status: {update_response.status_code}): {update_response.text}'
                print(f'[UPDATE ASSET] Asset ID: {asset_id} → Failed (Status: {update_response.status_code})')
        except requests.exceptions.RequestException as e:
            output_row['Status'] = 'Fail'
            output_row['Response'] = f'Request to update asset failed: {e}'
            print(f'[UPDATE ASSET] Asset ID: {asset_id} → Request failed: {e}')
        return output_row

    def _user_run(data, token, env_config):
        builtins.token = token
        builtins.env_config = env_config
        return thread_utils.run_in_parallel(process_func=process_row, items=data, token=token, env_config=env_config)
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
