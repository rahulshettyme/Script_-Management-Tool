# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: CA Name, CA ID

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json

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

    def _user_run(data, token, env_config):
        import pandas as pd
        import builtins
        import concurrent.futures
        import requests
        import json
        import requests
        import json

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
                return _safe_iloc(row, idx)
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
            except Exception:
                pass
        builtins.token = token
        builtins.base_url = env_config.get('apiBaseUrl')
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

        def _user_run(data, token, env_config):
            api_base_url = env_config.get('apiBaseUrl', '').rstrip('/')
            url = f'{api_base_url}/services/farm/api/croppable-areas/async/plot-risk/status'
            headers = {'Authorization': f'Bearer {token}'}
            processed_data = []
            for row in data:
                processed_row = dict(row)
                ca_name = processed_row.get('CA Name')
                ca_id_raw = processed_row.get('CA ID')
                if ca_id_raw is not None:
                    ca_id = str(ca_id_raw).strip()
                    if ca_id.endswith('.0'):
                        ca_id = ca_id[:-2]
                else:
                    ca_id = ''
                processed_row['CA ID'] = ca_id
                processed_row['CA Name'] = ca_name
                processed_row['Status'] = None
                processed_row['Error'] = None
                processed_row['Message'] = None
                if not ca_id:
                    processed_row['Status'] = 'FAILED'
                    processed_row['Error'] = 'Missing CA ID'
                    processed_row['Message'] = 'CA ID was not found in the input.'
                    processed_data.append(processed_row)
                    continue
                try:
                    params = {'croppableAreaIds': ca_id}
                    response = _log_get(url, headers=headers, params=params)
                    if response.status_code in [200, 201]:
                        res_json = response.json()
                        ca_data_list = res_json.get(ca_id)
                        if ca_data_list and isinstance(ca_data_list, list) and (len(ca_data_list) > 0):
                            ca_data = ca_data_list[0]
                            status = ca_data.get('status')
                            processed_row['Status'] = status
                            if status == 'SUCCESS':
                                processed_row['Error'] = None
                                processed_row['Message'] = None
                            else:
                                processed_row['Error'] = ca_data.get('error')
                                processed_row['Message'] = ca_data.get('message')
                        else:
                            processed_row['Status'] = 'UNKNOWN'
                            processed_row['Error'] = 'No data returned'
                            processed_row['Message'] = f'No status details found for CA ID {ca_id} in the response.'
                    else:
                        processed_row['Status'] = f'API_ERROR_{response.status_code}'
                        processed_row['Error'] = 'HTTP Error'
                        processed_row['Message'] = f'API returned status code {response.status_code}'
                except Exception as e:
                    processed_row['Status'] = 'EXCEPTION'
                    processed_row['Error'] = type(e).__name__
                    processed_row['Message'] = str(e)
                processed_data.append(processed_row)
            return processed_data
        res = _user_run(data, token, env_config)
        try:
            if res is None and hasattr(builtins, 'data_df'):
                import pandas as pd
                if isinstance(builtins.data_df, pd.DataFrame):
                    res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
        except Exception as e:
            print(f'[Warn] Failed to sync data_df to result: {e}')
        return res
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
