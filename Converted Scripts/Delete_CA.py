# CONFIG: isMultithreaded = False
# CONFIG: batchSize = 1
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: CA Name, CA ID

def run(data, token, env_config):
    import pandas as pd
    import builtins
    import concurrent.futures
    import requests
    import json
    import requests
    import json
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
    Converts an Excel serial date number or a date string to ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z).
    Handles potential numeric serial numbers from Excel and various string formats.
    
    Args:
        val: The value to convert, can be a float (Excel serial), int, or string.
        col_name (str, optional): The name of the column. Used to determine if a numeric value
                                   should be treated as an Excel date.
    Returns:
        str: ISO 8601 formatted date string, or the original value if conversion is not applicable/fails.
    """
        if col_name and any((keyword in col_name.lower() for keyword in ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest'])):
            if isinstance(val, (int, float)):
                try:
                    if val > 0 and val < 200000:
                        dt = datetime(1899, 12, 30) + timedelta(days=val)
                        return dt.isoformat(timespec='milliseconds') + 'Z'
                except (ValueError, TypeError):
                    pass
        if isinstance(val, str):
            val = val.strip()
            if val:
                try:
                    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'):
                        try:
                            dt = datetime.strptime(val, fmt)
                            return dt.isoformat(timespec='milliseconds') + 'Z'
                        except ValueError:
                            continue
                except (ValueError, TypeError):
                    pass
        return val

    def process_row(row, token, env_config):
        """
    Processes a single row of data to delete a Croppable Area (CA).
    
    Args:
        row (dict): A dictionary representing a single row from the Excel sheet.
        token (str): The authorization token.
        env_config (dict): Dictionary containing environment specific configurations
                           like 'apiBaseUrl'.
                           
    Returns:
        dict: The updated row dictionary with 'Status', 'Response', 'projectId',
              'projectAssetId', and 'Delete Status' fields.
    """
        row['Status'] = 'Failed'
        row['Response'] = ''
        row['projectId'] = None
        row['projectAssetId'] = None
        row['Delete Status'] = 'Failed'
        ca_id = row.get('CA ID')
        ca_name = row.get('CA Name')
        if not ca_id:
            row['Response'] = 'CA ID is missing or empty.'
            print(f'[ERROR] CA Name: {ca_name} - {row['Response']}')
            return row
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        get_ca_url = f'{env_config.get('apiBaseUrl')}/services/farm/api/croppable-areas/{ca_id}'
        try:
            get_ca_response = _log_get(get_ca_url, headers=headers)
            if not get_ca_response.ok:
                error_message = f'Failed to retrieve CA details for CA ID {ca_id}. Status: {get_ca_response.status_code}. Response: {get_ca_response.text}'
                row['Response'] = error_message
                print(f'[GET_CA] {ca_id} → Failed. {error_message}')
                return row
            get_ca_json = get_ca_response.json()
            project_id = get_ca_json.get('projectId')
            project_asset_id = get_ca_json.get('projectAssetId')
            row['projectId'] = project_id
            row['projectAssetId'] = project_asset_id
            print(f'[GET_CA] CA ID: {ca_id} → Project ID: {project_id}, Project Asset ID: {project_asset_id}')
            if not project_id:
                row['Response'] = f"Missing 'projectId' in Get_CA response for CA ID {ca_id}."
                print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
                return row
            if not project_asset_id:
                row['Response'] = f"Missing 'projectAssetId' in Get_CA response for CA ID {ca_id}."
                print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
                return row
        except requests.exceptions.RequestException as e:
            row['Response'] = f'Network or API error during Get_CA for CA ID {ca_id}: {str(e)}'
            print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
            return row
        except json.JSONDecodeError:
            row['Response'] = f'Failed to decode JSON from Get_CA response for CA ID {ca_id}. Response: {get_ca_response.text}'
            print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
            return row
        delete_ca_url = f'{env_config.get('apiBaseUrl')}/services/farm/api/projects/{project_id}/project-assets/selected-ids?ids={project_asset_id}&croppableAreaIds={ca_id}'
        try:
            delete_ca_response = _log_delete(delete_ca_url, headers=headers)
            if not delete_ca_response.ok:
                error_message = f'Failed to delete CA for CA ID {ca_id}. Status: {delete_ca_response.status_code}. Response: {delete_ca_response.text}'
                row['Response'] = error_message
                row['Delete Status'] = 'Failed'
                print(f'[DELETE_CA] {ca_id} → Failed. {error_message}')
                return row
            delete_ca_json = delete_ca_response.json()
            if delete_ca_json.get('deletable') == 1:
                row['Status'] = 'Success'
                row['Delete Status'] = 'Success'
                row['Response'] = 'CA deleted successfully.'
                print(f'[DELETE_CA] CA ID: {ca_id} → Deletable: 1. Status: Success.')
            else:
                row['Status'] = 'Failed'
                row['Delete Status'] = 'Failed'
                non_deletable_count = delete_ca_json.get('nonDeletable', 0)
                row['Response'] = f'CA delete request returned non-deletable status (count: {non_deletable_count}).'
                print(f'[DELETE_CA] CA ID: {ca_id} → Deletable: {delete_ca_json.get('deletable')}. Status: Failed. {row['Response']}')
        except requests.exceptions.RequestException as e:
            row['Response'] = f'Network or API error during Delete_CA for CA ID {ca_id}: {str(e)}'
            row['Delete Status'] = 'Failed'
            print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
            return row
        except json.JSONDecodeError:
            row['Response'] = f'Failed to decode JSON from Delete_CA response for CA ID {ca_id}. Response: {delete_ca_response.text}'
            row['Delete Status'] = 'Failed'
            print(f'[ERROR] CA ID: {ca_id} - {row['Response']}')
            return row
        return row

    def _user_run(data, token, env_config):
        """
    Main function to orchestrate the deletion of Croppable Areas based on provided data.
    
    Args:
        data (list of dict): List of rows, where each row is a dictionary 
                             representing input Excel data.
        token (str): Authorization token.
        env_config (dict): Environment specific configurations.
        
    Returns:
        list of dict: List of processed rows with updated status and response.
    """
        results = []
        for row in data:
            processed_row = process_row(row.copy(), token, env_config)
            results.append(processed_row)
        return results
    res = _user_run(data, token, env_config)
    try:
        if res is None and hasattr(builtins, 'data_df'):
            import pandas as pd
            if isinstance(builtins.data_df, pd.DataFrame):
                res = builtins.data_df.where(pd.notnull(builtins.data_df), None).to_dict(orient='records')
    except Exception as e:
        print(f'[Warn] Failed to sync data_df to result: {e}')
    return res
