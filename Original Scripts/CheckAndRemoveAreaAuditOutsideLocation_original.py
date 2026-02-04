# AI Updated - 2026-02-01 21:13:52 IST
import requests
import json
import threading
import thread_utils

# --- OUTPUT MAPPING CONFIGURATION ---
# Script Name: CheckAndRemoveAreaAuditOutsideIndia
# Excel Columns: CA_ID, CA_Name, Latitude, Longitude, is_outside_location, area_audit_status, area_audit_api_response

# UI 'Name' Column: Map from 'CA_Name'.
# UI 'Code' Column: Map from 'area_audit_status' (e.g., Success, Fail, Skipped).
# UI 'Response' Column: Map from 'area_audit_api_response'.
#                       Logic: 'cropAudited = false' or 'cropAudited = true'
#                              or 'HTTP Status: XXX', 'N/A', or error message.
# UI 'Status' Column Logic: Success if response attribute 'cropAudited' = false
#                           Fail if response attribute 'cropAudited' = true
#                           (Other statuses like 'Skipped' also possible based on pre-API conditions).
#
# --- Excel Output Definition ---
# - Column 'is_outside_location': Set to 'YES', 'NO', or 'INVALID_COORD'.
#                                 (Logic: depending on the result of Embedded India Polygon Check - Ray Casting,
#                                 or if Latitude/Longitude parsing fails).
# - Column 'area_audit_status': Set to 'Success', 'Fail', 'Skipped (Inside India)',
#                               'Skipped (Invalid Coordinates)', 'Skipped (Missing CA_ID)',
#                               'Fail (HTTP XXX)', 'Fail (Request Error)'.
#                               (Logic: Success if response attribute 'cropAudited' = false,
#                               Fail if response attribute 'cropAudited' = true, or based on API call outcome/skipping conditions).
# - Column 'area_audit_api_response': Set to 'cropAudited = false', 'cropAudited = true',
#                                     'HTTP Status: XXX', 'N/A', or detailed error message.
#                                     (Logic: put the response attribute cropAudited and its value,
#                                     or HTTP status/error for other cases).
# --- END CONFIGURATION ---


# --- Step 1 [LOGIC]: Define Embedded Simplified India Polygon Coordinates ---
# This is a simplified polygon for illustrative purposes. For production,
# a more detailed and accurate polygon might be required.
# Coordinates are (latitude, longitude)
INDIA_POLYGON = [
    (8.0, 68.0),   # South-West tip
    (8.0, 97.0),   # South-East tip
    (37.0, 97.0),  # North-East approximate
    (37.0, 68.0)   # North-West approximate
    # This polygon is a very crude rectangle approximation for India.
    # A more realistic polygon would have many more points.
    # The commented out example below provides more detail but is not active
    # as per the requirement for a "simplified" polygon and avoiding external APIs for shapefiles.
]

# Note on "Use google API for finding the location" from Step 1 instructions:
# The current implementation uses a pre-defined, embedded `INDIA_POLYGON`.
# Dynamically fetching polygon coordinates for an arbitrary "location provided by user"
# via Google APIs (e.g., Geocoding API + Places API for boundary data) would require:
# 1. An additional input mechanism for the location name (e.g., in env_config).
# 2. A Google API Key to be configured and passed securely.
# 3. Robust error handling for API calls.
# 4. Logic to parse and convert Google API boundary data into the (lat, lon) polygon
#    format expected by `is_point_in_polygon`.
# This is a significant feature enhancement beyond the scope of this update,
# therefore, the static `INDIA_POLYGON` is retained as per "Use embedded simplified polygon coordinates".

# --- Step 3 [LOGIC]: Implement Ray Casting Algorithm ---
def is_point_in_polygon(lat, lon, polygon):
    """
    Checks if a point (lat, lon) is inside a polygon using the Ray Casting algorithm.
    The polygon is a list of (lat, lon) tuples.
    """
    n = len(polygon)
    inside = False

    # Check if point is a vertex of the polygon
    for poly_lat, poly_lon in polygon:
        if lat == poly_lat and lon == poly_lon:
            return True

    # Ray casting algorithm
    p1lat, p1lon = polygon[0]
    for i in range(n + 1):
        p2lat, p2lon = polygon[i % n]

        # Check if point is on a horizontal edge
        # This handles cases where the point's latitude matches a horizontal segment.
        if p1lat == p2lat == lat:
            if min(p1lon, p2lon) <= lon <= max(p1lon, p2lon):
                return True

        # Check for intersection with segment (p1, p2)
        # The ray is cast horizontally to the right from the point (lat, lon)
        # Does the ray cross the vertical extent of the segment?
        if ((p1lat <= lat < p2lat) or (p2lat <= lat < p1lat)):
            # Avoid division by zero for horizontal segments (already handled above explicitly)
            if p2lat - p1lat != 0:
                # Calculate the longitude where the ray intersects the segment
                # Formula for x-intercept of ray: x_intersect = p1lon + (lat - p1lat) * (p2lon - p1lon) / (p2lat - p1lat)
                intersect_lon = p1lon + (lat - p1lat) * (p2lon - p1lon) / (p2lat - p1lat)
                if lon < intersect_lon: # If the intersection is to the right of the point
                    inside = not inside
            # If p2lat - p1lat is 0, it's a horizontal segment.
            # Points on such segments where lat matches p1lat/p2lat are handled by the explicit
            # horizontal edge check at the beginning of the loop.

        p1lat, p1lon = p2lat, p2lon

    return inside

