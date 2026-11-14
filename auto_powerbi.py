import os
import sys
import time
import glob
import json
import datetime
import threading
import unicodedata
import subprocess
import pandas as pd
import openpyxl
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import gspread
from oauth2client.service_account import ServiceAccountCredentials

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==================== CẤU HÌNH MẶC ĐỊNH ====================
CONFIG_FILE = "auto_pbi_config.json"
CREDENTIALS_FILE = "credentials.json"
CHROME_PROFILE_NAME = "Checkvar_Chrome_Profile"

DEFAULT_POWERBI_URL = "https://app.powerbi.com/groups/f646a92f-6891-413a-9995-d5538eb587df/reports/d407e2bf-c54d-49a6-8599-1251de2d20e1/932d786508d798566e66?experience=power-bi"
DEFAULT_SHEET_KPI_TONG = "https://docs.google.com/spreadsheets/d/1Gp4UVa_6YyQHA9SZxts8ey9z_mwB3j-BEKx20fvPPfk/edit#gid=374267905"
DEFAULT_SHEET_HS_CA_TRUC = "https://docs.google.com/spreadsheets/d/1Gp4UVa_6YyQHA9SZxts8ey9z_mwB3j-BEKx20fvPPfk/edit#gid=999570347"

IS_GUI_MODE = True

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(pbi_url, sheet_kpi_tong, sheet_hs_ca_truc):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "pbi_url": pbi_url,
                "sheet_kpi_tong": sheet_kpi_tong,
                "sheet_hs_ca_truc": sheet_hs_ca_truc
            }, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# ==================== GHI LOG / THÔNG BÁO ====================
def update_status(msg, color="#ffffff"):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{now}] {msg}", flush=True)
    except Exception:
        pass

    if IS_GUI_MODE and 'txt_status' in globals() and txt_status:
        def _append():
            try:
                txt_status.config(state=tk.NORMAL)
                tag_name = color.replace("#", "col_")
                txt_status.tag_config(tag_name, foreground=color)
                txt_status.insert(tk.END, f"[{now}] {msg}\n", tag_name)
                txt_status.see(tk.END)
                txt_status.config(state=tk.DISABLED)
            except Exception:
                pass
        try:
            root.after(0, _append)
        except Exception:
            pass

# ==================== CHUYỂN IFRAME BÁO CÁO ====================
def switch_to_correct_iframe(driver):
    driver.switch_to.default_content()

    def scan():
        try:
            if driver.find_elements(By.CSS_SELECTOR, ".slicer-container, .visual-slicer, .slicer-dropdown-popup, .visual-container"):
                return True
        except Exception:
            pass
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
        except Exception:
            return False
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                if scan():
                    return True
                driver.switch_to.parent_frame()
            except Exception:
                pass
        return False

    for _ in range(15):
        if scan():
            return True
        time.sleep(1)
        driver.switch_to.default_content()
    return False

