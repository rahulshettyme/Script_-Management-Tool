# EXPECTED_INPUT_COLUMNS: name,nickName,expectedHarvestDays,cropName,cropId,expectedYield,expectedYieldUnits,refrenceAreaUnits

# AI Generated Script - 2026-01-14 14:31:44 IST
import requests
import json
import thread_utils
import attribute_utils

def run(data, token, env_config):
    base_url = env_config['apiBaseUrl']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # --- Step 1 & 2 Setup: Caching and Static Data ---
    
    cache = {'crop_map': None}

    # Step 2: Static definition of 'locations' variable
    locations = {
        "bounds": {
            "northeast": {
                "lat": 72.7087158,
                "lng": -66.3193754
            },
            "southwest": {
                "lat": 15.7760139,
                "lng": -173.2992296
            }
        },
        "country": "United States",
        "placeId": "ChIJCzYy5IS16lQRQrfeQ5K5Oxw",
        "latitude": 38.7945952,
        "longitude": -106.5348379,
        "geoInfo": {
            "type": "FeatureCollection",
            "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-173.2992296, 15.7760139], [-66.3193754, 15.7760139], [-66.3193754, 72.7087158], [-173.2992296, 72.7087158], [-173.2992296, 15.7760139]]]
                    }
                }
            ]
        },
        "name": "United States"
    }
    
    # Function to fetch and cache crop data (executed once)
    def fetch_and_cache_crops():
        url = f"{base_url}/services/farm/api/crops?size=1000"
        auth_header = {'Authorization': f'Bearer {token}'}
        try:
            response = requests.get(url, headers=auth_header)
            response.raise_for_status()
            crops = response.json()
            crop_map = {}
            for crop in crops:
                if crop.get('name') and crop.get('id'):
                    crop_map[crop['name']] = crop['id']
            cache['crop_map'] = crop_map
        except Exception as e:
            # Setting to empty map ensures parallel processing doesn't retry fetching master data
            print(f"Error fetching crop data (Step 1): {e}")
            cache['crop_map'] = {} 
    
    if cache['crop_map'] is None:
        fetch_and_cache_crops()


    def process_row(row):
        
        # Initialize output columns (Step 4 preparation)
        row['status'] = 'Pending'
        row['API response'] = ''
        
        crop_map = cache['crop_map']
        
        # --- Step 1 Instructions: Get cropId from cropName ---
        
        crop_name = row.get('cropName')
        
        if not crop_name:
            row['status'] = 'Failed'
            row['API response'] = 'Missing required column: cropName'
            return row
            
        crop_id = crop_map.get(crop_name)
        
        if crop_id is None:
            row['status'] = 'Failed'
            row['API response'] = f"Crop name '{crop_name}' not found in master data."
            # Ensure 'cropId' column is populated, even with None, if needed for schema consistency, 
            # though failure preempts further steps.
            row['cropId'] = None 
            return row
            
        # Write id back to the required column
        row['cropId'] = crop_id 

        # --- Step 3: Add Variety API (POST) ---
        
        try:
            # 1. Prepare and safely cast input values
            expected_yield_value = attribute_utils.safe_cast(row.get('expectedYield'), float)
            expected_harvest_days_value = attribute_utils.safe_cast(row.get('expectedHarvestDays'), int)
            
            # 2. Construct the core payload based on instructions
            payload = {
                "data": {
                    "yieldPerLocation": [{
                        "data": {},
                        "locations": locations, # 1. yieldPerLocation.locations (Static variable)
                        "expectedYield": expected_yield_value, # 2. expectedYield
                        "expectedYieldQuantity": "",
                        "expectedYieldUnits": row.get('expectedYieldUnits'), # 3. expectedYieldUnits
                        "refrenceAreaUnits": row.get('refrenceAreaUnits') # 4. refrenceAreaUnits
                    }]
                },
                "cropId": crop_id, # 5. cropId
                "name": row.get('name'), # 6. name
                "nickName": row.get('nickName'), # 7. nickName
                "expectedHarvestDays": expected_harvest_days_value, # 8. expectedHarvestDays
                "processStandardDeduction": None,
                "cropPrice": None,
                "cropStages": [],
                "seedGrades": [],
                "harvestGrades": [],
                "id": None,
                "varietyAdditionalAttributeList": []
            }

            # 3. Inject custom attributes (CRITICAL RULE)
            # Targeting 'data' key as per common platform convention for variety creation attributes
            payload = attribute_utils.add_attributes_to_payload(row, payload, env_config, target_key='data')
            
            # 4. Execute POST request
            url = f"{base_url}/services/farm/api/varieties"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            api_response = response.json()
            
            # --- Step 4: Add status and API response ---
            row['status'] = 'Success'
            row['API response'] = json.dumps(api_response)

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else 'N/A'
            error_text = e.response.text if e.response is not None else str(e)
            row['status'] = f"Failed (HTTP {status_code})"
            row['API response'] = error_text
        except Exception as e:
            row['status'] = 'Failed (Processing Error)'
            row['API response'] = str(e)
            
        return row

    return thread_utils.run_in_parallel(process_row, data)