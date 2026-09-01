import os
import subprocess
import shutil
import argparse
import time

# --- CONFIGURATION ---
SRC_BASE = r'C:\Users\rahul.shetty\Documents\Important\AntiGravity\Data Generate'
DST_BASE = r'C:\Users\rahul.shetty\Documents\Important\AntiGravity\Cropin Cloud Github\QA-Ops_Workbench'

# Folders to sync (Whole directories)
FOLDERS = ['backend', 'System', 'Converted Scripts', 'components']

# Individual files to sync (Root only)
FILES = [
    os.path.join('Manager', 'runner_bridge.py'),
    'createbulkdata.html', 
    'script.js', 
    'style.css', 
    'package.json', 
    'requirements.txt',
    'logo.png'
]

def kill_link(path):
    """Safely remove a junction or hardlink without deleting source data."""
    if not os.path.exists(path):
        return
    
    print(f"[CLEANUP] Removing existing path/link: {path}")
    if os.path.isdir(path):
        # Use rmdir to break junctions without touching source
        subprocess.run(f'rmdir "{path}"', shell=True)
        # If it was a real folder, rmdir might fail if not empty, so fallback to rmtree
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            os.remove(path)
        except:
            pass

def sync_folder(src, dst, reverse=False):
    """Use Robocopy for robust, fast directory mirroring."""
    s, d = (dst, src) if reverse else (src, dst)
    
    if not os.path.exists(s):
        print(f"[SKIP] Source folder missing: {s}")
        return

    print(f"[SYNC] {'<--' if reverse else '-->'} Folder: {os.path.basename(s)}")
    
    # Robocopy /MIR : Mirror a directory tree
    # /XF : Exclude files (logs, secrets, audit trails, etc)
    # /XD : Exclude directories
    cmd = f'robocopy "{s}" "{d}" /MIR /XF *.log *.txt *.bak secrets.json audittrail.json audittrail_local.json /XD __pycache__ .git .vscode /NJH /NJS /NDL /NC /NS /NP'
    subprocess.run(cmd, shell=True)

def sync_file(src, dst, reverse=False):
    """Standard file copy."""
    s, d = (dst, src) if reverse else (src, dst)
    
    if not os.path.exists(s):
        print(f"[SKIP] Source file missing: {s}")
        return

    print(f"[COPY] {'<--' if reverse else '-->'} File: {os.path.basename(s)}")
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d)

def main():
    parser = argparse.ArgumentParser(description="Safe One-Way Sync for QA-Ops Workbench")
    parser.add_argument("--back", action="store_true", help="Sync BACK from Deployment to Local (Pull)")
    args = parser.parse_args()

    mode = "BACKWARD (PULL)" if args.back else "FORWARD (PUSH)"
    print("====================================================")
    print(f"SAFE SYNC SYSTEM - MODE: {mode}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================================\n")

    # 1. Cleanup Phase (Only on Forward Push to ensure links are broken)
    if not args.back:
        print("--- Checking for Dangerous Links & Secrets ---")
        for f in FOLDERS:
            kill_link(os.path.join(DST_BASE, f))
        for f in FILES:
            kill_link(os.path.join(DST_BASE, f))
        
        # Explicitly ensure no secrets.json exists in deployment
        potential_secret = os.path.join(DST_BASE, 'System', 'secrets.json')
        if os.path.exists(potential_secret):
            print(f"[SECURITY] Deleting secrets.json from deployment: {potential_secret}")
            os.remove(potential_secret)
            
        print("--- Cleanup Complete ---\n")

    # 2. Sync Folders
    for f in FOLDERS:
        sync_folder(os.path.join(SRC_BASE, f), os.path.join(DST_BASE, f), reverse=args.back)

    # 3. Sync Files
    for f in FILES:
        sync_file(os.path.join(SRC_BASE, f), os.path.join(DST_BASE, f), reverse=args.back)

    print("\n====================================================")
    print(f"FINISHED: {mode} Complete.")
    print("====================================================")

if __name__ == "__main__":
    main()
