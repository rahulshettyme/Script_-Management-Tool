import re

# Read the file
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace google_api_key with Geocoding_api_key in geofence instructions
content = content.replace(
    "env_config.get('google_api_key')",
    "env_config.get('Geocoding_api_key')"
)

# Write back
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed API key name from google_api_key to Geocoding_api_key")
