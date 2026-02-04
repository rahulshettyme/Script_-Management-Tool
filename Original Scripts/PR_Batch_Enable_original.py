# EXPECTED_INPUT_COLUMNS: croppableAreaId, farmerId,Status,APIresponse

# AI Generated Script - 2026-01-12 16:19:59 IST
import requests
import json
from data_platform import thread_utils
from data_platform import attribute_utils

def run(data, token, env_config):
    base_url = env_config['apiBaseUrl']
    api_path = "/services/farm/api/croppable-areas/plot-risk/batch"
    url = f"{base_url}{api_path}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    batch_size = 25
    
    # 1. Prepare indexed data for batching
    indexed_data = []
    
    # We must handle cases where required input fields might be missing 
    # and map the input row back to its index in the 'data' list.
    
    for i, row in enumerate(data):
        try:
            ca_id = row['croppableAreaId']
            f_id = row['farmerId']
            
            # Ensure IDs are convertible to standard types if needed, though they are usually ints
            indexed_data.append({
                'croppableAreaId': ca_id,
                'farmerId': f_id,
                '_original_row_index': i
            })
        except KeyError:
            # If input keys are missing, mark the row immediately
            row['Status'] = 'Input Error'
            row['APIresponse'] = 'Missing required input column: croppableAreaId or farmerId.'

    # 2. Create and process batches
    for i in range(0, len(indexed_data), batch_size):
        batch = indexed_data[i:i + batch_size]
        
        if not batch:
            continue
            
        payload = []
        ca_id_map = {} # Maps string croppableAreaId -> original index in 'data'
        
        for item in batch:
            ca_id = item['croppableAreaId']
            f_id = item['farmerId']
            index = item['_original_row_index']
            
            payload.append({
                "croppableAreaId": ca_id,
                "farmerId": f_id
            })
            ca_id_map[str(ca_id)] = index
            
        try:
            # Note: We are not using attribute_utils here as the payload is a list of DTO objects, 
            # and the target key for attributes is ambiguous in this list structure.
            response = requests.post(url, headers=headers, json=payload)
            status_code = response.status_code
            
            if status_code == 200:
                # API call succeeded (200). Process individual results from the response body.
                try:
                    response_json = response.json()
                    sr_plot_details = response_json.get('srPlotDetails', {})
                    
                    for ca_id_str, detail in sr_plot_details.items():
                        original_index = ca_id_map.get(ca_id_str)
                        
                        if original_index is not None:
                            row = data[original_index]
                            
                            row['Status'] = 'Success'
                            
                            # Read 'message' or 'error' from the detailed response object
                            message = detail.get('message', detail.get('error', f"No message found in details for CA {ca_id_str}"))
                            row['APIresponse'] = message
                            
                except json.JSONDecodeError:
                    # 200 status but failed to parse JSON response
                    error_msg = f"Request successful but failed to decode JSON response. Raw response snippet: {response.text[:200]}"
                    for original_index in ca_id_map.values():
                        row = data[original_index]
                        row['Status'] = 'Failed (JSON Error)'
                        row['APIresponse'] = error_msg

            else:
                # API failed (not status 200). Write entire response to all rows in the batch.
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text
                
                error_response_str = json.dumps(response_data) if isinstance(response_data, dict) else str(response_data)
                
                for original_index in ca_id_map.values():
                    row = data[original_index]
                    row['Status'] = 'Failed'
                    # Instruction: write entire response for each 'croppableAreaId'
                    row['APIresponse'] = f"API Call Failed (Status {status_code}). Response: {error_response_str}"
                    
        except requests.RequestException as e:
            # Connection or network error
            error_msg = str(e)
            for original_index in ca_id_map.values():
                row = data[original_index]
                row['Status'] = 'Failed'
                row['APIresponse'] = f"Request Exception: {error_msg}"
                
    # 3. Define the mandatory nested process_row function
    def process_row(row):
        # Since the 'data' list was mutated in place during batch processing in the run function, 
        # this function simply returns the already updated row structure.
        return row
        
    # 4. Return the result wrapped in the required parallel execution utility
    return thread_utils.run_in_parallel(process_row, data)