# CONFIG: isMultithreaded = True
# CONFIG: batchSize = 5
# CONFIG: enableGeofencing = False
# CONFIG: allowAdditionalAttributes = False
# EXPECTED_INPUT_COLUMNS: Asset Name, Asset ID, Project ID

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
    Converts Excel serial dates or standard date strings to ISO 8601 format (YYYY-MM-DDT00:00:00.000Z).
    Handles Excel's 1900-based date system.

    Args:
        val: The value to convert, can be float (Excel serial), int, or string.
        col_name (str, optional): The name of the column. Used to determine if a numeric value
                                  should be treated as an Excel serial date.
    Returns:
        str: ISO 8601 formatted date string, or original value if conversion is not applicable/fails.
    """
        if val is None or val == '':
            return None
        date_keywords = ['date', 'dos', 'dob', 'time', 'sowing', 'pruning', 'harvest']
        is_date_column = col_name and any((keyword in col_name.lower() for keyword in date_keywords))
        if isinstance(val, (int, float)):
            if is_date_column:
                try:
                    if val > 59:
                        dt = datetime(1899, 12, 30) + timedelta(days=val)
                    else:
                        dt = datetime(1899, 12, 30) + timedelta(days=val)
                    return dt.strftime('%Y-%m-%dT00:00:00.000Z')
                except Exception:
                    return val
            else:
                return val
        elif isinstance(val, str):
            val_stripped = val.strip()
            if '-' in val_stripped or '/' in val_stripped or ':' in val_stripped:
                try:
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ']:
                        try:
                            dt = datetime.strptime(val_stripped, fmt)
                            return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        except ValueError:
                            continue
                    if is_date_column:
                        try:
                            from dateutil.parser import parse
                            dt = parse(val_stripped)
                            return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        except ImportError:
                            pass
                        except Exception:
                            pass
                    return val_stripped
                except Exception:
                    return val_stripped
            else:
                return val_stripped
        return val

    def process_row(row):
        """
    Processes a single row of data, assigning an asset to a project and then validating it.
    """
        row['Status'] = 'Fail'
        row['Response'] = ''
        row['projectAssetIds'] = None
        row['Assigned status'] = 'Not Processed'
        row['Validated status'] = 'Not Processed'
        row['CA ID'] = None
        asset_name = row.get('Asset Name')
        asset_id = row.get('Asset ID')
        project_id = row.get('Project ID')
        row['Asset Name'] = asset_name
        row['Asset ID'] = asset_id
        if not asset_id:
            row['Response'] = 'Asset ID is missing.'
            return row
        if not project_id:
            row['Response'] = 'Project ID is missing.'
            return row
        headers = {'Authorization': f'Bearer {builtins.token}', 'Content-Type': 'application/json'}
        assign_url = f'{base_url}/services/farm/api/projects/{project_id}/probable-assets'
        assign_payload = [asset_id]
        try:
            assign_response = _log_post(assign_url, headers=headers, json=assign_payload)
            assign_response.raise_for_status()
            assign_result = assign_response.json()
            if assign_result.get('recordsCompleted') == 1:
                row['Assigned status'] = 'Success'
                project_asset_ids = assign_result.get('projectAssetIds')
                if project_asset_ids and isinstance(project_asset_ids, list):
                    row['projectAssetIds'] = project_asset_ids[0]
                else:
                    row['Assigned status'] = 'Fail'
                    row['Response'] = "Assign API succeeded but 'projectAssetIds' not found in response."
            else:
                row['Assigned status'] = 'Fail'
                error_message = assign_result.get('error', 'Unknown error during assignment.')
                row['Response'] = f'Asset assignment failed: {error_message}'
        except requests.exceptions.HTTPError as e:
            row['Assigned status'] = 'Fail'
            row['Response'] = f'Assign API HTTP error: {e.response.status_code} - {e.response.text}'
        except requests.exceptions.RequestException as e:
            row['Assigned status'] = 'Fail'
            row['Response'] = f'Assign API request failed: {e}'
        except json.JSONDecodeError:
            row['Assigned status'] = 'Fail'
            row['Response'] = f'Assign API received non-JSON response: {assign_response.text}'
        except Exception as e:
            row['Assigned status'] = 'Fail'
            row['Response'] = f'An unexpected error occurred during assignment: {e}'
        if row['Assigned status'] == 'Success' and row['projectAssetIds'] is not None:
            validate_url = f'{base_url}/services/farm/api/projects/{project_id}/self-validate-project-assets?cloneFlag=false'
            validate_payload = [row['projectAssetIds']]
            try:
                validate_response = _log_post(validate_url, headers=headers, json=validate_payload)
                validate_response.raise_for_status()
                validate_result = validate_response.json()
                if validate_result.get('recordsCompleted') == 1:
                    row['Validated status'] = 'Success'
                    row['Status'] = 'Pass'
                    croppable_area_ids = validate_result.get('croppableAreaIds')
                    if croppable_area_ids and isinstance(croppable_area_ids, list):
                        row['CA ID'] = croppable_area_ids[0]
                    else:
                        row['Validated status'] = 'Fail'
                        row['Status'] = 'Fail'
                        row['Response'] += "; Validate API succeeded but 'croppableAreaIds' not found in response." if row['Response'] else "Validate API succeeded but 'croppableAreaIds' not found in response."
                else:
                    row['Validated status'] = 'Fail'
                    row['Status'] = 'Fail'
                    error_message = validate_result.get('error', 'Unknown error during validation.')
                    row['Response'] += f'; Asset validation failed: {error_message}' if row['Response'] else f'Asset validation failed: {error_message}'
            except requests.exceptions.HTTPError as e:
                row['Validated status'] = 'Fail'
                row['Status'] = 'Fail'
                row['Response'] += f'; Validate API HTTP error: {e.response.status_code} - {e.response.text}' if row['Response'] else f'Validate API HTTP error: {e.response.status_code} - {e.response.text}'
            except requests.exceptions.RequestException as e:
                row['Validated status'] = 'Fail'
                row['Status'] = 'Fail'
                row['Response'] += f'; Validate API request failed: {e}' if row['Response'] else f'Validate API request failed: {e}'
            except json.JSONDecodeError:
                row['Validated status'] = 'Fail'
                row['Status'] = 'Fail'
                row['Response'] += f'; Validate API received non-JSON response: {validate_response.text}' if row['Response'] else f'Validate API received non-JSON response: {validate_response.text}'
            except Exception as e:
                row['Validated status'] = 'Fail'
                row['Status'] = 'Fail'
                row['Response'] += f'; An unexpected error occurred during validation: {e}' if row['Response'] else f'An unexpected error occurred during validation: {e}'
        else:
            row['Validated status'] = 'Skipped'
            row['Status'] = 'Fail'
            if not row['Response']:
                row['Response'] = 'Skipped validation as asset assignment failed or no projectAssetIds were generated.'
        return row

    def _user_run(data, token, env_config):
        """
    Main entry point for the script. Orchestrates parallel processing of rows.
    """
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
