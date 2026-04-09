@echo off
cd /d "%~dp0"

:: Kill any existing Streamlit on port 8501
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: Start Streamlit in background
start /b py -m streamlit run dashboard.py --server.port 8501 --server.headless true >nul 2>&1

:: Wait for server to come up
timeout /t 4 /nobreak >nul

:: Open in Edge app mode (looks like a native app, no browser chrome)
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:8501 --window-size=1400,900

exit
