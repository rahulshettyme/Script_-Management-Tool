@echo off
echo Starting Script Management Tool and Sharing via ngrok...

:: Start the server in a new window
echo Starting local server on port 3001...
start "Script Management Tool Server" cmd /k "npm start"

:: Wait a few seconds for the server to start
timeout /t 5

:: Start ngrok
echo Starting ngrok tunnel...
start "ngrok Tunnel" cmd /k "ngrok http 3001"

echo.
echo ========================================================
echo Server and ngrok are running!
echo Check the ngrok window for the public URL (e.g., https://xyz.ngrok-free.app)
echo Share that URL with others.
echo ========================================================
pause
