import os
import sys
import json
import shutil
import datetime
import calendar
import subprocess
import gspread
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "1Gp4UVa_6YyQHA9SZxts8ey9z_mwB3j-BEKx20fvPPfk"

def parse_val(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    v_str = str(v).replace('%', '').replace(',', '').strip()
    try:
        val = float(v_str)
        if '%' in str(v):
            return val / 100.0
        return val
    except Exception:
        return 0.0

def sync_sheets_to_dashboard(push_github=True):
    print("==================================================")
    print("📡 ĐANG ĐỌC DỮ LIỆU TRỰC TIẾP TỪ GOOGLE SHEETS...")
    print("==================================================")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Không tìm thấy file {CREDENTIALS_FILE}!")

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)

    # 1. Đọc sheet KPI tong
    print("📄 Đang đọc tab 'KPI tong'...")
    ws_kpi = sh.worksheet("KPI tong")
    vals_kpi = ws_kpi.get_all_values()
    if not vals_kpi or len(vals_kpi) < 2:
        raise ValueError("Sheet 'KPI tong' không có dữ liệu!")

    # Lấy update_time_val từ ô P1 nếu có
    update_time_val = None
    try:
        p1_val = ws_kpi.acell("P1").value
        if p1_val and "Cập nhật" in p1_val:
            update_time_val = p1_val.replace("Cập nhật PBI:", "").replace("Cập nhật:", "").strip()
    except Exception:
        pass

    if not update_time_val:
        update_time_val = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")

    header_kpi = [h.strip() for h in vals_kpi[0]]
    kpi_data = []
    for idx, r in enumerate(vals_kpi[1:]):
        row_dict = {}
        for i, val in enumerate(r):
            if i < len(header_kpi):
                row_dict[header_kpi[i]] = val

        raw_name = str(row_dict.get('smownerid_name', '')).strip()
        if not raw_name or 'applied filters' in raw_name.lower():
            continue

        short_name = raw_name
        parts = [p.strip() for p in raw_name.split('-')]
        if len(parts) >= 2:
            short_name = parts[1]

        kpi_data.append({
            'id': len(kpi_data) + 1,
            'ma': str(row_dict.get('Mã', '')).split('.')[0],
            'name': short_name,
            'full_name': raw_name,
            'team': str(row_dict.get('team', '')),
            'level': str(row_dict.get('Level', '')).split('.')[0],
            'kpi_ticket': parse_val(row_dict.get('KPI ticket', 0)),
            'slg_kh': parse_val(row_dict.get('Slg KH quy đổi', 0)),
            'pct_kpi_ticket': parse_val(row_dict.get('%KPI ticket', 0)),
            'kpi_cv': parse_val(row_dict.get('KPI CV', 0)),
            'slg_cv': parse_val(row_dict.get('SLg CV quy đổi', 0)),
            'pct_kpi_cv': parse_val(row_dict.get('%KPI CV', 0)),
            'no_ticket_2ht': int(parse_val(row_dict.get('No ticket 2HT', 0))),
            'pct_kpi_tong': parse_val(row_dict.get('%KPI tổng', 0)),
        })

    print(f"✅ Đã tải thành công {len(kpi_data)} nhân viên từ 'KPI tong'!")

    # 2. Đọc sheet HS ca truc
    print("📄 Đang đọc tab 'HS ca truc'...")
    ws_hs = sh.worksheet("HS ca truc")
    vals_hs = ws_hs.get_all_values()
    hs_data = []
    if vals_hs and len(vals_hs) >= 2:
        shift_map = [
            ('Khác', 1),
            ('S', 5),
            ('HCS', 9),
            ('TR', 13),
            ('HCC', 17),
            ('T', 21),
            ('Total', 25)
        ]
        for r in vals_hs[1:]:
            u_name = str(r[0] or '').strip()
            if not u_name or 'applied filters' in u_name.lower():
                continue
            shifts = {}
            for s_name, c_start in shift_map:
                shifts[s_name] = {
                    'hours': round(parse_val(r[c_start]), 2) if c_start < len(r) else 0.0,
                    'cv': round(parse_val(r[c_start+1]), 1) if c_start+1 < len(r) else 0.0,
                    'kh': round(parse_val(r[c_start+2]), 1) if c_start+2 < len(r) else 0.0,
                    'pct_kpi': round(parse_val(r[c_start+3]), 4) if c_start+3 < len(r) else 0.0
                }
            hs_data.append({
                'user_name': u_name,
                'shifts': shifts
            })
    print(f"✅ Đã tải thành công {len(hs_data)} nhân viên từ 'HS ca truc'!")

    # 3. Tạo Dashboard
    import build_dashboard
    # Override generate_dashboard with fresh Google Sheet data
    build_dashboard.generate_dashboard(update_time_val, custom_kpi_data=kpi_data, custom_hs_data=hs_data)

    # 4. Đẩy lên GitHub
    if push_github:
        print("🐙 Đang đồng bộ lên GitHub Pages...")
        cwd = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(["git", "add", "index.html", "kpi_dashboard.html", "kpi_data.json"], cwd=cwd)
        subprocess.run(["git", "commit", "-m", f"Sync from Google Sheets ({update_time_val})"], cwd=cwd)
        subprocess.run(["git", "push", "origin", "main"], cwd=cwd)
        print("🎉 ĐÃ ĐỒNG BỘ XONG LÊN GITHUB PAGES!")

if __name__ == "__main__":
    sync_sheets_to_dashboard(push_github=True)
