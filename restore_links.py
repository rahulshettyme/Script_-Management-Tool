import subprocess
import os

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

print("--- Creating Directory Junctions ---")
for f in folders:
    src = os.path.join(src_base, f)
    dst = os.path.join(dst_base, f)
    if os.path.exists(dst):
        print(f"Skipping (exists): {dst}")
        continue
    cmd = f'mklink /j "{dst}" "{src}"'
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True)

print("\n--- Creating File Hardlinks ---")
for f in files:
    src = os.path.join(src_base, f)
    dst = os.path.join(dst_base, f)
    if os.path.exists(dst):
        print(f"Skipping (exists): {dst}")
        continue
    # Hardlinks (/h) usually don't require admin and stay in sync.
    cmd = f'mklink /h "{dst}" "{src}"'
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True)
