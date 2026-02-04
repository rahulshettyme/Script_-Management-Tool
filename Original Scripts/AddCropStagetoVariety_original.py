# EXPECTED_INPUT_COLUMNS: name,varietyID,cropStagename,cropStagedaysAfterSowing,cropstagedata

# AI Generated Script - 2026-01-15 18:13:42 IST
import requests
import json
import threading
import thread_utils
import attribute_utils

# Initialize global lock for master data fetching
fetch_lock = threading.Lock()

def run(data, token, env_config):
    base_url = env_config['apiBaseUrl']
    
    # Cache structure: {'crop_stage_map': {lower_name: template_json}}
    cache = {'crop_stage_map': None}

    def fetch_crop_stages_master():
        """Step 1: Fetch and cache crop stages master data (Run Once)."""
        if cache['crop_stage_map'] is None:
            with fetch_lock:
                if cache['crop_stage_map'] is None:
                    url = f"{base_url}/services/farm/api/crop-stages"
                    print(f"Fetching master crop stages from {url}")
                    try:
                        # Headers without Content-Type needed for GET
                        response = requests.get(url, headers={'Authorization': f'Bearer {token}'})
                        response.raise_for_status()
                        stages_list = response.json()
                        
                        # Create map: lowercased_stripped_name -> stage_template
                        stage_map = {}
                        for stage in stages_list:
                            name = str(stage.get('name')).strip().lower()
                            # We store the template structure for later modification
                            stage_map[name] = stage.copy()
                        
                        cache['crop_stage_map'] = stage_map
                        print(f"Successfully cached {len(stage_map)} crop stages.")
                    except requests.exceptions.RequestException as e:
                        print(f"Error fetching crop stages master data: {e}")
                        # If failed, subsequent row processing will fail gracefully
                        cache['crop_stage_map'] = {} 

    # Execute Step 1 Master Data Fetch
    fetch_crop_stages_master()
    
    # ----------------------------------------------------
    # Grouping data by varietyID for aggregated API calls (Steps 2, 3, 4)
    
    grouped_data = {}
    for row in data:
        variety_id = row.get('varietyID')
        
        # Initialize required output columns
        row['status'] = ''
        row['API response'] = ''
        row['cropstagedata'] = '' # Populated during Step 1 validation
        
        if variety_id is not None and str(variety_id).strip():
            k = str(variety_id).strip()
            grouped_data.setdefault(k, []).append(row)
        else:
            row['status'] = 'Skipped'
            row['API response'] = 'Missing or Invalid varietyID.'
            grouped_data.setdefault('_UNGROUPED', []).append(row)


    def process_group(item):
        variety_id, rows = item
        base_url = env_config['apiBaseUrl']
        auth_headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        crop_stage_map = cache['crop_stage_map']

        # 1. Prepare/Validate Crop Stages per row (Step 1 Row Logic)
        if not crop_stage_map:
            # This happens if master data fetch failed
            for row in rows:
                row['status'] = 'Failed Validation'
                row['API response'] = 'Failed to retrieve Crop Stage Master Data.'
            return rows

        valid_stages_data_map = {} # Using a map to ensure uniqueness by stage name

        for row in rows:
            row['_is_valid_stage'] = False
            
            stage_name_input = row.get('cropStagename')
            days_input = row.get('cropStagedaysAfterSowing')

            if stage_name_input is None:
                row['cropstagedata'] = 'Invalid Crop Stage (Name Missing)'
                continue

            stage_name_input = str(stage_name_input).strip()
            lookup_key = stage_name_input.lower()
            template = crop_stage_map.get(lookup_key)

            if template:
                prepared_stage = template.copy()
                
                try:
                    # Try converting daysAfterSowing to integer
                    if days_input is not None and str(days_input).strip() != '':
                        # Use float conversion first to handle inputs like '10.0'
                        days_value = int(float(days_input))
                        prepared_stage['daysAfterSowing'] = days_value
                        
                        # Store JSON string in the required output column
                        row['cropstagedata'] = json.dumps(prepared_stage)
                        row['_is_valid_stage'] = True
                        
                        # Add to unique map (last input wins for the same stage name)
                        valid_stages_data_map[lookup_key] = prepared_stage
                    else:
                        row['cropstagedata'] = 'Invalid Crop Stage (Days must be numeric)'
                except (ValueError, TypeError):
                    row['cropstagedata'] = 'Invalid Crop Stage (Days format error)'
            else:
                row['cropstagedata'] = 'Invalid Crop Stage'
        
        # If no valid stages were prepared across the group, update rows and return
        if not valid_stages_data_map:
            for row in rows:
                if 'status' not in row:
                    row['status'] = 'Validation Failed'
                    row['API response'] = 'No valid crop stages found to update variety.'
            return rows

        # 2. Fetch Existing Variety Details (Step 2)
        variety_url = f"{base_url}/services/farm/api/varieties/{variety_id}"
        variety_payload_template = None
        
        try:
            response_get = requests.get(variety_url, headers={'Authorization': f'Bearer {token}'})
            response_get.raise_for_status()
            variety_payload_template = response_get.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to retrieve Variety {variety_id}. Error: {e}"
            for row in rows:
                row['status'] = 'Error Fetching Variety'
                row['API response'] = error_msg
            return rows
        
        # 3. Logic: Build Final Payload (Step 3)
        
        # 3a. Consolidate new stages
        final_crop_stages = list(valid_stages_data_map.values())

        # 3b. Replace cropStages in the variety payload
        variety_payload_template['cropStages'] = final_crop_stages
        
        # 3c. Update expectedHarvestDays (if column exists)
        # Use value from the first row in the group for consistency
        harvest_days_input = rows[0].get('expectedHarvestDays')
        if harvest_days_input is not None and str(harvest_days_input).strip():
            try:
                # Ensure it's treated as a numeric value
                harvest_days_value = int(float(harvest_days_input))
                variety_payload_template['expectedHarvestDays'] = harvest_days_value
            except (ValueError, TypeError):
                # If conversion fails, keep the existing value from variety_payload_template
                print(f"Warning: Failed to parse expectedHarvestDays '{harvest_days_input}' for variety {variety_id}. Skipping update for this attribute.")
                pass

        # 3d. Add custom attributes (Standard procedure)
        variety_payload_template = attribute_utils.add_attributes_to_payload(
            rows[0], variety_payload_template, env_config, target_key='data'
        )

        # 4. Update Variety API (Step 4)
        update_url = f"{base_url}/services/farm/api/varieties"
        payload = variety_payload_template

        try:
            response_put = requests.put(update_url, headers=auth_headers, data=json.dumps(payload))
            status_code = response_put.status_code
            response_text = response_put.text
            
            # 5. Logging (Step 5)
            if status_code == 200:
                response_summary = "Success"
                
                for row in rows:
                    row['status'] = 'Success'
                    row['API response'] = response_summary
            
            elif status_code >= 400:
                api_response_message = f"HTTP {status_code}"
                
                try:
                    error_data = response_put.json()
                    
                    # Rule 5.2: If 400, write attribute 'title' value
                    if status_code == 400 and 'title' in error_data:
                        api_response_message = error_data['title']
                    elif 'message' in error_data:
                        api_response_message = error_data['message']
                    else:
                        api_response_message = response_text
                        
                except json.JSONDecodeError:
                    api_response_message = response_text

                for row in rows:
                    row['status'] = f'Failed (HTTP {status_code})'
                    row['API response'] = api_response_message
                    
            else:
                for row in rows:
                    row['status'] = f'Failed (HTTP {status_code})'
                    row['API response'] = response_text[:500]

        except requests.exceptions.RequestException as e:
            error_msg = f"Request error during PUT: {e}"
            for row in rows:
                row['status'] = 'Request Failed'
                row['API response'] = error_msg
        
        # Cleanup temporary keys
        for row in rows:
            if '_is_valid_stage' in row:
                del row['_is_valid_stage']

        return rows

    # Separate ungrouped data (if any)
    ungrouped_results = grouped_data.pop('_UNGROUPED', [])
    
    # Run processing in parallel for grouped items
    processed_results = thread_utils.run_in_parallel(
        target_function=process_group,
        items_to_process=list(grouped_data.items()),
        max_workers=env_config.get('max_workers', 5)
    )
    
    # Flatten the results list
    final_results = [row for group_rows in processed_results for row in group_rows]
    
    return final_results + ungrouped_results