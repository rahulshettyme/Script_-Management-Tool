import subprocess
import os

base_dir = r'C:\Users\rahul.shetty\Documents\Important\AntiGravity\Cropin Cloud Github\QA-Ops_Workbench'

print("--- Refreshing Git Index to Restore Missing Scripts ---")

# Stage everything (this will pick up the restored files)
subprocess.run('git add .', shell=True, cwd=base_dir)

# Check status
print("\n--- Current Git Status ---")
result = subprocess.run('git status', shell=True, cwd=base_dir, capture_output=True, text=True)
print(result.stdout)
