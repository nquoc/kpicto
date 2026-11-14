import os
import re
import urllib.parse
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def retry_gspread_op(op_func, log_callback=None, max_attempts=3, delay=2):
    def update_log(msg, color="#ffffff"):
        if log_callback: log_callback(msg, color)
        else: print(msg)
        
    for attempt in range(1, max_attempts + 1):
        try:
            return op_func()
        except Exception as e:
            if attempt == max_attempts:
                raise e
            update_log(f"⚠️ Thử lại lần {attempt}/{max_attempts} do lỗi kết nối Google Sheets: {e}", "#f1c40f")
            time.sleep(delay)

def update_google_sheet_api(df, sheet_url, log_callback=None, update_time=None, update_time_cell=None):
    def update_log(msg, color="#ffffff"):
        if log_callback: log_callback(msg, color)
        else: print(msg)

    try:
        if not sheet_url or not sheet_url.strip() or 'docs.google.com' not in sheet_url:
            update_log("⚠️ Link Google Sheet không hợp lệ hoặc để trống.", "#e67e22")
            return False

        update_log("🔐 Đang xác thực với Google API...", "#3498db")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        credentials_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
        if not os.path.exists(credentials_file):
            raise FileNotFoundError("Không tìm thấy file credentials.json trong thư mục tool!")
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        update_log("📂 Đang mở Google Sheet...", "#3498db")
        spreadsheet = retry_gspread_op(lambda: client.open_by_url(sheet_url), log_callback)
        
        # Parse GID
        parsed_url = urllib.parse.urlparse(sheet_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        gid = query_params.get("gid", [None])[0]
        
        if not gid and parsed_url.fragment:
            fragment = parsed_url.fragment
            if "gid=" in fragment:
                match = re.search(r'gid=(\d+)', fragment)
                if match:
                    gid = match.group(1)

        worksheet = None
        if gid is not None:
            try:
                gid_int = int(gid)
                worksheets = retry_gspread_op(lambda: spreadsheet.worksheets(), log_callback)
                for ws in worksheets:
                    if ws.id == gid_int:
                        worksheet = ws
                        break
            except Exception as e:
                update_log(f"⚠️ Không thể khớp GID {gid}: {e}. Sẽ dùng sheet đầu tiên.", "#f1c40f")

        if not worksheet:
            worksheet = retry_gspread_op(lambda: spreadsheet.get_worksheet(0), log_callback)
            
        update_log(f"📄 Đang cập nhật Sheet: '{worksheet.title}'...", "#3498db")
        
        # Format DataFrame data (NaNs to empty string to prevent JSON serialization errors)
        df_clean = df.fillna("")
        
        # Clean Excel formulas like =TEXT("0","value") or ="value" from all cells
        def clean_formulas(val):
            if not isinstance(val, str):
                return val
            match = re.search(r'=TEXT\(\s*[^,]+\s*,\s*"([^"]+)"\)', val, re.IGNORECASE)
            if match:
                return match.group(1)
            match_simple = re.search(r'=\s*"([^"]+)"', val)
            if match_simple:
                return match_simple.group(1)
            return val

        if hasattr(df_clean, 'map'):
            df_clean = df_clean.map(clean_formulas)
        else:
            df_clean = df_clean.applymap(clean_formulas)

        # Convert numeric values to int/float for SUM support, excluding ID/text columns
        def should_keep_as_string(col_name):
            col_name_lower = str(col_name).lower()
            non_numeric_keywords = ['id', 'code', 'mã', 'nhân sự', 'người', 'time', 'ngày', 'giờ', 'tạo', 'check', 'sửa', 'công việc', 'địa điểm', 'mô tả']
            return any(kw in col_name_lower for kw in non_numeric_keywords)

        for col in df_clean.columns:
            if not should_keep_as_string(col):
                def try_number(val):
                    if val == "" or pd.isna(val):
                        return ""
                    try:
                        f_val = float(str(val).strip())
                        if f_val.is_integer():
                            return int(f_val)
                        return f_val
                    except ValueError:
                        return val
                df_clean[col] = df_clean[col].apply(try_number)

        # Convert all columns to strings/numbers to prevent serialization issues
        # For datetimes/timestamps, convert them to formatted strings
        for col in df_clean.columns:
            if pd.api.types.is_datetime64_any_dtype(df_clean[col]) or pd.api.types.is_datetime64tz_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            elif df_clean[col].dtype == object:
                df_clean[col] = df_clean[col].apply(lambda x: str(x) if x is not None else "")
                
        # Clear old data from A2 to the bottom, ONLY for the columns we write to
        end_col_num = len(df_clean.columns)
        end_col_letter = gspread.utils.rowcol_to_a1(1, end_col_num).replace("1", "")
        max_rows = max(10000, worksheet.row_count)
        clear_range = f"A2:{end_col_letter}{max_rows}"
        
        update_log(f"🧹 Đang xóa dữ liệu cũ trong vùng {clear_range}...", "#3498db")
        retry_gspread_op(lambda: worksheet.batch_clear([clear_range]), log_callback)
        
        data_to_write = df_clean.values.tolist()
        
        if len(data_to_write) > 0:
            update_log(f"⚡ Đang ghi {len(data_to_write)} dòng dữ liệu mới...", "#3498db")
            end_row = 1 + len(data_to_write)
            write_range = f"A2:{end_col_letter}{end_row}"
            
            retry_gspread_op(lambda: worksheet.update(write_range, data_to_write), log_callback)
        else:
            update_log("⚠️ Không có dữ liệu phát sinh (0 dòng). Đã làm sạch vùng dữ liệu cũ.", "#f1c40f")

        # Ghi thời gian cập nhật của Power BI nếu có
        if update_time:
            if not update_time_cell:
                next_col_num = max(end_col_num + 2, 16)
                update_time_cell = gspread.utils.rowcol_to_a1(1, next_col_num)
            update_log(f"📝 Đang ghi thời gian cập nhật Power BI vào ô {update_time_cell} (và P1)...", "#3498db")
            retry_gspread_op(lambda: worksheet.update(update_time_cell, [[f"Cập nhật PBI: {update_time}"]]), log_callback)
            if update_time_cell != 'P1':
                try:
                    retry_gspread_op(lambda: worksheet.update('P1', [[f"Cập nhật PBI: {update_time}"]]), log_callback)
                except: pass
            
        update_log("🎉 Đã dán dữ liệu thành công lên Google Sheet qua API!", "#2ecc71")
        return True
    except Exception as e:
        update_log(f"❌ Lỗi API Google Sheets: {e}", "#ef4444")
        raise e
