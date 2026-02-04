import requests
import json
import concurrent.futures

def run(data, token, env_config):
    # Extract base URL from config
    base_url = env_config.get('apiBaseUrl')
    api_path = '/services/farm/api/croppable-areas/plot-risk/batch'
    url = f'{base_url}{api_path}'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    batch_size = 25
    indexed_data = []

    # Pre-process data to keep track of indices
    for i, row in enumerate(data):
        try:
            ca_id = row['croppableAreaId']
            f_id = row['farmerId']
            # Ensure croppableAreaName exists or provide default? System says it looks for 'croppableAreaName'
            # We don't need to modify it, just ensure it's in the input data returned at the end.
            indexed_data.append({'croppableAreaId': ca_id, 'farmerId': f_id, '_original_row_index': i})
        except KeyError:
            row['Status'] = 'Input Error'
            row['API response'] = 'Missing required input column: croppableAreaId or farmerId.'

    # Process batches
    for i in range(0, len(indexed_data), batch_size):
        batch = indexed_data[i:i + batch_size]
        if not batch:
            continue
        
        payload = []
        ca_id_map = {}
        for item in batch:
            ca_id = item['croppableAreaId']
            f_id = item['farmerId']
            index = item['_original_row_index']
            payload.append({'croppableAreaId': ca_id, 'farmerId': f_id})
            ca_id_map[str(ca_id)] = index
            
        try:
            print(f"[Log] Sending batch of {len(payload)} items...")
            response = requests.post(url, headers=headers, json=payload)
            status_code = response.status_code
            
            if status_code == 200:
                try:
                    response_json = response.json()
                    sr_plot_details = response_json.get('srPlotDetails', {})
                    
                    for ca_id_str, detail in sr_plot_details.items():
                        original_index = ca_id_map.get(ca_id_str)
                        if original_index is not None:
                            row = data[original_index]
                            
                            # --- FIXED STATUS LOGIC ---
                            item_status = detail.get('status', 'Unknown')
                            # Check for specific failure statuses
                            if item_status == 'SF_VALIDATION_FAILED' or item_status == 'Failed':
                                row['Status'] = 'Failed'
                            else:
                                row['Status'] = 'Success' 
                            
                            row['Code'] = status_code # Add Status Code for UI
                            
                            # --- FIXED MESSAGE LOGIC ---
                            message = detail.get('message', detail.get('error', f'No message found in details for CA {ca_id_str}'))
                            row['API response'] = message
                            
                            sr_plot_id = detail.get('srPlotId')
                            if sr_plot_id:
                                row['srPlotId'] = sr_plot_id
                                
                except json.JSONDecodeError:
                    error_msg = f'Request successful but failed to decode JSON response. Raw response snippet: {response.text[:200]}'
                    for original_index in ca_id_map.values():
                        row = data[original_index]
                        row['Status'] = 'Failed (JSON Error)'
                        row['Code'] = status_code
                        row['API response'] = error_msg
            else:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text
                
                error_response_str = json.dumps(response_data) if isinstance(response_data, dict) else str(response_data)
                for original_index in ca_id_map.values():
                    row = data[original_index]
                    row['Status'] = 'Failed'
                    row['Code'] = status_code
                    row['API response'] = f'API Call Failed (Status {status_code}). Response: {error_response_str}'
                    
        except requests.RequestException as e:
            error_msg = str(e)
            for original_index in ca_id_map.values():
                row = data[original_index]
                row['Status'] = 'Failed'
                row['Code'] = 'Exception'
                row['API response'] = f'Request Exception: {error_msg}'

                row['Status'] = 'Failed'
                row['Code'] = 'Exception'
                row['API response'] = f'Request Exception: {error_msg}'

    # HACK: PR_Batch_Enable modifies 'data' list, NOT 'data_df'.
    # However, runner_bridge initializes 'builtins.data_df' which is STALE at this point.
    # The script_converter will blindly overwrite our result with the stale DataFrame if it exists.
    # We must delete it to signal that 'data' is the source of truth.
    import builtins
    if hasattr(builtins, 'data_df'):
        del builtins.data_df

    return data