# ==================== TỰ ĐỘNG ĐĂNG NHẬP MICROSOFT ====================
def handle_microsoft_login(driver):
    current_url = driver.current_url.lower()
    if "login" not in current_url and "microsoftonline" not in current_url and "mysignins" not in current_url:
        return True

    update_status("🔑 Phát hiện màn hình đăng nhập Microsoft, đang tự động xử lý...", "#f39c12")

    for attempt in range(25):
        current_url = driver.current_url.lower()
        if "powerbi.com" in current_url and "login" not in current_url and "microsoftonline" not in current_url and "mysignins" not in current_url:
            update_status("✅ Đăng nhập Microsoft thành công!", "#2ecc71")
            return True

        action_taken = False

        # 1. Bỏ qua màn hình cài app Microsoft Authenticator ("Skip setup" / "Bỏ qua")
        try:
            skips = driver.find_elements(By.XPATH, "//*[contains(text(), 'Skip setup') or contains(text(), 'Skip for now') or contains(text(), 'Bỏ qua')]")
            for link in skips:
                if link.is_displayed():
                    try: link.click()
                    except: driver.execute_script("arguments[0].click();", link)
                    update_status("👉 Đã bấm nút 'Skip setup' (Bỏ qua cài đặt Authenticator)", "#2ecc71")
                    action_taken = True
                    time.sleep(5)
                    break
        except Exception:
            pass

        if action_taken:
            continue

        # 2. Màn hình "Let's keep your account secure" (Click "Use a different account")
        try:
            cancel_links = driver.find_elements(By.XPATH, "//a[@id='cancelLink'] | //a[contains(text(), 'Use a different account')] | //a[contains(text(), 'Sử dụng tài khoản khác')]")
            for link in cancel_links:
                if link.is_displayed():
                    try: link.click()
                    except: driver.execute_script("arguments[0].click();", link)
                    update_status("👉 Đã bấm nút 'Use a different account'", "#2ecc71")
                    action_taken = True
                    time.sleep(5)
                    break
        except Exception:
            pass

        if action_taken:
            continue

        # 3. Điền mật khẩu
        try:
            pwd_fields = driver.find_elements(By.XPATH, "//input[@type='password' or @name='passwd' or @id='i0118']")
            for pwd in pwd_fields:
                if pwd.is_displayed():
                    pwd.clear()
                    pwd.send_keys("DVKH@leaders2026")
                    time.sleep(0.5)
                    pwd.send_keys(Keys.ENTER)
                    update_status("👉 Đã điền mật khẩu DVKH@leaders2026...", "#2ecc71")
                    action_taken = True
                    time.sleep(5)
                    break
        except Exception:
            pass

        if action_taken:
            continue

        # 4. Chọn tài khoản dvkh_leaders@kiotviet.com
        try:
            tiles = driver.find_elements(By.XPATH, """
                //div[@role='button' and (contains(@data-test-id, 'kiotviet.com') or .//small[contains(text(), 'kiotviet.com')])] |
                //div[contains(@class, 'table') and @role='button'] |
                //*[@data-test-id='dvkh_leaders@kiotviet.com']
            """)
            for tile in tiles:
                if tile.is_displayed():
                    try: tile.click()
                    except: driver.execute_script("arguments[0].click();", tile)
                    update_status("👉 Đã chọn tài khoản dvkh_leaders@kiotviet.com", "#2ecc71")
                    action_taken = True
                    time.sleep(5)
                    break
        except Exception:
            pass

        if action_taken:
            continue

        # 5. Màn hình xác nhận Tiếp theo / Có ("Stay signed in" / "Yes" / "Next")
        try:
            btns = driver.find_elements(By.XPATH, "//input[@id='idSIButton9' or @type='submit'] | //button[@id='idSIButton9' or contains(text(), 'Yes') or contains(text(), 'Có') or contains(text(), 'Next') or contains(text(), 'Tiếp theo')]")
            for btn in btns:
                if btn.is_displayed():
                    try: btn.click()
                    except: driver.execute_script("arguments[0].click();", btn)
                    update_status("👉 Đã bấm nút Tiếp theo / Có (Yes)...", "#3498db")
                    action_taken = True
                    time.sleep(5)
                    break
        except Exception:
            pass

        time.sleep(2)

    current_url = driver.current_url.lower()
    return "powerbi.com" in current_url and "login" not in current_url and "microsoftonline" not in current_url

# ==================== XỬ LÝ BỘ LỌC (SLICERS) ====================
def clean_norm(text):
    if not text:
        return ""
    return unicodedata.normalize('NFC', str(text).strip().lower())

def filter_slicer_to_value(driver, name, target_value):
    update_status(f"🔍 Đang lọc cột '{name}' -> '{target_value}'...", "#3498db")
    container = None
    visuals = driver.find_elements(By.CSS_SELECTOR, "visual-container, .visual-container, .visual-container-component")
    for vis in visuals:
        try:
            if vis.text.strip().replace('\n', ' ').startswith(name):
                container = vis
                break
        except Exception:
            pass

    if not container:
        update_status(f"⚠️ Không tìm thấy bộ lọc '{name}'", "#f39c12")
        return False

    # Xóa bộ lọc cũ nếu có nút tẩy
    try:
        clear_btn = container.find_element(By.CSS_SELECTOR, ".slicer-header-clear, .clear-filter, .eraser")
        driver.execute_script("arguments[0].click();", clear_btn)
        time.sleep(1)
    except Exception:
        pass

    # Nếu đích là All, sau khi clear là xong
    if target_value in ["All", "Tất cả"]:
        return True

    # Mở dropdown
    dropdown_btn = None
    try:
        dropdown_btn = container.find_element(By.CSS_SELECTOR, ".slicer-dropdown-button, .slicer-dropdown-menu, .slicer-dropdown, .slicer-chevron, .chevron-down, .dropdown-chevron, .slicer-rest-of-header")
    except Exception:
        pass

    if dropdown_btn:
        driver.execute_script("arguments[0].click();", dropdown_btn)
    else:
        driver.execute_script("arguments[0].click();", container)
    time.sleep(2)

    popup = None
    for _ in range(10):
        try:
            for p in driver.find_elements(By.CSS_SELECTOR, ".slicer-dropdown-popup"):
                if p.is_displayed():
                    popup = p
                    break
        except Exception:
            pass
        if popup:
            break
        time.sleep(0.5)

    if not popup:
        update_status(f"⚠️ Không tìm thấy popup dropdown cho '{name}'", "#f39c12")
        return False

    target_norm = clean_norm(target_value)
    target_item = None
    for item in popup.find_elements(By.CSS_SELECTOR, ".slicerItemContainer"):
        try:
            if target_norm == clean_norm(item.get_attribute("title")) or target_norm in clean_norm(item.text):
                target_item = item
                break
        except Exception:
            pass

    if not target_item:
        update_status(f"⚠️ Không có giá trị '{target_value}' trong bộ lọc '{name}'", "#f39c12")
        if dropdown_btn:
            try: driver.execute_script("arguments[0].click();", dropdown_btn)
            except Exception: pass
        return False

    driver.execute_script("arguments[0].scrollIntoView(true);", target_item)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target_item)
    time.sleep(1.5)

    if dropdown_btn:
        try: driver.execute_script("arguments[0].click();", dropdown_btn)
        except Exception: pass
    time.sleep(1)
    update_status(f"✅ Đã chọn '{target_value}' cho cột '{name}'!", "#2ecc71")
    return True

