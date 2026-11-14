@echo off
cd /d "%~dp0"
echo ======================================================
echo  Dang ky lich chay tu dong Power BI TEAM CAN THO (08:30 and 13:30)
echo ======================================================
echo.

set "SCRIPT_PATH=%~dp0Run_Auto_PowerBI_Scheduled.bat"

echo [*] Dang dang ky tac vu chay luc 08:30 sang (TEAM CAN THO)...
schtasks /create /tn "Auto_PowerBI_Export_CANTHO_830" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 08:30 /f
if %errorlevel% neq 0 (
    echo [x] That bai khi dang ky tac vu 08:30! Vui long chuot phai chon "Run as Administrator".
    goto end
)

echo [*] Dang dang ky tac vu chay luc 13:30 chieu (1:30 PM) (TEAM CAN THO)...
schtasks /create /tn "Auto_PowerBI_Export_CANTHO_1330" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 13:30 /f
if %errorlevel% neq 0 (
    echo [x] That bai khi dang ky tac vu 13:30! Vui long chuot phai chon "Run as Administrator".
    goto end
)

echo.
echo [V] Dang ky thanh cong ca 2 khung gio 08:30 va 13:30 hang ngay!
echo.

:end
pause
