# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: CA Name, CA ID, Variety Name, Date of Sowing (YYYY-MM-DD)

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
    global _variety_cache
    _variety_cache = {}

    def parse_excel_date(val):
        """
    Converts Excel serial date numbers or typical date string formats to standard target format:
    YYYY-MM-DDT00:00:00.000+0000
    """
        if val is None or str(val).strip() == '':
            return None
        val_str = str(val).strip()
        try:
            val_float = float(val_str)
            if 0 < val_float < 100000:
                dt = datetime(1899, 12, 30) + timedelta(days=val_float)
                return dt.strftime('%Y-%m-%dT00:00:00.000+0000')
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S.%f+0000', '%Y-%m-%dT%H:%M:%SZ'):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.strftime('%Y-%m-%dT00:00:00.000+0000')
            except ValueError:
                continue
        if 'T00:00:00.000+0000' in val_str:
            return val_str
        if len(val_str) >= 10 and val_str[4] in ('-', '/') and (val_str[7] in ('-', '/')):
            prefix = val_str[:10].replace('/', '-')
            return f'{prefix}T00:00:00.000+0000'
        return None

    def process_row(row):
        env_config = builtins.env_config
        variety_name = str(row.get('Variety Name') or '').strip()
        ca_id = row.get('CA ID')
        if not ca_id:
            row['Status'] = 'Fail'
            row['Response'] = 'CA ID is missing'
            return row
        variety_id = None
        if variety_name:
            with _lock:
                cached_val = _variety_cache.get(variety_name.lower())
            if cached_val:
                variety_id = cached_val
                print(f'[LOOKUP_VARIETY] {variety_name} → ID: {variety_id} (Cached)')
            else:
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                url_variety = f'{base_url}/services/farm/api/crops/details/filter?page=0&size=100&sort=name,asc'
                payload_variety = {'search': variety_name}
                try:
                    resp = _log_post(url_variety, headers=headers, json=payload_variety)
                    if resp.ok:
                        data_list = resp.json()
                        for crop in data_list:
                            for child in crop.get('children', []):
                                if child.get('name', '').strip().lower() == variety_name.lower():
                                    variety_id = child.get('id')
                                    break
                            if variety_id:
                                break
                        if not variety_id and data_list:
                            for crop in data_list:
                                children = crop.get('children', [])
                                if children:
                                    variety_id = children[0].get('id')
                                    break
                        if variety_id:
                            with _lock:
                                _variety_cache[variety_name.lower()] = variety_id
                            print(f'[LOOKUP_VARIETY] {variety_name} → ID: {variety_id}')
                        else:
                            print(f'[LOOKUP_VARIETY] {variety_name} → ID: Not Found')
                    else:
                        print(f'[LOOKUP_VARIETY] {variety_name} → API Error: Status {resp.status_code}')
                except Exception as e:
                    print(f'[LOOKUP_VARIETY] {variety_name} → Exception: {str(e)}')
        try:
            ca_id_clean = int(float(ca_id))
        except Exception:
            ca_id_clean = str(ca_id).strip()
        url_get = f'{base_url}/services/farm/api/croppable-areas/{ca_id_clean}'
        headers_get = {'Authorization': f'Bearer {token}'}
        print(f'[CA_LOOKUP] CA ID: {ca_id_clean} → Fetching details')
        try:
            resp_get = _log_get(url_get, headers=headers_get)
            if not resp_get.ok:
                row['Status'] = 'Fail'
                row['Response'] = f'Failed to fetch CA details: {resp_get.status_code}'
                return row
            ca_data = resp_get.json()
        except Exception as e:
            row['Status'] = 'Fail'
            row['Response'] = f'Exception fetching CA details: {str(e)}'
            return row
        if variety_id is not None:
            ca_data['varietyId'] = variety_id
        sowing_date_raw = row.get('Date of Sowing (YYYY-MM-DD)')
        sowing_date_formatted = parse_excel_date(sowing_date_raw)
        if sowing_date_formatted:
            ca_data['sowingDate'] = sowing_date_formatted
        usable_area = ca_data.get('usableArea') or {}
        declared_area = ca_data.get('declaredArea') or {}
        ca_data['usableAreaCount'] = usable_area.get('count')
        ca_data['declaredAreaCount'] = declared_area.get('count')
        ca_data['auditedAreaCount'] = (ca_data.get('auditedArea') or {}).get('count', '')
        if 'caLinkFarmers' not in ca_data:
            ca_data['caLinkFarmers'] = []
        url_put = f'{base_url}/services/farm/api/croppable-areas'
        headers_put = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        try:
            resp_put = _log_put(url_put, headers=headers_put, json=ca_data)
            if resp_put.ok:
                row['Status'] = 'Pass'
            else:
                row['Status'] = 'Fail'
                row['Response'] = f'Failed to update CA: {resp_put.status_code} - {resp_put.text[:200]}'
        except Exception as e:
            row['Status'] = 'Fail'
            row['Response'] = f'Exception updating CA: {str(e)}'
        return row

    def _user_run(data, token, env_config):
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