# ==================== XUẤT DỮ LIỆU VISUAL RA EXCEL ====================
def export_visual(driver, visual_element, temp_dir, export_name, export_mode="summarized"):
    for f in glob.glob(os.path.join(temp_dir, "*.*")):
        try: os.remove(f)
        except Exception: pass

    # Cuộn tới visual
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visual_element)
    time.sleep(1)

    # Hover để hiện nút 3 chấm (...)
    try:
        driver.execute_script("""
            var el = arguments[0];
            while (el) {
                if (el.classList && (el.classList.contains('visualContainer') || el.classList.contains('visual-container') || el.classList.contains('visualWrapper') || el.classList.contains('visual-container-component'))) {
                    var ev1 = new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window });
                    var ev2 = new MouseEvent('mousemove', { bubbles: true, cancelable: true, view: window });
                    el.dispatchEvent(ev1);
                    el.dispatchEvent(ev2);
                }
                el = el.parentElement;
            }
        """, visual_element)
    except Exception:
        pass

    try:
        ActionChains(driver).move_to_element(visual_element).perform()
        time.sleep(0.5)
    except Exception:
        pass

    width = visual_element.size['width']
    height = visual_element.size['height']
    try:
        ActionChains(driver).move_to_element_with_offset(visual_element, width/2 - 30, -height/2 + 15).perform()
        time.sleep(0.5)
    except Exception:
        pass

    menu_btn = None
    selectors = [".vcMenuBtn", "button[title='More options']", "button[title='Thao tác khác']", ".pb-visual-menu-container"]
    for _ in range(12):
        for sel in selectors:
            try:
                btns = visual_element.find_elements(By.CSS_SELECTOR, sel)
                if btns:
                    menu_btn = btns[0]
                    break
            except Exception:
                pass
        if menu_btn:
            break
        time.sleep(0.5)

    if not menu_btn:
        raise Exception(f"Không tìm thấy nút menu 3 chấm (...) của bảng {export_name}")

    driver.execute_script("arguments[0].click();", menu_btn)
    time.sleep(2)

    # Chọn Export data
    export_menu_item = None
    menu_items = driver.find_elements(By.XPATH, "//*[contains(text(), 'Export data')] | //*[contains(text(), 'Xuất dữ liệu')] | //span[contains(text(), 'Export data')]")
    for item in menu_items:
        export_menu_item = item
        if item.is_displayed():
            break

    if not export_menu_item:
        raise Exception(f"Không tìm thấy mục 'Export data' trong menu bảng {export_name}")

    driver.execute_script("arguments[0].click();", export_menu_item)
    time.sleep(2.5)

    # Chuyển ra default content để thao tác trên hộp thoại Export
    driver.switch_to.default_content()

    if export_mode == "layout":
        # Chọn "Data with current layout" cho bảng ma trận HS ca trực
        update_status(f"📐 [{export_name}] Đang chọn chế độ 'Data with current layout'...", "#3498db")
        try:
            layout_opts = driver.find_elements(By.XPATH, "//*[contains(text(), 'current layout') or contains(text(), 'bố cục hiện tại')]")
            for opt in layout_opts:
                if opt.is_displayed():
                    driver.execute_script("arguments[0].click();", opt)
                    time.sleep(1)
                    break
        except Exception as e:
            update_status(f"⚠️ Lỗi chọn layout: {e}", "#f39c12")
    else:
        # Chọn "Summarized data"
        update_status(f"📊 [{export_name}] Đang chọn chế độ 'Summarized data'...", "#3498db")
        try:
            summarized_opts = driver.find_elements(By.XPATH, "//*[contains(text(), 'Summarized data') or contains(text(), 'Dữ liệu được tóm tắt')] | //span[contains(text(), 'Summarized data')]")
            for opt in summarized_opts:
                if opt.is_displayed():
                    driver.execute_script("arguments[0].click();", opt)
                    time.sleep(1)
                    break
        except Exception as e:
            update_status(f"⚠️ Lỗi chọn summarized: {e}", "#f39c12")

    # Bấm nút xác nhận Export
    confirm_btn = None
    dialog_selectors = ["button[data-testid='export-btn']", "button.exportButton", "button.primaryBtn", "//button[@data-testid='export-btn']", "//button[contains(@class, 'exportButton')]"]
    for sel in dialog_selectors:
        try:
            btns = driver.find_elements(By.XPATH if sel.startswith("//") else By.CSS_SELECTOR, sel)
            for btn in btns:
                if "app-bar" not in (btn.get_attribute("class") or "") and btn.is_displayed():
                    confirm_btn = btn
                    break
            if confirm_btn: break
        except Exception:
            pass

    if not confirm_btn:
        btns = driver.find_elements(By.XPATH, "//button[text()='Export' and not(contains(@class, 'app-bar'))] | //button[text()='Xuất' and not(contains(@class, 'app-bar'))] | //span[text()='Export']/.. | //span[text()='Xuất']/..")
        for btn in btns:
            if btn.is_displayed():
                confirm_btn = btn
                break

    if not confirm_btn:
        switch_to_correct_iframe(driver)
        for sel in ["button[data-testid='export-btn']", "button.exportButton", "button.primaryBtn"]:
            try:
                btns = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in btns:
                    if btn.is_displayed():
                        confirm_btn = btn
                        break
                if confirm_btn: break
            except Exception:
                pass

    if not confirm_btn:
        raise Exception(f"Không tìm thấy nút 'Export' xác nhận tải bảng {export_name}")

    driver.execute_script("arguments[0].click();", confirm_btn)
    update_status(f"⏳ [{export_name}] Đã bấm Xuất file, đang đợi tải về...", "#e67e22")

    # Đợi file tải xong
    downloaded_file = None
    for i in range(60):
        files = glob.glob(os.path.join(temp_dir, "*.*"))
        files = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if files:
            time.sleep(2)
            downloaded_file = files[0]
            break
        time.sleep(1)

    if not downloaded_file:
        raise Exception(f"Không tải được file Excel cho bảng {export_name} sau 60 giây")

    dest_file = f"PowerBI_Export_{export_name}.xlsx"
    import shutil
    shutil.copy(downloaded_file, dest_file)
    update_status(f"💾 [{export_name}] Đã lưu file Excel: {dest_file}", "#2ecc71")
    return dest_file