def run(data, token, env_config):
    base_url = env_config.get('apiBaseUrl')
    
    preprocessed_data = []
    
    # --- Step 2 [LOGIC]: Read Input Excel, Convert Lat/Lon, Validate Columns.
    # The 'data' parameter is assumed to be the parsed Excel data (list of dictionaries).
    # This loop handles conversion and validation of lat/lon and initializes output columns.
    for row in data:
        # Renamed from 'is_outside_india' to 'is_outside_location' as per prompt in configuration.
        row.setdefault('is_outside_location', '')
        row.setdefault('area_audit_status', '')
        row.setdefault('area_audit_api_response', '')
        # Ensure CA_Name exists, default to empty string if not present
        row.setdefault('CA_Name', row.get('CA_Name', ''))
        
        try:
            lat = float(str(row.get('Latitude', '')).strip())
            lon = float(str(row.get('Longitude', '')).strip())
            
            # --- Step 3 [LOGIC]: Check point in embedded India geometry ---
            is_inside_india = is_point_in_polygon(lat, lon, INDIA_POLYGON)
            
            # Mark column 'is_outside_location' as 'YES' or 'NO'
            row['is_outside_location'] = 'NO' if is_inside_india else 'YES'
            
        except (ValueError, TypeError):
            row['is_outside_location'] = 'INVALID_COORD'
            
        preprocessed_data.append(row)

    # --- Step 4 [API]: Define Parallel Processing Function (API Execution) ---
    def process_row(row):
        # 'CA_ID' is used for the API call, as per Excel Columns and instructions.
        ca_id = row.get('CA_ID')
        
        # Execute API only if identified as outside India AND CA_ID is present
        if row.get('is_outside_location') == 'YES' and ca_id:
            
            # API Call: DELETE /services/farm/api/croppable-areas/{ca_id}/area-audit
            api_path = f"/services/farm/api/croppable-areas/{ca_id}/area-audit"
            url = f"{base_url}{api_path}"
            headers = {'Authorization': f'Bearer {token}'}
            method = "DELETE"
            
            print(f"[API_DEBUG] {method} {url}")
            
            response_json = {}
            status = "Fail" # Default status
            api_response_str = "N/A" # Default response
            crop_audited = None # Default to None
            
            try:
                response = requests.delete(url, headers=headers)
                
                try:
                    if response.text: # Only attempt JSON decode if there's content
                        response_json = response.json()
                        crop_audited = response_json.get('cropAudited', None)
                except json.JSONDecodeError:
                    # If response.text exists but is not valid JSON, and status is not 204.
                    # This could mean a non-JSON error response or an empty body for non-204.
                    pass
                
                # Determine api_response_str based on 'cropAudited' first, as per mapping
                if crop_audited is not None:
                    # As per UI/Excel mapping: "put the response attribute cropAudited and its value"
                    api_response_str = f"cropAudited = {str(crop_audited).lower()}"
                else:
                    # Fallback for non-standard responses, missing 'cropAudited', or HTTP errors
                    api_response_str = f"HTTP Status: {response.status_code}"
                    if response_json.get('message'):
                        api_response_str += f" | Message: {response_json['message']}"
                    elif response_json.get('title'):
                        api_response_str += f" | Title: {response_json['title']}"
                    elif response.text and not response_json: # If response was not JSON but had text
                        api_response_str += f" | Response Body: {response.text[:100]}..." # Truncate for log
                
                # Determine area_audit_status based on configuration
                if response.status_code in (200, 204):
                    if crop_audited is False:
                        status = "Success" # "Success if response attribute 'cropAudited' = false"
                    elif crop_audited is True:
                        status = "Fail"    # "Fail if response attribute 'cropAudited' = true"
                    else:
                        # If HTTP success but 'cropAudited' is missing/None, treat as success if no other explicit failure.
                        # This condition implies a successful operation despite missing the specific flag,
                        # but we still mark it as 'Success' if the API call was generally successful.
                        status = "Success (cropAudited status indeterminate)"
                else:
                    status = f"Fail (HTTP {response.status_code})"
                    # Error message is already appended to api_response_str above
            
            except requests.exceptions.RequestException as e:
                status = f"Fail (Request Error)"
                api_response_str = str(e)
            
            # Update row outputs
            row['area_audit_status'] = status
            row['area_audit_api_response'] = api_response_str
            
        # Conditions for skipping API call
        elif row.get('is_outside_location') == 'NO':
            row['area_audit_status'] = 'Skipped (Inside India)'
            row['area_audit_api_response'] = 'N/A'
        
        elif row.get('is_outside_location') == 'INVALID_COORD':
            row['area_audit_status'] = 'Skipped (Invalid Coordinates)'
            row['area_audit_api_response'] = 'N/A'
        
        elif not ca_id:
            row['area_audit_status'] = 'Skipped (Missing CA_ID)'
            row['area_audit_api_response'] = 'N/A'
            
        return row

    # --- Step 5 [LOGIC]: Parallel Execution & Return Data ---
    # The script returns the processed list of dictionaries.
    # The platform executing this script is expected to handle writing this
    # data to an Excel file as per the "Excel Output Definition".
    return thread_utils.run_in_parallel(process_row, preprocessed_data)