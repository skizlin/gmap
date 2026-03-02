@echo off
echo Stopping any running servers...
taskkill /F /IM python.exe /T 2>nul

echo.
echo Installing dependencies...
pip install -r backend/requirements.txt

echo.
echo Starting PTC Global Mapper Server...
echo.
echo WAIT for "Application startup complete" message.
echo THEN go to: http://127.0.0.1:8000/feeder-events
echo.

python -m backend.main

pause
