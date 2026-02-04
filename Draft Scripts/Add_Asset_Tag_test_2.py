import requests
import json
import thread_utils
import attribute_utils

def run(data, token, env_config):
    """
    Executes the automation script to add an asset tag to assets from Excel data.

    Args:
        data (list of dict): A list of dictionaries, where each dictionary represents a row
                             from the Excel sheet. Expected keys: 'Asset Name', 'Asset ID',
                             'Tag', 'Tag ID', 'Status', 'API_Response'.
        token (str): The authorization token for API calls.
        env_config (dict): A dictionary containing environment-specific configurations,
                           including 'apiBaseUrl'.

    Returns:
        list of dict: The updated list of dictionaries with 'Status' and 'API_Response'
                      for each row.
    """

    # CRITICAL - CACHING / GLOBAL VARIABLES:
    # Initialize a container in `run` to cache master data (e.g., asset tags).
    # This ensures the API call for asset tags is made only once and the data
    # is reused across all rows, avoiding threading/scope issues.
    cache = {'asset_tags': None}

    def process_row(row):
        """
        Processes a single row of Excel data to add an asset tag.

        Args:
            row (dict): A dictionary representing a single row from the Excel sheet.

        Returns:
            dict: The updated row dictionary with processing status and API response.
        """
        api_base_url = env_config['apiBaseUrl']
        headers = {'Authorization': f'Bearer {token}'}

        # Step 1 [API]: Asset Tag Lookup
        # Reads asset_tag_api response, compares attribute "name" with excel column 'Tag'.
        # If data found continue. Else fail row.

        asset_tag_name = row.get('Tag')
        if not asset_tag_name:
            row['Status'] = 'Fail'
            row['API_Response'] = 'Excel column "Tag" is empty.'
            return row

        asset_tag_id = None
        # Access the shared cache for asset tags
        asset_tags_list = cache['asset_tags']

        # If asset tags are not in cache, fetch them
        if asset_tags_list is None:
            asset_tags_url = f"{api_base_url}/services/master/api/filter"
            asset_tags_params = {"type": "ASSET", "size": 5000}
            try:
                asset_tags_resp = requests.get(asset_tags_url, headers=headers, params=asset_tags_params)
                asset_tags_resp.raise_for_status()  # Raise an exception for HTTP errors
                asset_tags_list = asset_tags_resp.json()
                cache['asset_tags'] = asset_tags_list  # Store the response in cache for reuse
            except requests.exceptions.RequestException as e:
                row['Status'] = 'Fail'
                row['API_Response'] = f"Step 1 API call (Asset Tag) failed: {e}"
                return row
            except json.JSONDecodeError:
                row['Status'] = 'Fail'
                row['API_Response'] = f"Step 1 API (Asset Tag) returned invalid JSON: {asset_tags_resp.text}"
                return row

        # Search for the tag by name in the cached list
        found_tag_data = None
        if asset_tags_list:
            for tag in asset_tags_list:
                if tag.get('name') == asset_tag_name:
                    found_tag_data = tag
                    break

        if found_tag_data:
            asset_tag_id = found_tag_data.get('id')
            row['Tag ID'] = asset_tag_id  # Store the found Tag ID in the row
        else:
            row['Status'] = 'Fail'
            row['API_Response'] = 'Tag not Found'
            return row

        # Step 2 [API]: Asset Details
        # Reads asset API response, if data found continue. Else fail row.

        asset_id = row.get('Asset ID')
        if not asset_id:
            row['Status'] = 'Fail'
            row['API_Response'] = 'Excel column "Asset ID" is empty.'
            return row

        asset_details_url = f"{api_base_url}/services/farm/api/assets/{asset_id}"
        asset_details_response = None
        try:
            asset_details_resp = requests.get(asset_details_url, headers=headers)
            asset_details_resp.raise_for_status()
            asset_details_response = asset_details_resp.json()
            # Store the full response temporarily for use in Step 3
            row['_asset_details_response'] = asset_details_response
        except requests.exceptions.RequestException as e:
            row['Status'] = 'Fail'
            row['API_Response'] = f"Step 2 API call (Asset Details) failed: {e}"
            return row
        except json.JSONDecodeError:
            row['Status'] = 'Fail'
            row['API_Response'] = f"Step 2 API (Asset Details) returned invalid JSON: {asset_details_resp.text}"
            return row

        if not asset_details_response:
            row['Status'] = 'Fail'
            row['API_Response'] = 'Asset not Found or empty response from Step 2 API.'
            return row

        # Step 3 [API]: Asset Update
        # Gets the response from asset_api. Updates the attribute "data" with "tags".
        # Sends the whole response with updated data section as body for 'asset_update_api'.

        asset_update_url = f"{api_base_url}/services/farm/api/assets"
        
        # Start with the asset details response from Step 2 as the base payload for update
        payload = row['_asset_details_response'].copy()
        
        # Ensure 'data' field exists in payload and is a dictionary
        if 'data' not in payload or payload['data'] is None:
            payload['data'] = {}
        elif not isinstance(payload['data'], dict):
            # If 'data' exists but is not a dict, log/handle it, then initialize as dict
            # For simplicity, we'll overwrite it to ensure it's a dict.
            payload['data'] = {}

        # Ensure 'tags' field exists within 'data' and is a list
        if 'tags' not in payload['data'] or payload['data']['tags'] is None:
            payload['data']['tags'] = []
        elif not isinstance(payload['data']['tags'], list):
            # If 'tags' exists but is not a list, convert it to a list
            payload['data']['tags'] = [payload['data']['tags']] if payload['data']['tags'] else []

        # Add the new tag ID if it's not already present in the list
        if asset_tag_id is not None and asset_tag_id not in payload['data']['tags']:
            payload['data']['tags'].append(asset_tag_id)
        
        # CRITICAL - Additional Attributes Support:
        # Use attribute_utils.add_attributes_to_payload to inject optional custom attributes
        # The 'tags' are placed within the 'data' object, so target_key='data'.
        payload = attribute_utils.add_attributes_to_payload(row, payload, env_config, target_key='data')

        # CRITICAL - MULTIPART / DTO Support:
        # For Payload Type DTO_FILE, 'Content-Type' must NOT be set explicitly in headers.
        # requests library will set the appropriate 'Content-Type: multipart/form-data'
        # with the correct boundary.
        update_headers = headers.copy() # Make a copy to avoid modifying original headers
        if 'Content-Type' in update_headers:
            del update_headers['Content-Type']

        # Construct the 'dto' file part
        files = {'dto': (None, json.dumps(payload), 'application/json')}

        try:
            asset_update_resp = requests.put(asset_update_url, headers=update_headers, files=files)
            asset_update_resp.raise_for_status()
            update_response_json = asset_update_resp.json()
            row['Status'] = 'Success'
            row['API_Response'] = json.dumps(update_response_json)
        except requests.exceptions.RequestException as e:
            row['Status'] = 'Fail'
            row['API_Response'] = f"Step 3 API call (Asset Update) failed: {e}"
        except json.JSONDecodeError:
            row['Status'] = 'Fail'
            row['API_Response'] = f"Step 3 API (Asset Update) returned invalid JSON: {asset_update_resp.text}"

        return row

    # CRITICAL - Main `run` function MUST return `thread_utils.run_in_parallel(process_row, data)`.
    return thread_utils.run_in_parallel(process_row, data)