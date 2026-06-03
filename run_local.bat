@echo off
setlocal

set GT7_USE_LOCAL_WEB_SERVICE=true
set DISCORD_GUILD_ID=1488937498120814698

start "GT7 Flask" cmd /k "cd /d %~dp0 && python app.py"
timeout /t 3 /nobreak >nul
start "GT7 Discord Bot" cmd /k "cd /d %~dp0 && python bot_vs.py --local"

endlocal