# ==================== ĐỒNG BỘ DỮ LIỆU LÊN GOOGLE SHEETS ====================
def sync_data_to_google_sheet(file_kpi_tong, file_hs_ca_truc, sheet_kpi_url, sheet_hs_url, update_time_val=None):
    update_status("📡 Đang đồng bộ dữ liệu lên Google Sheets...", "#3498db")
    
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Không tìm thấy file {CREDENTIALS_FILE} trong thư mục tool!")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)

    # Hàm parse GID hoặc mở sheet
    def get_worksheet_by_url(url, default_title=None):
        sh = client.open_by_url(url)
        gid = None
        if "#gid=" in url:
            gid = url.split("#gid=")[-1].split("&")[0]
        elif "gid=" in url:
            import re
            m = re.search(r'gid=(\d+)', url)
            if m: gid = m.group(1)

        if gid is not None:
            try:
                gid_int = int(gid)
                for ws in sh.worksheets():
                    if ws.id == gid_int:
                        return sh, ws
            except Exception:
                pass
        if default_title:
            try:
                return sh, sh.worksheet(default_title)
            except Exception:
                pass
        return sh, sh.get_worksheet(0)

    # 1. Cập nhật sheet KPI tong
    if file_kpi_tong and os.path.exists(file_kpi_tong):
        update_status("📄 Đang cập nhật bảng 'KPI tong' lên Google Sheet...", "#3498db")
        sh_kpi, ws_kpi = get_worksheet_by_url(sheet_kpi_url, "KPI tong")
        df_kpi = pd.read_excel(file_kpi_tong, skiprows=2)
        kpi_headers = df_kpi.columns.tolist()
        kpi_values = df_kpi.fillna("").values.tolist()
        all_kpi_rows = [kpi_headers] + kpi_values

        ws_kpi.batch_clear(["A1:Z200"])
        ws_kpi.update(values=all_kpi_rows, range_name="A1", value_input_option="USER_ENTERED")
        update_status(f"🎉 Cập nhật thành công 'KPI tong': {len(kpi_values)} dòng dữ liệu!", "#2ecc71")

        # Cập nhật thời gian Power BI vào ô P1
        if update_time_val:
            try:
                ws_kpi.update(values=[[f"Cập nhật PBI: {update_time_val}"]], range_name="P1")
            except Exception:
                pass
            # Cập nhật thêm tab tonghop!P1 nếu có (để công thức F2 ở KPI RUT GON v3 vẫn tự chạy)
            try:
                ws_th = sh_kpi.worksheet("tonghop")
                ws_th.update(values=[[f"Cập nhật PBI: {update_time_val}"]], range_name="P1")
            except Exception:
                pass

    # 2. Cập nhật sheet HS ca truc
    if file_hs_ca_truc and os.path.exists(file_hs_ca_truc):
        update_status("📄 Đang cập nhật bảng 'HS ca truc' lên Google Sheet...", "#3498db")
        sh_hs, ws_hs = get_worksheet_by_url(sheet_hs_url, "HS ca truc")
        
        wb = openpyxl.load_workbook(file_hs_ca_truc)
        ws_excel = wb.active
        rows_excel = list(ws_excel.iter_rows(values_only=True))
        
        # Row 1 là header cột: ['user_name', 'Giờ làm việc', ...]
        # Row 2+ là data
        hs_header = list(rows_excel[1])
        hs_data = []
        for r in rows_excel[2:]:
            u_name = str(r[0] or '').strip()
            if not u_name or 'applied filters' in u_name.lower():
                continue
            hs_data.append([val if val is not None else "" for val in r])

        all_hs_rows = [hs_header] + hs_data
        ws_hs.batch_clear(["A1:AZ300"])
        ws_hs.update(values=all_hs_rows, range_name="A1", value_input_option="USER_ENTERED")
        update_status(f"🎉 Cập nhật thành công 'HS ca truc': {len(hs_data)} nhân viên!", "#2ecc71")

