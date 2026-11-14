@echo off
cd /d "%~dp0"
echo ======================================================
echo  HUY DANG KY LICH CHAY TU DONG POWER BI (08:30 va 13:30)
echo ======================================================
echo.

schtasks /delete /tn "Auto_PowerBI_Export_CANTHO_830" /f
schtasks /delete /tn "Auto_PowerBI_Export_CANTHO_1330" /f

echo.
echo [V] Da huy dang ky lich tu dong thanh cong!
echo.
pause
