@echo off
cd /d "%~dp0"
title Dong Bo Google Sheets Len Web Dashboard
echo ========================================================
echo DANG DONG BO SO LIEU TU GOOGLE SHEETS LEN WEB DASHBOARD...
echo ========================================================
echo.
python sync_sheets_to_web.py
echo.
pause
