import os
import shutil
import argparse
import sys
import json
from pathlib import Path

# --- CONFIGURATION ---
# Files/Folders to COPY (Whitelist)
INCLUDE_PATHS = [
    "createbulkdata.html",
    "script.js",
    "style.css",
    "package.json",
    "requirements.txt",
    "backend",          # Whole folder
    "System",           # Whole folder
    "Manager",          # Whole folder (filtered inside)
    "Converted Scripts",# Whole folder (filtered inside)
    "Script Configs",   # Whole folder
    "components"        # Whole folder
]

# Files/Folders to IGNORE (Blacklist overrides whitelist)
IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    ".env",
    "secrets.json",     # Don't deploy secrets? (Review if needed)
    "node_modules",
    
    # Management UI
    "script_management.html",
    "script_management_v2.js",
    "script_dashboard.html",
    "script_dashboard.js",
    "script_onboarding.agent",
    "agent_feedback.json",
    
    # Development/Drafts
    "Draft Scripts",
    "Original Scripts",
    "repro_input.json",
    "debug_credentials.py",
    "install_dependencies.py",
    "test_arghack.py",
    ".cache_master_data",
    "valid_token_BACKUP.txt",
    
    # Self
    "publish_release.py"
]

def load_gitignore_patterns(root_dir):
    """Load patterns from .gitignore if it exists."""
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def is_ignored(path, root_dir):
    """Check if path matches any ignore pattern."""
    rel_path = os.path.relpath(path, root_dir)
    name = os.path.basename(path)
    
    # Check manual blacklist
    for pattern in IGNORE_PATTERNS:
        if pattern == name or pattern == rel_path or (pattern.endswith('/') and rel_path.startswith(pattern[:-1])):
            return True
            
    # Simple glob matching for patterns like *.pyc
    import fnmatch
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
            
    return False

def copy_path(src, dst_root, source_root):
    """Copy file or directory recursively with filtering."""
    if is_ignored(src, source_root):
        print(f"[SKIP] Ignored: {os.path.relpath(src, source_root)}")
        return

    rel_path = os.path.relpath(src, source_root)
    dst = os.path.join(dst_root, rel_path)

    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        
        for item in os.listdir(src):
            s = os.path.join(src, item)
            copy_path(s, dst_root, source_root)
    else:
        # File copy
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
            
        shutil.copy2(src, dst)
        print(f"[COPY] {rel_path}")

def main():
    parser = argparse.ArgumentParser(description="Publish Data Generate Release to Target Folder")
    parser.add_argument("--target", required=True, help="Target directory path for the clean deployment repo")
    args = parser.parse_args()

    source_root = os.getcwd()
    target_root = os.path.abspath(args.target)

    if not os.path.exists(target_root):
        print(f"Creating target directory: {target_root}")
        os.makedirs(target_root)

    print(f"\n--- STARTING PUBLISH ---")
    print(f"Source: {source_root}")
    print(f"Target: {target_root}")
    print("------------------------\n")

    for item_name in INCLUDE_PATHS:
        src_path = os.path.join(source_root, item_name)
        
        if not os.path.exists(src_path):
            print(f"[WARN] Source item not found: {item_name}")
            continue
            
        copy_path(src_path, target_root, source_root)

    print("\n------------------------")
    print("--- PUBLISH COMPLETE ---")
    print("------------------------")

if __name__ == "__main__":
    main()
