@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Dong Bo & Day Len GitHub Pages
echo ========================================================
echo 🚀 ĐANG ĐỒNG BỘ VÀ ĐẨY DỮ LIỆU LÊN GITHUB PAGES...
echo ========================================================
echo.

powershell -ExecutionPolicy Bypass -Command "$src = 'H:\My Drive\tools\KPI_Dashboard_Web'; $dst = 'C:\Users\quoc\Downloads\Auto_CRM_Export_BAM_Cai_Nua'; $files = @('index.html', 'kpi_dashboard.html', 'kpi_data.json', 'ot_tracker.html', 'schedule.html', 'index2.html', 'code.gs', 'README.md', '.gitignore'); foreach ($f in $files) { if (Test-Path \"$src\$f\") { Copy-Item \"$src\$f\" \"$dst\$f\" -Force } }; Copy-Item \"$src\js\" \"$dst\js\" -Recurse -Force; Copy-Item \"$src\css\" \"$dst\css\" -Recurse -Force; Copy-Item \"$src\Data\*\" \"$dst\Data\" -Recurse -Force; Remove-Item \"$dst\Data\Data\" -Recurse -Force -ErrorAction SilentlyContinue"

cd /d "C:\Users\quoc\Downloads\Auto_CRM_Export_BAM_Cai_Nua"
git add index.html kpi_dashboard.html kpi_data.json ot_tracker.html schedule.html index2.html code.gs README.md js/ css/ Data/ .gitignore
git commit -m "Update web dashboard from Google Drive (%date% %time%)"
git push origin main

echo.
echo ========================================================
echo 🎉 ĐÃ ĐẨY LÊN GITHUB PAGES THÀNH CÔNG!
echo ========================================================
pause
