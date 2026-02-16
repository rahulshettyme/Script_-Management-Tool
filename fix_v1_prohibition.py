import re

# Read the file
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line with "CRITICAL: Use V2, NOT geofence_utils" and add a stronger prohibition
old_line = 'prompt += "\\nimport components.geofence_utils_v2 as geofence_utils  # CRITICAL: Use V2, NOT geofence_utils"'
new_line = '''prompt += "\\nimport components.geofence_utils_v2 as geofence_utils  # CRITICAL: Use V2, NOT V1"
        prompt += "\\n# FORBIDDEN: Do NOT use 'import components.geofence_utils' - MUST use geofence_utils_v2"'''

content = content.replace(old_line, new_line)

# Write back
with open(r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Manager\script_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added explicit prohibition against geofence_utils V1")
