# EXPECTED_INPUT_COLUMNS: CA ID, CA Name

# AI Updated Script - 2026-01-11 13:48:49 IST
# EXPECTED_INPUT_COLUMNS: CA ID, CA Name
import requests
import json
import thread_utils
import attribute_utils

def run(data, token, env_config):
    """
    Main function to process CA IDs in parallel and fetch CA names from the API.

    Args:
        data (list of dict): A list of dictionaries, where each dictionary represents a row
                             from the Excel sheet. Expected keys: 'CA ID'.
        token (str): The authorization token to be used in API requests.
        env_config (dict): A dictionary containing environment-specific configurations,
                           including 'apiBaseUrl'.

    Returns:
        list of dict: The updated list of dictionaries with 'CA Name', '_status', and '_error'
                      attributes for each row.
    """

    def process_row(row):
        """
        Processes a single row to fetch the Croppable Area (CA) name from the API.
        It updates the row with the fetched 'CA Name' and sets '_status' and '_error'
        based on the API call's outcome.

        Args:
            row (dict): A dictionary representing a single row from the Excel sheet.

        Returns:
            dict: The updated row dictionary.
        """
        ca_id_raw = row.get('CA ID')

        # Validate if 'CA ID' is present and not empty
        if ca_id_raw is None or str(ca_id_raw).strip() == '':
            row['_status'] = 'Failed'
            row['_error'] = "CA ID is missing or empty in the row."
            return row
        
        # Ensure CA ID is a string for URL path construction
        ca_id = str(ca_id_raw)

        # Construct the API URL.
        # env_config['apiBaseUrl'] is assumed to be the base URL for the API endpoints.
        # The API path defined in the workflow is GET /services/farm/api/croppable-areas/<CA ID>
        base_url = env_config['apiBaseUrl'].rstrip('/') # Remove trailing slash to prevent double slashes
        url = f"{base_url}/services/farm/api/croppable-areas/{ca_id}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json' 
        }

        try:
            # Make the GET request to the CA API
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            response_json = response.json()

            # Read attribute 'name' from the response and add it to the 'CA Name' column
            ca_name = response_json.get('name')

            if ca_name is not None:
                row['CA Name'] = ca_name
                row['_status'] = 'Success'
            else:
                row['_status'] = 'Failed'
                row['_error'] = "Attribute 'name' not found in API response or its value was null."

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'N/A'
            response_text = e.response.text if e.response else 'No response text available.'
            row['_status'] = 'Failed'
            row['_error'] = f"API request failed (HTTP {status_code}): {response_text}"
        except requests.exceptions.ConnectionError as e:
            row['_status'] = 'Failed'
            row['_error'] = f"Connection Error: Could not connect to the API server: {e}"
        except requests.exceptions.Timeout as e:
            row['_status'] = 'Failed'
            row['_error'] = f"Request timed out: {e}"
        except requests.exceptions.RequestException as e:
            row['_status'] = 'Failed'
            row['_error'] = f"An unexpected request error occurred: {type(e).__name__}: {e}"
        except json.JSONDecodeError:
            row['_status'] = 'Failed'
            # If JSON decoding fails, try to include the raw response text for debugging
            response_text = response.text if 'response' in locals() else 'No response received'
            row['_error'] = f"Failed to decode JSON from response. Raw response: {response_text}"
        except Exception as e:
            row['_status'] = 'Failed'
            row['_error'] = f"An unexpected error occurred during processing: {type(e).__name__}: {e}"

        return row

    # Process rows in parallel using the thread_utils helper
    return thread_utils.run_in_parallel(process_row, data)