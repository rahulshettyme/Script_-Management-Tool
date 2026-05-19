import os
import subprocess
import shutil

src_base = r'C:\Users\cropin\Documents\Important\AntiGravity\Data Generate'
dst_base = r'C:\Users\cropin\Documents\Important\AntiGravity\Cropin Cloud Github\QA-Ops_Workbench'

folders = ['backend', 'System', 'Converted Scripts', 'components', 'Manager']
files = [
    'createbulkdata.html', 
    'script.js', 
    'style.css', 
    'package.json', 
    'requirements.txt'
]

def force_remove(path):
    if os.path.exists(path):
        print(f"Removing existing path: {path}")
        if os.path.isdir(path):
            # Try rmdir first (for junctions/links)
            try:
                subprocess.run(f'rmdir "{path}"', shell=True, check=True)
            except:
                # If that fails, try rmtree (for regular folders)
                shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except:
                pass

print("--- Force Restoring Junctions & Links ---")

for f in folders:
    dst = os.path.join(dst_base, f)
    src = os.path.join(src_base, f)
    
    force_remove(dst)
    
    # Create Junction
    cmd = f'mklink /j "{dst}" "{src}"'
    print(f"Creating Junction: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Success: {result.stdout.strip()}")

for f in files:
    dst = os.path.join(dst_base, f)
    src = os.path.join(src_base, f)
    
    force_remove(dst)
    
    # Create Hardlink
    cmd = f'mklink /h "{dst}" "{src}"'
    print(f"Creating Hardlink: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Success: {result.stdout.strip()}")

print("\n--- Final Verification ---")
for f in folders:
    dst = os.path.join(dst_base, f)
    if os.path.exists(dst):
        print(f"Verified: {f} exists at {dst}")
        # Count files to prove it's linked
        try:
            count = len(os.listdir(dst))
            print(f"  Contains {count} items.")
        except:
            print("  Error reading directory.")
    else:
        print(f"FAILED: {f} does not exist!")
