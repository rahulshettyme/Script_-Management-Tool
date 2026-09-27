@echo off
echo [PULL] Copying Deployment Changes back to Local Work Folder...
set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%PATH%"
python "C:\Users\rahul.shetty\Documents\Important\AntiGravity\Data Generate\sync_links.py" --back
pause
