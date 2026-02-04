@echo off
echo Stopping Data Generate Server on Port 3001...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3001" ^| find "LISTENING"') do (
    echo Found process %%a, killing it...
    taskkill /F /PID %%a
)
echo Server Stopped.
pause
