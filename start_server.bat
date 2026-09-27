@echo off
echo Starting Data Generate Server...
cd /d "C:\Users\rahul.shetty\Documents\Important\AntiGravity\Data Generate"


set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%PATH%"

call npm start
pause
