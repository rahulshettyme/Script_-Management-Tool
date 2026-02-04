import sys
import subprocess
import os
from pathlib import Path

def install_dependencies():
    print("=========================================")
    print("🚀  INITIALIZING DEPLOYMENT ENVIRONMENT")
    print("=========================================")

    # 1. Locate check requirements.txt
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ Error: requirements.txt not found!")
        sys.exit(1)

    print(f"📦 Found requirements.txt. Installing dependencies...")
    
    # 2. Run PIP Install
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies. Error: {e}")
        sys.exit(1)

    # 3. Setup Project Directories
    print("\n📂 Verifying Project Directories...")
    
    # Create temp_data if missing (Critical for scripts)
    temp_data = Path("temp_data")
    if not temp_data.exists():
        temp_data.mkdir(parents=True, exist_ok=True)
        print(f"   - Created '{temp_data}' directory.")
    else:
        print(f"   - '{temp_data}' directory exists.")

    print("\n=========================================")
    print("✅  SETUP COMPLETE! READY TO DEPLOY/RUN.")
    print("=========================================")

if __name__ == "__main__":
    install_dependencies()
