import os
import subprocess
import shutil
import time

# --- CONFIGURATION ---
SRC_BASE = r'C:\Users\cropin\Documents\Important\AntiGravity\Data Generate'
DST_BASE = r'C:\Users\cropin\Documents\Important\AntiGravity\Cropin Cloud Github\QA-Ops_Workbench'

# Folders to sync via Junctions (Auto-Sync)
FOLDERS = ['backend', 'System', 'Converted Scripts', 'components']

# Specific Manager files (avoiding generation tools)
MANAGER_FILES = ['runner_bridge.py']

# Root files to sync via Hardlinks (Bidirectional but fragile)
FILES = [
    'createbulkdata.html', 
    'script.js', 
    'style.css', 
    'package.json', 
    'requirements.txt',
    'logo.png'
]

def is_hardlink(file1, file2):
    """Check if two paths point to the same physical file."""
    try:
        if not os.path.exists(file1) or not os.path.exists(file2):
            return False
        return os.path.samefile(file1, file2)
    except OSError:
        return False

def handle_file_sync(src, dst):
    """Detect repairs, sync back if needed, and re-link."""
    if not os.path.exists(src):
        print(f"[ERROR] Source missing: {src}")
        return

    # 1. If destination doesn't exist, just link it
    if not os.path.exists(dst):
        print(f"[LINK] Creating new hardlink: {os.path.basename(dst)}")
        subprocess.run(f'mklink /h "{dst}" "{src}"', shell=True, check=True)
        return

    # 2. Check if already linked
    if is_hardlink(src, dst):
        return

    # 3. LINK BROKEN - Detected regular file in Production
    print(f"[REPAIR] Broken link detected for {os.path.basename(dst)}")
    
    src_mtime = os.path.getmtime(src)
    dst_mtime = os.path.getmtime(dst)

    # Smart Sync: If Production is newer (Git Pull / Merge), pull it to Local
    if dst_mtime > src_mtime + 2: # 2s buffer for filesystem precision
        print(f"  [SYNC-BACK] Production file is NEWER. Copying to local...")
        shutil.copy2(dst, src)
    else:
        print(f"  [SYNC-FORWARD] Local file is NEWER or equal. Re-linking...")

    # 4. Re-establish Link
    try:
        os.remove(dst)
        subprocess.run(f'mklink /h "{dst}" "{src}"', shell=True, check=True)
    except Exception as e:
        print(f"  [ERROR] Failed to link {os.path.basename(dst)}: {e}")

def handle_folder_sync(src, dst):
    """Ensure directory junctions are intact."""
    if not os.path.exists(src):
        os.makedirs(src, exist_ok=True)

    if os.path.exists(dst):
        # Junctions are usually stable unless manually deleted
        return

    print(f"[LINK] Creating directory junction: {os.path.basename(dst)}")
    subprocess.run(f'mklink /j "{dst}" "{src}"', shell=True, check=True)

def main():
    print("====================================================")
    print("STARTING: QA-Ops Workbench - Self-Repairing Sync System")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================================\n")

    # 1. Folders (Junctions)
    print("--- Checking Folders (Junctions) ---")
    for f in FOLDERS:
        src = os.path.join(SRC_BASE, f)
        dst = os.path.join(DST_BASE, f)
        handle_folder_sync(src, dst)

    # 2. Manager Sub-files
    print("\n--- Checking Manager (Individual Files) ---")
    src_mgr = os.path.join(SRC_BASE, "Manager")
    dst_mgr = os.path.join(DST_BASE, "Manager")
    os.makedirs(dst_mgr, exist_ok=True)
    for f in MANAGER_FILES:
        src = os.path.join(src_mgr, f)
        dst = os.path.join(dst_mgr, f)
        handle_file_sync(src, dst)

    # 3. Root Files (Hardlinks)
    print("\n--- Checking Root Files (Hardlinks) ---")
    for f in FILES:
        src = os.path.join(SRC_BASE, f)
        dst = os.path.join(DST_BASE, f)
        handle_file_sync(src, dst)

    print("\n====================================================")
    print("FINISHED: Sync System Check Complete.")
    print("====================================================")

if __name__ == "__main__":
    main()
