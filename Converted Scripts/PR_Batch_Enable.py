# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: croppableAreaName, croppableAreaId, farmerId, Status, API response, srPlotId

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json
    import requests
    import json
    import time

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

    def process_row(row, status_info=None, batch_error=None):
        """
    Standardizes the output row with required UI and Excel columns.
    """
        row['CA Name'] = row.get('croppableAreaName')
        row['CA ID'] = row.get('croppableAreaId')
        if batch_error:
            row['Status'] = 'Failed'
            row['API response'] = batch_error
        elif status_info:
            row['Status'] = status_info.get('status')
            row['API response'] = status_info.get('message')
            row['srPlotId'] = status_info.get('_id') or status_info.get('srPlotId')
        return row

    def _user_run(data, token, env_config):
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        final_output = []
        for i in range(0, len(data), 25):
            batch_rows = data[i:i + 25]
            batch_payload = []
            for row in batch_rows:
                try:
                    batch_payload.append({'croppableAreaId': int(row.get('croppableAreaId')), 'farmerId': int(row.get('farmerId'))})
                except (ValueError, TypeError):
                    batch_payload.append({'croppableAreaId': row.get('croppableAreaId'), 'farmerId': row.get('farmerId')})
            batch_api_url = f'{base_url}/services/farm/api/croppable-areas/plot-risk/batch'
            try:
                print(f'[PR_BATCH] Processing batch of {len(batch_payload)} areas...')
                response = _log_post(batch_api_url, json=batch_payload, headers=headers)
                if not response.ok:
                    error_response = response.text
                    print(f'[PR_BATCH] Failed with status {response.status_code}')
                    for row in batch_rows:
                        final_output.append(process_row(row, batch_error=error_response))
                    continue
                print(f'[PR_BATCH] Success (200). Waiting 10 seconds for processing...')
                time.sleep(10)
                ca_ids = [str(item['croppableAreaId']) for item in batch_payload]
                status_api_url = f'{base_url}/services/farm/api/croppable-areas/async/plot-risk/status'
                params = {'croppableAreaIds': ','.join(ca_ids)}
                status_res = _log_get(status_api_url, params=params, headers=headers)
                if status_res.ok:
                    status_data_map = status_res.json()
                    for row in batch_rows:
                        cid = str(row.get('croppableAreaId'))
                        if cid in status_data_map and isinstance(status_data_map[cid], list) and (len(status_data_map[cid]) > 0):
                            individual_status = status_data_map[cid][0]
                            final_output.append(process_row(row, status_info=individual_status))
                        else:
                            row['Status'] = 'NOT_FOUND'
                            row['API response'] = 'No status returned for this ID'
                            final_output.append(process_row(row))
                else:
                    status_error = f'Status API Error: {status_res.status_code} - {status_res.text}'
                    print(f'[PR_STATUS] API Call failed: {status_error}')
                    for row in batch_rows:
                        final_output.append(process_row(row, batch_error=status_error))
            except Exception as e:
                print(f'[EXCEPTION] Error during batch processing: {str(e)}')
                for row in batch_rows:
                    final_output.append(process_row(row, batch_error=str(e)))
        return final_output
    "\nOUTPUT MAPPING CONFIGURATION:\n- UI Output Definition:\n  - UI Column 'CA Name': Set to 'croppableAreaName' (Logic: croppableAreaName from excel)\n  - UI Column 'CA ID': Set to 'croppableAreaId' (Logic: croppableAreaId from excel)\n  - UI Column 'Status': Set to 'data.status' (Logic: data.status of PR_Status API)\n- Excel Output Definition:\n   - Column 'Status': Set to 'data.status' (Logic: data.status of PR_Status API)\n   - Column 'API response': Set to 'data.message' (Logic: data.message of PR_Status API)\n   - Column 'srPlotId': Set to 'data._id or data.srPlotId' (Logic: data._id or data.srPlotId of PR_Status API)\n"
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
