@echo off
cd /d "%~dp0"
docker compose stop
echo Your tasks remain saved. Use Start App.cmd to return.
pause
