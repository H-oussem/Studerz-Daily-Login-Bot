@echo off
cd /d "%~dp0"
echo ======================================================== >> bot_run.log
echo Run started at: %date% %time% >> bot_run.log
"C:\Python314\python.exe" bot.py >> bot_run.log 2>&1
echo Finished at: %date% %time% >> bot_run.log