# ==================== LUỒNG XỬ LÝ CHÍNH ====================
def _process_thread(pbi_url, sheet_kpi_tong, sheet_hs_ca_truc, is_headless=True):
    driver = None
    try:
        temp_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "powerbi_auto_downloads")
        os.makedirs(temp_dir, exist_ok=True)

        update_status("🚀 Khởi động trình duyệt Chrome...", "#3498db")
        options = webdriver.ChromeOptions()
        if is_headless:
            update_status("⚙️ Chrome chạy ở chế độ ẨN (Headless)...", "#3498db")
            options.add_argument("--headless=new")
        else:
            update_status("⚙️ Chrome chạy ở chế độ HIỂN THỊ CỬA SỔ...", "#3498db")

        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA"), CHROME_PROFILE_NAME)
        options.add_argument(f"user-data-dir={user_data_dir}")
        options.add_argument("profile-directory=Default")
        options.add_experimental_option("prefs", {
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        driver = webdriver.Chrome(options=options)
        if is_headless:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": temp_dir
            })

        update_status("🌐 Đang kết nối tới Power BI...", "#3498db")
        driver.get(pbi_url)
        time.sleep(15)

        # Xử lý đăng nhập Microsoft nếu xuất hiện
        handle_microsoft_login(driver)
        time.sleep(5)

        # Lấy thời gian cập nhật Power BI từ popup Info-bar ("Data updated")
        update_time_val = None
        try:
            driver.switch_to.default_content()
            info_btns = driver.find_elements(By.CSS_SELECTOR, "button.info-bar")
            if info_btns:
                driver.execute_script("arguments[0].click();", info_btns[0])
                time.sleep(1.5)
                labels = driver.find_elements(By.XPATH, "//b[contains(text(), 'Data updated') or contains(text(), 'Cập nhật')]/following::label[1]")
                for lbl in labels:
                    txt = lbl.text.strip()
                    if txt:
                        update_time_val = txt
                        break
                try:
                    driver.execute_script("arguments[0].click();", info_btns[0])
                except Exception:
                    pass

            if update_time_val:
                # Chuẩn hóa ví dụ "13:24 14/11/26" -> "13:24 - 14/11/2026"
                parts = update_time_val.split()
                if len(parts) == 2:
                    t_part, d_part = parts[0], parts[1]
                    d_sub = d_part.split('/')
                    if len(d_sub) == 3 and len(d_sub[2]) == 2:
                        d_part = f"{d_sub[0]}/{d_sub[1]}/20{d_sub[2]}"
                    update_time_val = f"{t_part} - {d_part}"
                update_status(f"📅 Thời gian Data updated Power BI: {update_time_val}", "#2ecc71")
            else:
                update_time_val = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
                update_status(f"⚠️ Không đọc được popup, dùng giờ hiện tại: {update_time_val}", "#f39c12")
        except Exception as e_time:
            update_time_val = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
            update_status(f"⚠️ Lưu ý đọc thời gian Power BI: {e_time}", "#f39c12")

        # Chuyển vào iframe báo cáo
        update_status("📦 Đang chuyển vùng vào Iframe báo cáo...", "#3498db")
        if not switch_to_correct_iframe(driver):
            raise Exception("Không thể chuyển vào iframe báo cáo. Vui lòng kiểm tra lại kết nối mạng hoặc link báo cáo.")

        # Xử lý các bộ lọc: Reset các bộ lọc khác về All, lọc Team CTO 1
        update_status("🧹 Đang thiết lập các bộ lọc chuẩn...", "#3498db")
        slicers_to_all = ["Line", "Level", "Nhân viên", "Ca trực", "Kênh trực", "Tạo bởi AI ?", "Chuyển lead FB", "Hỗ trợ HDDT - CKS", "Số ticket kênh Ticket"]
        for s in slicers_to_all:
            filter_slicer_to_value(driver, s, "All")

        filter_slicer_to_value(driver, "Team", "Team CTO 1")
        time.sleep(3)

        # Định vị 2 bảng trên báo cáo
        visuals = driver.find_elements(By.CSS_SELECTOR, "visual-container, .visual-container, .visual-container-component")
        vis_kpi_tong = None
        vis_hs_ca_truc = None

        for vis in visuals:
            txt = vis.text
            if "smownerid_name" in txt and "%KPI tổng" in txt and not vis_kpi_tong:
                vis_kpi_tong = vis
            if "Ca trực" in txt and "user_name" in txt and "Giờ làm việc" in txt and not vis_hs_ca_truc:
                vis_hs_ca_truc = vis

        if not vis_kpi_tong:
            raise Exception("Không tìm thấy bảng dữ liệu 'KPI tong' trên báo cáo!")
        if not vis_hs_ca_truc:
            raise Exception("Không tìm thấy bảng dữ liệu 'HS ca truc' trên báo cáo!")

        # 1. Xuất bảng KPI tong
        update_status("--------------------------------------------------", "#9b59b6")
        update_status("🚀 BẮT ĐẦU XUẤT BẢNG 1/2: KPI TỔNG HỢP", "#9b59b6")
        file_kpi = export_visual(driver, vis_kpi_tong, temp_dir, "KPI_TONG", export_mode="summarized")
        switch_to_correct_iframe(driver)

        # 2. Xuất bảng HS ca truc
        update_status("--------------------------------------------------", "#2ecc71")
        update_status("🚀 BẮT ĐẦU XUẤT BẢNG 2/2: HIỆU SUẤT CA TRỰC", "#2ecc71")
        file_hs = export_visual(driver, vis_hs_ca_truc, temp_dir, "HS_CA_TRUC", export_mode="layout")

        # Tắt driver giải phóng Chrome
        if driver:
            try: driver.quit()
            except Exception: pass
            driver = None

        # 3. Đồng bộ lên Google Sheets
        update_status("--------------------------------------------------", "#ffffff")
        sync_data_to_google_sheet(file_kpi, file_hs, sheet_kpi_tong, sheet_hs_ca_truc, update_time_val)

        # 4. Tự động cập nhật Website Dashboard HTML & JSON
        try:
            update_status("🌐 Đang tự động cập nhật Website Dashboard xem KPI...", "#3498db")
            import build_dashboard
            build_dashboard.generate_dashboard(update_time_val)
            update_status("✅ Đã cập nhật xong giao diện Website Dashboard!", "#2ecc71")
        except Exception as e_dash:
            update_status(f"⚠️ Lưu ý cập nhật dashboard: {e_dash}", "#f39c12")

        # 5. Tự động đồng bộ lên GitHub Pages
        try:
            update_status("🐙 Đang tự động đẩy dữ liệu lên GitHub...", "#3498db")
            cwd = os.path.dirname(os.path.abspath(__file__))
            subprocess.run(["git", "add", "index.html", "kpi_dashboard.html", "kpi_data.json", "PowerBI_Export_KPI_TONG.xlsx", "PowerBI_Export_HS_CA_TRUC.xlsx"], cwd=cwd)
            subprocess.run(["git", "commit", "-m", f"Auto update KPI data {update_time_val}"], cwd=cwd)
            subprocess.run(["git", "push", "origin", "main"], cwd=cwd)
            update_status("✅ Đã đồng bộ lên GitHub Pages thành công!", "#2ecc71")
        except Exception as e_git:
            update_status(f"⚠️ Lưu ý sync git: {e_git}", "#f39c12")

        update_status("✨ HOÀN THÀNH TẤT CẢ CÁC BƯỚC TỰ ĐỘNG 100%! ✨", "#00b894")
        if IS_GUI_MODE and 'btn_run' in globals() and btn_run:
            btn_run.config(state=tk.NORMAL, text="▶ Chạy tự động Power BI")
            btn_chrome.config(state=tk.NORMAL)

    except Exception as e:
        update_status(f"❌ Lỗi tiến trình: {e}", "#ef4444")
        if driver:
            try: driver.quit()
            except Exception: pass
        if IS_GUI_MODE and 'btn_run' in globals() and btn_run:
            btn_run.config(state=tk.NORMAL, text="▶ Chạy tự động Power BI")
            btn_chrome.config(state=tk.NORMAL)
            messagebox.showerror("Thông báo lỗi", f"Đã xảy ra lỗi:\n{e}")
        if not IS_GUI_MODE:
            sys.exit(1)

