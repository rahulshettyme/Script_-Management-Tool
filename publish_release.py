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
    "logo.png",
    "backend",          # Whole folder
    "System",           # Whole folder
    "Manager",          # Whole folder (filtered inside)
    "Converted Scripts",# Whole folder (filtered inside)
    "components"        # Whole folder
]

DEFAULT_TARGETS = [
    "../Data_Generate_Deploy",
    "../Cropin Cloud Github/QA-Ops_Workbench"
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
    
    # Management & Development (Phase 2)
    "script_analyzer.py",
    "script_generator.py",
    "script_converter.py",
    "script_reverser.py",
    "register_scripts.py",
    "manual_conversion_test.py",
    "reproduce_issue.py",
    "test_analyzer_post.py",
    "test_analyzer_post_generic.py",
    "test_output.py",
    "test_farmer_bypass.json",
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
    rel_path = os.path.normpath(os.path.relpath(path, root_dir))
    parts = rel_path.split(os.sep)
    name = os.path.basename(path)
    
    # Special logic for Manager: ONLY allow runner_bridge.py
    if len(parts) > 1 and parts[0] == "Manager":
        if parts[1] != "runner_bridge.py" and name != "Manager":
            return True

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
        return

    rel_path = os.path.relpath(src, source_root)
    dst = os.path.normpath(os.path.join(dst_root, rel_path))
    src = os.path.normpath(src)

    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        
        for item in os.listdir(src):
            s = os.path.join(src, item)
            copy_path(s, dst_root, source_root)
    elif os.path.isfile(src):
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
            
        shutil.copy2(src, dst)
        print(f"[COPY] {rel_path}")
    else:
        # Unexpected item type (e.g. broken link mentioned earlier)
        # We skip these to avoid crashes
        pass

def main():
    parser = argparse.ArgumentParser(description="Publish Data Generate Release to Target Folder")
    parser.add_argument("--target", nargs='+', default=DEFAULT_TARGETS, help="Target directory path(s). Defaults to standard deployment folders.")
    parser.add_argument("--clean", action="store_true", help="Remove target folders before copying to ensure a clean sync.")
    args = parser.parse_args()

    source_root = os.getcwd()
    targets = [os.path.abspath(t) for t in args.target]

    for target_root in targets:
        if not os.path.exists(target_root):
            print(f"Creating target directory: {target_root}")
            os.makedirs(target_root)

        print(f"\n--- STARTING PUBLISH ---")
        print(f"Source: {source_root}")
        print(f"Target: {target_root}")
        if args.clean:
            print("Mode: CLEAN (Target folders will be cleared first)")
        print("------------------------\n")

        for item_name in INCLUDE_PATHS:
            src_path = os.path.join(source_root, item_name)
            dst_path = os.path.join(target_root, item_name)
            
            if not os.path.exists(src_path):
                print(f"[WARN] Source item not found: {item_name}")
                continue
            
            if args.clean and os.path.exists(dst_path):
                print(f"[CLEAN] Removing legacy: {item_name}")
                if os.path.isdir(dst_path):
                    shutil.rmtree(dst_path)
                else:
                    os.remove(dst_path)
                
            copy_path(src_path, target_root, source_root)

    print("\n------------------------")
    print("--- PUBLISH COMPLETE ---")
    print("------------------------")

if __name__ == "__main__":
    main()
