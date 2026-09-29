@echo off
cd /d "%~dp0"
docker --version >nul 2>&1
if errorlevel 1 (
  echo Please install and open Docker Desktop first. See README.md.
  pause
  exit /b 1
)
docker compose up --build -d --wait
if errorlevel 1 (
  echo The app could not start. Make sure Docker Desktop is running.
  echo See README.md for troubleshooting.
  pause
  exit /b 1
)
start "" http://localhost:8080
echo Daylight is running at http://localhost:8080
pause