def start_powerbi_process():
    btn_run.config(state=tk.DISABLED, text="Đang chạy...")
    btn_chrome.config(state=tk.DISABLED)

    pbi_url = entry_url.get().strip()
    sheet_kpi_tong = entry_sheet_kpi.get().strip()
    sheet_hs_ca_truc = entry_sheet_hs.get().strip()
    save_config(pbi_url, sheet_kpi_tong, sheet_hs_ca_truc)

    is_headless = var_headless.get()
    threading.Thread(target=_process_thread, args=(pbi_url, sheet_kpi_tong, sheet_hs_ca_truc, is_headless), daemon=True).start()

def open_manual_chrome():
    update_status("🌐 Đang mở Chrome để bạn kiểm tra / đăng nhập thủ công...", "#f39c12")
    user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA"), CHROME_PROFILE_NAME)
    config = load_config()
    pbi_url = config.get("pbi_url", DEFAULT_POWERBI_URL)
    cmd = f'start chrome "{pbi_url}" --user-data-dir="{user_data_dir}" --profile-directory="Default"'
    subprocess.Popen(cmd, shell=True)

# ==================== CLI MODE (SCHEDULED) ====================
def run_cli_mode():
    global IS_GUI_MODE
    IS_GUI_MODE = False
    update_status("=== KHỞI CHẠY CHẾ ĐỘ TỰ ĐỘNG (CLI MODE) ===")
    config = load_config()
    pbi_url = config.get("pbi_url", DEFAULT_POWERBI_URL)
    sheet_kpi_tong = config.get("sheet_kpi_tong", DEFAULT_SHEET_KPI_TONG)
    sheet_hs_ca_truc = config.get("sheet_hs_ca_truc", DEFAULT_SHEET_HS_CA_TRUC)

    _process_thread(pbi_url, sheet_kpi_tong, sheet_hs_ca_truc, is_headless=True)
    update_status("🎉 HOÀN THÀNH TỰ ĐỘNG!")
    sys.exit(0)

