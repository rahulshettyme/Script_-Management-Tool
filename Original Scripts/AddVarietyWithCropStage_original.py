# EXPECTED_INPUT_COLUMNS: name,nickName,expectedHarvestDays,cropName,cropId,expectedYield,expectedYieldUnits,refrenceAreaUnits,cropStagename,cropStagedaysAfterSowing,cropstagedata,varietyID

# AI Updated Script - 2026-01-15 07:47:38 IST
import requests
import threading
import copy
import thread_utils
import attribute_utils

def run(data, token, env_config):
    # Initialize base_url from env_config
    base_url = env_config.get('BASE_URL')
    if not base_url:
        raise ValueError("BASE_URL not found in env_config")
        
    # Initialize Cache for Master Data (Run Once)
    cache = {'crop_map': None, 'stage_map': None}
    fetch_lock = threading.Lock()
    
    # Static Locations (Step 3) - Definition updated to strictly match the requirement
    locations = {
        'bounds': {
            'northeast': {
                'lat': 72.7087158, 
                'lng': -66.3193754
            }, 
            'southwest': {
                'lat': 15.7760139, 
                'lng': -173.2992296
            }
        }, 
        'country': 'United States', 
        'placeId': 'ChIJCzYy5IS16lQRQrfeQ5K5Oxw', 
        'latitude': 38.7945952, 
        'longitude': -106.5348379, 
        'geoInfo': {
            'type': 'FeatureCollection', 
            'features': [{
                'type': 'Feature', 
                'properties': {}, 
                'geometry': {
                    'type': 'Polygon', 
                    'coordinates': [[[-173.2992296, 15.7760139], [-66.3193754, 15.7760139], [-66.3193754, 72.7087158], [-173.2992296, 72.7087158], [-173.2992296, 15.7760139]]]
                }
            }]
        }, 
        'name': 'United States'
    }
    
    # Helper: Fetch Crops (Step 2)
    def fetch_and_cache_crops():
        # Call GET /services/farm/api/crops?size=1000
        url = f'{base_url}/services/farm/api/crops?size=1000'
        auth_header = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(url, headers=auth_header)
            response.raise_for_status()
            crops = response.json()
            crop_map = {}
            # Instructions: Get 'id' attribute for the column 'cropName'
            for crop in crops:
                if crop.get('name') and crop.get('id'):
                    key = str(crop['name']).strip().lower()
                    crop_map[key] = crop['id']
            cache['crop_map'] = crop_map
        except Exception as e:
            print(f'Error fetching crop data: {e}')
            cache['crop_map'] = {}

    # Helper: Fetch Stages (Step 1)
    def fetch_and_cache_crop_stages():
        # Call GET /services/farm/api/crop-stages
        url = f'{base_url}/services/farm/api/crop-stages'
        auth_header = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(url, headers=auth_header)
            response.raise_for_status()
            stages = response.json()
            stage_map = {}
            # Instructions: compare response attribute "name" for column 'cropStagename'
            for stage in stages:
                if stage.get('name'):
                    key = str(stage['name']).strip().lower()
                    stage_map[key] = stage
            cache['stage_map'] = stage_map
        except Exception as e:
            print(f'Error fetching crop stage data: {e}')
            cache['stage_map'] = {}

    # Execute Master Data Fetch (Double-Checked Locking)
    if cache['crop_map'] is None:
        with fetch_lock:
            if cache['crop_map'] is None:
                fetch_and_cache_crops()
                
    if cache['stage_map'] is None:
        with fetch_lock:
            if cache['stage_map'] is None:
                fetch_and_cache_crop_stages()

    stage_map = cache['stage_map']
    crop_map = cache['crop_map']
    
    if not crop_map:
        raise Exception('Critical Error: Failed to fetch Crop Master Data. Check API connection or Token.')

    # Pre-process Data: Populate 'cropstagedata' and 'cropId' (Steps 1 & 2)
    for row in data:
        # Step 5.1: Initialize Status columns
        row['status'] = 'Pending'
        row['API response'] = ''
        # Step 5.2: Initialize new output column
        row['varietyID'] = None 

        # Step 1: Populate 'cropstagedata'
        stage_name = row.get('cropStagename')
        if stage_name:
            # Lookup stage template using stripped lowercase name (Case Insensitivity & Whitespace preservation)
            stage_template = stage_map.get(str(stage_name).strip().lower())
            if stage_template:
                stage_data = copy.deepcopy(stage_template)
                days = attribute_utils.safe_cast(row.get('cropStagedaysAfterSowing'), int)
                # Instructions: replace attribute 'daysAfterSowing' with value in 'cropStagedaysAfterSowing'
                if days is not None:
                    stage_data['daysAfterSowing'] = days 
                row['cropstagedata'] = stage_data
            else:
                row['cropstagedata'] = None
        else:
            row['cropstagedata'] = None

        # Step 2: Populate 'cropId' column
        crop_name = row.get('cropName')
        if crop_name and crop_map:
            lookup_key = str(crop_name).strip().lower()
            crop_id = crop_map.get(lookup_key)
            if crop_id is not None:
                row['cropId'] = crop_id


    # Group Data by Variety Name (Preparation for Step 4)
    grouped_data = {}
    error_data = [] # For rows without names
    
    for row in data:
        name = row.get('name')
        if name:
            if name not in grouped_data:
                grouped_data[name] = []
            grouped_data[name].append(row)
        else:
            row['status'] = 'Failed'
            row['API response'] = 'Missing required column: name'
            error_data.append(row)

    # Process each Variety Group (Step 4: Add Variety API)
    def process_group(item):
        variety_name, rows = item
        main_row = rows[0] # Use attributes from the first row for the main variety payload
        
        crop_name = main_row.get('cropName')
        if not crop_name:
            # Apply failure status to all rows in the group
            for row in rows:
                row['status'] = 'Failed'
                row['API response'] = 'Missing required column: cropName'
            return rows

        lookup_key = str(crop_name).strip().lower()
        # Look up Crop ID again for validation/current context
        crop_id = crop_map.get(lookup_key) 
        
        if crop_id is None:
            # Apply failure status to all rows in the group
            error_msg = f"Crop name '{crop_name}' not found."
            for row in rows:
                row['status'] = 'Failed'
                row['API response'] = error_msg
            return rows

        # Consolidate Stages from all rows in this group (Step 4.9 logic)
        # 1 API call should have 'name' with all its 'cropStagename' details
        crop_stages = []
        seen_stages = set()
        
        for row in rows:
            stage_data = row.get('cropstagedata')
            if stage_data:
                s_name = stage_data.get('name')
                if s_name and s_name not in seen_stages:
                    crop_stages.append(stage_data)
                    seen_stages.add(s_name)

        try:
            # Build Payload
            payload = {
                'data': {
                    'yieldPerLocation': [{
                        'data': {}, 
                        'locations': locations, # Step 4.1 (Static Locations defined in Step 3)
                        'expectedYield': attribute_utils.safe_cast(main_row.get('expectedYield'), float), # Step 4.2
                        'expectedYieldQuantity': '', 
                        'expectedYieldUnits': main_row.get('expectedYieldUnits'), # Step 4.3
                        'refrenceAreaUnits': main_row.get('refrenceAreaUnits') # Step 4.4
                    }]
                }, 
                'cropId': crop_id, # Step 4.5
                'name': variety_name, # Step 4.6
                'nickName': main_row.get('nickName'), # Step 4.7
                'expectedHarvestDays': attribute_utils.safe_cast(main_row.get('expectedHarvestDays'), int), # Step 4.8
                'processStandardDeduction': None, 
                'cropPrice': None, 
                'cropStages': crop_stages, # Step 4.9 (Consolidated stages)
                'seedGrades': [], 
                'harvestGrades': [], 
                'id': None, 
                'varietyAdditionalAttributeList': []
            }
            
            # API Call
            url = f'{base_url}/services/farm/api/varieties'
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            api_resp = response.json()
            row_id = api_resp.get('id')
            
            status_msg = f'Successfully created Variety ID: {row_id}'

            # Apply success results to ALL rows in the group (Step 5 & CRITICAL INSTRUCTION 10)
            for row in rows:
                row['varietyID'] = row_id # Step 5.2
                row['status'] = 'Success' # Step 5.1
                row['API response'] = status_msg # Step 5.1
            
        except Exception as e:
            error_msg = str(e)
            # Apply failure status to all rows in the group
            for row in rows:
                row['status'] = 'Failed'
                row['API response'] = error_msg

        # Return ALL rows in the group (CRITICAL INSTRUCTION 10)
        return rows

    # Run Parallel
    group_list = list(grouped_data.items())
    results_groups = thread_utils.run_in_parallel(process_group, group_list)
    
    final_data = error_data
    for group_rows in results_groups:
        final_data.extend(group_rows)
        
    return final_data