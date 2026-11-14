import time
import os
import sys
import hashlib
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sync_sheets_to_web import sync_sheets_to_dashboard, CREDENTIALS_FILE, SHEET_ID

print("==================================================")
print("👀 ĐANG THEO DÕI GOOGLE SHEETS ĐỂ UPDATE REALTIME...")
print("==================================================")
print("💡 Khi anh sửa số trên Google Sheet, bot sẽ tự động cập nhật lên web trong 5 giây!")
sys.stdout.flush()

def get_sheet_hash():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        ws_kpi = sh.worksheet("KPI tong")
        vals_kpi = ws_kpi.get_all_values()
        ws_hs = sh.worksheet("HS ca truc")
        vals_hs = ws_hs.get_all_values()
        content = json.dumps([vals_kpi, vals_hs], ensure_ascii=False)
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"⚠️ Lỗi đọc sheet: {e}")
        return None

last_hash = get_sheet_hash()
print(f"✅ Đã ghi nhận trạng thái ban đầu của Google Sheet.")
sys.stdout.flush()

while True:
    try:
        time.sleep(8)
        current_hash = get_sheet_hash()
        if current_hash and last_hash and current_hash != last_hash:
            print("\n🔔 PHÁT HIỆN SỐ LIỆU TRÊN GOOGLE SHEET THAY ĐỔI!")
            print("🚀 Đang tự động cập nhật lên Website GitHub Pages...")
            sys.stdout.flush()
            sync_sheets_to_dashboard(push_github=True)
            last_hash = current_hash
            print("✅ Đã cập nhật xong! Tiếp tục theo dõi...")
            sys.stdout.flush()
    except KeyboardInterrupt:
        break
    except Exception as e:
        time.sleep(5)
