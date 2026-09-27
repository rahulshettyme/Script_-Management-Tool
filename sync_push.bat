@echo off
echo [PUSH] Copying Local Work to Deployment Folder...
set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%PATH%"
python "C:\Users\rahul.shetty\Documents\Important\AntiGravity\Data Generate\sync_links.py"
pause
