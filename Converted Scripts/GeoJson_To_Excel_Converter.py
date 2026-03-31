import json

def run(rows, token, env_config):
    """
    Converts GeoJSON FeatureCollection into a specific Excel format.
    Each feature becomes a new row in the output.
    """
    processed_rows = []
    
    for row in rows:
        geojson_str = row.get('GeoJSON_Data') or row.get('geojson_data') or ''
        
        if not geojson_str:
            # Check for other possible column names if needed
            for k in row.keys():
                if 'geojson' in k.lower():
                    geojson_str = row[k]
                    break
        
        if not geojson_str:
            processed_rows.append({
                "plotID": "N/A",
                "Geo info": "Missing GeoJSON_Data column",
                "Status": "Fail",
                "Response": "No GeoJSON data provided in input"
            })
            continue
            
        try:
            # Support both stringified JSON and dict (if the runner already parsed it)
            if isinstance(geojson_str, str):
                data = json.loads(geojson_str)
            else:
                data = geojson_str
                
            if 'features' not in data:
                processed_rows.append({
                    "plotID": "N/A",
                    "Geo info": "Invalid GeoJSON",
                    "Status": "Fail",
                    "Response": "No features found in FeatureCollection"
                })
                continue
                
            for feature in data['features']:
                # 1. Extract plotID
                plot_id = feature.get('properties', {}).get('plotID')
                
                # 2. Transform Geometry
                # change "type": "Polygon" to "type": "MultiPolygon"
                # change geometry [[[]]] to [[[[]]]] (3 to 4 square bases)
                original_type = feature.get('geometry', {}).get('type', '')
                coords = feature.get('geometry', {}).get('coordinates', [])
                
                new_type = "MultiPolygon"
                new_coords = coords
                
                if original_type == "Polygon":
                    # Wrap once to make it MultiPolygon compatible (3 levels -> 4 levels)
                    new_coords = [coords]
                elif original_type == "MultiPolygon":
                    # Already 4 levels, but user asked for 3 to 4 specifically for Polygon conversion
                    # We will ensure it is 4 levels.
                    new_coords = coords
                
                # 3. Create a blank output format as {"features":[],"type":"FeatureCollection"}
                # Add whole extracted part in step 1 inside "features":[] of step 2
                single_feature_collection = {
                    "features": [{
                        "type": "Feature",
                        "properties": feature.get('properties', {}),
                        "geometry": {
                            "type": new_type,
                            "coordinates": new_coords
                        }
                    }],
                    "type": "FeatureCollection"
                }
                
                # 4. Add to processed rows
                processed_rows.append({
                    "plotID": plot_id,
                    "Geo info": json.dumps(single_feature_collection),
                    "Status": "Pass",
                    "Response": "Successfully Formatted"
                })
                
        except Exception as e:
            processed_rows.append({
                "plotID": "Error",
                "Geo info": str(e),
                "Status": "Fail",
                "Response": f"Processing Error: {str(e)}"
            })
            
    return processed_rows