# ==================== GUI MODE ====================
def run_gui_mode():
    global root, entry_url, entry_sheet_kpi, entry_sheet_hs, btn_run, btn_chrome, txt_status, var_headless

    root = tk.Tk()
    root.title("Auto Power BI Export to Excel & Google Sheets")
    root.geometry("750x750")
    root.configure(bg="#1e1e24")
    root.resizable(False, False)

    config = load_config()
    pbi_url_val = config.get("pbi_url", DEFAULT_POWERBI_URL)
    sheet_kpi_val = config.get("sheet_kpi_tong", DEFAULT_SHEET_KPI_TONG)
    sheet_hs_val = config.get("sheet_hs_ca_truc", DEFAULT_SHEET_HS_CA_TRUC)

    lbl_title = tk.Label(root, text="BỘ TỰ ĐỘNG XUẤT POWER BI (TEAM CTO 1)", font=("Arial", 16, "bold"), fg="#6c5ce7", bg="#1e1e24")
    lbl_title.pack(pady=(15, 10))

    frame_config = tk.Frame(root, bg="#2a2b36", bd=1, relief=tk.FLAT)
    frame_config.pack(padx=20, pady=10, fill=tk.X)

    tk.Label(frame_config, text="Đường dẫn báo cáo Power BI:", font=("Arial", 10, "bold"), fg="#f5f6fa", bg="#2a2b36").pack(anchor=tk.W, padx=15, pady=(8, 2))
    entry_url = tk.Entry(frame_config, width=80, font=("Consolas", 10), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief=tk.FLAT)
    entry_url.insert(0, pbi_url_val)
    entry_url.pack(padx=15, pady=(0, 8), fill=tk.X)

    tk.Label(frame_config, text="Google Sheet: Tab 'KPI tong':", font=("Arial", 10, "bold"), fg="#f5f6fa", bg="#2a2b36").pack(anchor=tk.W, padx=15, pady=(4, 2))
    entry_sheet_kpi = tk.Entry(frame_config, width=80, font=("Consolas", 10), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief=tk.FLAT)
    entry_sheet_kpi.insert(0, sheet_kpi_val)
    entry_sheet_kpi.pack(padx=15, pady=(0, 8), fill=tk.X)

    tk.Label(frame_config, text="Google Sheet: Tab 'HS ca truc':", font=("Arial", 10, "bold"), fg="#f5f6fa", bg="#2a2b36").pack(anchor=tk.W, padx=15, pady=(4, 2))
    entry_sheet_hs = tk.Entry(frame_config, width=80, font=("Consolas", 10), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief=tk.FLAT)
    entry_sheet_hs.insert(0, sheet_hs_val)
    entry_sheet_hs.pack(padx=15, pady=(0, 8), fill=tk.X)

    var_headless = tk.BooleanVar(value=True)
    chk_headless = tk.Checkbutton(frame_config, text="Chạy ẩn trình duyệt Chrome (Headless mode)", variable=var_headless,
                                  font=("Arial", 10), fg="#f5f6fa", bg="#2a2b36", selectcolor="#1e1e24", activebackground="#2a2b36", activeforeground="#f5f6fa")
    chk_headless.pack(anchor=tk.W, padx=15, pady=(0, 10))

    btn_frame = tk.Frame(root, bg="#1e1e24")
    btn_frame.pack(pady=5)

    btn_run = tk.Button(btn_frame, text="▶ Chạy tự động Power BI", command=start_powerbi_process,
                        bg="#6c5ce7", fg="white", font=("Arial", 11, "bold"), width=25, height=2, bd=0, activebackground="#5b4bc4", activeforeground="white")
    btn_run.pack(side=tk.LEFT, padx=10)

    def sync_sheets_and_web():
        btn_sync.config(state=tk.DISABLED, text="Đang đồng bộ...")
        def _th():
            try:
                update_status("📡 Đang đồng bộ số liệu từ Google Sheets lên Web...", "#3498db")
                import sync_sheets_to_web
                sync_sheets_to_web.sync_sheets_to_dashboard(push_github=True)
                update_status("🎉 Đã đồng bộ số liệu mới nhất từ Google Sheets lên Web thành công!", "#00b894")
            except Exception as e:
                update_status(f"❌ Lỗi đồng bộ Google Sheets: {e}", "#ef4444")
            finally:
                root.after(0, lambda: btn_sync.config(state=tk.NORMAL, text="🔄 Đồng bộ từ GG Sheet"))
        threading.Thread(target=_th, daemon=True).start()

    btn_sync = tk.Button(btn_frame, text="🔄 Đồng bộ từ GG Sheet", command=sync_sheets_and_web,
                         bg="#10b981", fg="white", font=("Arial", 10, "bold"), height=2, bd=0, activebackground="#059669", activeforeground="white")
    btn_sync.pack(side=tk.LEFT, padx=8)

    btn_chrome = tk.Button(btn_frame, text="Mở Chrome Login", command=open_manual_chrome,
                           bg="#f39c12", fg="white", font=("Arial", 10), height=2, bd=0, activebackground="#e67e22", activeforeground="white")
    btn_chrome.pack(side=tk.LEFT, padx=8)

    def open_web_dashboard():
        dash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpi_dashboard.html")
        if os.path.exists(dash_path):
            import webbrowser
            webbrowser.open(dash_path)
            update_status("🌐 Đã mở Website KPI Dashboard trên trình duyệt!", "#2ecc71")
        else:
            update_status("⚠️ Chưa tìm thấy file kpi_dashboard.html, vui lòng chạy xuất dữ liệu trước.", "#f1c40f")

    btn_web = tk.Button(btn_frame, text="🌐 Mở Website KPI", command=open_web_dashboard,
                        bg="#0984e3", fg="white", font=("Arial", 10, "bold"), height=2, bd=0, activebackground="#74b9ff", activeforeground="white")
    btn_web.pack(side=tk.LEFT, padx=8)

    log_frame = tk.Frame(root, bg="#2a2b36", bd=1, relief=tk.FLAT)
    log_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

    scrollbar = tk.Scrollbar(log_frame, bg="#2a2b36")
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    txt_status = tk.Text(log_frame, height=12, font=("Consolas", 10), yscrollcommand=scrollbar.set, bg="#1e1e24", fg="#ffffff", state=tk.DISABLED, bd=0, highlightthickness=0)
    txt_status.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    scrollbar.config(command=txt_status.yview)

    update_status("▶ Hệ thống sẵn sàng hoạt động!", "#00b894")
    update_status("💡 Lưu ý: Vui lòng đóng tất cả các tab Chrome trước khi chạy tự động.", "#f1c40f")

    root.mainloop()

if __name__ == "__main__":
    if "--auto" in sys.argv:
        run_cli_mode()
    else:
        run_gui_mode()
