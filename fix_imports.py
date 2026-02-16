import re

# Read the file
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the geofence import line
content = content.replace(
    'prompt += "\\nfrom components import geofence_utils_v2 as geofence_utils"',
    'prompt += "\\nimport components.geofence_utils_v2 as geofence_utils  # CRITICAL: Use V2, NOT geofence_utils"'
)

# Add builtins import after thread_utils
content = content.replace(
    '''if is_multithreaded:
        prompt += "\\nimport thread_utils  # Direct import, NOT 'from components import thread_utils'"
    if enable_geofencing:''',
    '''if is_multithreaded:
        prompt += "\\nimport thread_utils  # Direct import, NOT 'from components import thread_utils'"
        prompt += "\\nimport builtins  # Required for accessing token/env_config"
    if enable_geofencing:'''
)

# Write back
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed geofence_utils_v2 import syntax")
