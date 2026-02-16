import os

path = r'c:\Users\cropin\Documents\Important\AntiGravity\Data Generate\Converted Scripts'
files = [f for f in os.listdir(path) if f.endswith('.py')]

results = {'v1': [], 'v2': [], 'none': []}

for f in files:
    try:
        with open(os.path.join(path, f), 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        # Check for V1 usage
        if 'from components import geofence_utils' in content or \
           ('import components.geofence_utils' in content and 'geofence_utils_v2' not in content):
            results['v1'].append(f)
        # Check for V2 usage
        elif 'geofence_utils_v2' in content:
            results['v2'].append(f)
        # No geofence usage
        else:
            results['none'].append(f)
    except Exception as e:
        print(f"Error reading {f}: {e}")

print('=' * 60)
print('GEOFENCE USAGE REPORT - CONVERTED SCRIPTS')
print('=' * 60)
print(f'\nV1 Users ({len(results["v1"])}):')
for f in results['v1']:
    print(f'  - {f}')

print(f'\nV2 Users ({len(results["v2"])}):')
for f in results['v2']:
    print(f'  - {f}')

print(f'\nNo Geofence ({len(results["none"])}):')
for f in results['none']:
    print(f'  - {f}')

print('\n' + '=' * 60)
print('SUMMARY:')
print(f'  Total Scripts: {len(files)}')
print(f'  Using V1: {len(results["v1"])}')
print(f'  Using V2: {len(results["v2"])}')
print(f'  Not using geofence: {len(results["none"])}')
print('=' * 60)

if len(results['v1']) == 0:
    print('\n✅ SAFE TO DEPRECATE V1 - No scripts are using it!')
elif len(results['v1']) == 1:
    print(f'\n⚠️  Only 1 script using V1: {results["v1"][0]}')
    print('   You can update this script and then deprecate V1.')
else:
    print(f'\n⚠️  {len(results["v1"])} scripts still using V1.')
    print('   Update these scripts before deprecating V1.')
