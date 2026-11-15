import os, json, datetime, calendar
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
CACHE_FILE = os.path.join(SCRIPT_DIR, "Data", "schedule_cache.json")
SPREADSHEET_SCHEDULE_URL = "https://docs.google.com/spreadsheets/d/1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo/edit"

TARGET_IDS = ["8239", "8131", "8171", "8116", "8177", "8222", "8257", "8274", "8284", "8285", "8817", "8818", "8805", "8607"]

def get_schedule_data():
    """
    Tải và tính toán dữ liệu lịch trực & chấm công cho Team Ông Minh Nhựt (CTO 1).
    Ưu tiên tải mới từ Google Sheets; nếu lỗi/offline thì tải từ Cache.
    """
    data = None
    if os.path.exists(CREDENTIALS_FILE):
        try:
            data = _fetch_from_sheets()
        except Exception as e:
            print(f"Warning fetching live schedule: {e}")

    if not data and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Loaded schedule from cache: {CACHE_FILE}")
        except Exception as e:
            print(f"Warning reading schedule cache: {e}")

    return data

def _fetch_from_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    ss = client.open_by_url(SPREADSHEET_SCHEDULE_URL)

    today = datetime.date.today()
    m_curr = today.month
    y_curr = today.year
    m_next = m_curr + 1 if m_curr < 12 else 1
    y_next = y_curr if m_curr < 12 else y_curr + 1
    m_prev = m_curr - 1 if m_curr > 1 else 12
    y_prev = y_curr if m_curr > 1 else y_curr - 1

    sheet_curr_name = f"Tháng {m_curr:02d}/{y_curr}"
    sheet_next_name = f"Tháng {m_next:02d}/{y_next}"

    # Chu kỳ A: 26 tháng trước đến 25 tháng này (hoặc 26 này đến 25 sau nếu hôm nay >= 26)
    if today.day < 26:
        cycle_a_start = datetime.date(y_prev, m_prev, 26)
        cycle_a_end = datetime.date(y_curr, m_curr, 25)
    else:
        cycle_a_start = datetime.date(y_curr, m_curr, 26)
        cycle_a_end = datetime.date(y_next, m_next, 25)

    # Chu kỳ B: 01 đến ngày cuối tháng của tháng hiện tại
    cycle_b_start = datetime.date(y_curr, m_curr, 1)
    last_d = calendar.monthrange(y_curr, m_curr)[1]
    cycle_b_end = datetime.date(y_curr, m_curr, last_d)

    def parse_sheet_data(ws, m, y):
        rows = ws.get_all_values()
        ngay_row_idx = None
        ca_row_idx = None
        thu_row_idx = None
        for idx, r in enumerate(rows[:12]):
            txt = ' '.join(r).lower()
            if 'thứ' in txt or 'cn' in txt:
                if thu_row_idx is None:
                    thu_row_idx = idx
            s_count = sum(1 for c in r if c.strip() in ['S', 'TR', 'T', 'HC-S', 'HC-C'])
            if s_count >= 5 and ca_row_idx is None:
                ca_row_idx = idx

        if ca_row_idx is not None:
            ngay_row_idx = ca_row_idx - 1
            if thu_row_idx is None:
                thu_row_idx = ca_row_idx - 2
        else:
            thu_row_idx, ngay_row_idx, ca_row_idx = 2, 3, 4

        thu_row = rows[thu_row_idx] if thu_row_idx < len(rows) else []
        ngay_row = rows[ngay_row_idx] if ngay_row_idx < len(rows) else []
        ca_row = rows[ca_row_idx] if ca_row_idx < len(rows) else []

        end_col = len(ca_row)
        for i in range(4, len(ca_row)):
            ca_name = (ca_row[i] or (ngay_row[i] if i < len(ngay_row) else '')).strip().lower()
            if 'tổng' in ca_name or 'tong' in ca_name:
                end_col = i
                break

        col_to_date = {}
        curr_day = ""
        curr_thu = ""
        for i in range(4, end_col):
            if i < len(thu_row) and thu_row[i].strip():
                curr_thu = thu_row[i].strip()
            if i < len(ngay_row) and ngay_row[i].strip():
                curr_day = ngay_row[i].strip()
            if not curr_day:
                continue
            try:
                day_num = int(curr_day)
            except ValueError:
                continue

            dm = m - 1 if day_num >= 26 else m
            dy = y if (m > 1 or day_num < 26) else y - 1
            if dm == 0:
                dm = 12

            try:
                dt_obj = datetime.date(dy, dm, day_num)
                col_to_date[i] = {
                    'date': dt_obj,
                    'thu': curr_thu,
                    'ca': ca_row[i].strip() if i < len(ca_row) else ''
                }
            except:
                pass

        emp_schedules = {}
        start_emp_row = (ca_row_idx + 1) if ca_row_idx is not None else 5
        for r_idx in range(start_emp_row, len(rows)):
            row = rows[r_idx]
            if len(row) <= 3:
                continue
            emp_id = row[2].strip()
            emp_name = row[3].strip()

            if not emp_id or emp_id not in TARGET_IDS:
                continue

            if emp_id not in emp_schedules:
                emp_schedules[emp_id] = {
                    'name': emp_name,
                    'shifts': {}
                }

            for col_idx, col_info in col_to_date.items():
                val = row[col_idx].strip() if col_idx < len(row) else ''
                d_str = col_info['date'].strftime('%Y-%m-%d')
                if d_str not in emp_schedules[emp_id]['shifts']:
                    emp_schedules[emp_id]['shifts'][d_str] = []
                if val:
                    emp_schedules[emp_id]['shifts'][d_str].append({
                        'ca': col_info['ca'],
                        'val': val
                    })

        return emp_schedules, col_to_date

    # Load current month
    ws_curr = ss.worksheet(sheet_curr_name)
    sched_curr, col_to_date_curr = parse_sheet_data(ws_curr, m_curr, y_curr)

    # Next month if exists
    sched_next = {}
    try:
        ws_next = ss.worksheet(sheet_next_name)
        sched_next, _ = parse_sheet_data(ws_next, m_next, y_next)
    except Exception:
        pass

    # Merge employee shifts
    all_employees = {}
    for eid, info in sched_curr.items():
        if eid not in all_employees:
            all_employees[eid] = {'id': eid, 'name': info['name'], 'shifts': {}}
        for d, s in info['shifts'].items():
            all_employees[eid]['shifts'][d] = s

    for eid, info in sched_next.items():
        if eid not in all_employees:
            all_employees[eid] = {'id': eid, 'name': info['name'], 'shifts': {}}
        for d, s in info['shifts'].items():
            all_employees[eid]['shifts'][d] = s

    # Tính toán chuẩn hóa công (Bất biến <= 1.0 công / ngày)
    def calc_stats(shifts_dict, start_d, end_d, limit_d=None):
        tot_off = 0.0
        tot_p = 0.0
        tot_work = 0.0
        curr = start_d
        lim = min(end_d, limit_d) if limit_d else end_d
        days_ct = 0

        while curr <= lim:
            d_str = curr.strftime('%Y-%m-%d')
            s_list = shifts_dict.get(d_str, [])
            if s_list:
                days_ct += 1
                off_val = 0.0
                p_val = 0.0
                has_active = False

                for item in s_list:
                    v = item.get('val', '').upper().strip()
                    if v == "OFF":
                        off_val += 1.0
                    elif v == "OFF/2":
                        off_val += 0.5
                    elif v == "P":
                        p_val += 1.0
                    elif v == "P/2":
                        p_val += 0.5
                    elif v != "":
                        has_active = True

                d_off = min(1.0, off_val)
                d_p = min(1.0 - d_off, p_val)
                d_work = (1.0 - d_off - d_p) if has_active else 0.0

                tot_off += d_off
                tot_p += d_p
                tot_work += d_work
            curr += datetime.timedelta(days=1)

        return {
            'off': tot_off,
            'p': tot_p,
            'work': tot_work,
            'total': tot_off + tot_p + tot_work,
            'days_counted': days_ct
        }

    min_date = min(cycle_a_start, cycle_b_start)
    max_date = max(cycle_a_end, cycle_b_end)

    thu_names_vi = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
    dates_list = []
    c_d = min_date
    while c_d <= max_date:
        d_str = c_d.strftime('%Y-%m-%d')
        thu_idx = c_d.weekday()
        dates_list.append({
            'date_str': d_str,
            'day_num': c_d.day,
            'month': c_d.month,
            'year': c_d.year,
            'thu': thu_names_vi[thu_idx],
            'is_weekend': (thu_idx >= 5),
            'is_today': (c_d == today),
            'in_cycle_a': (cycle_a_start <= c_d <= cycle_a_end),
            'in_cycle_b': (cycle_b_start <= c_d <= cycle_b_end)
        })
        c_d += datetime.timedelta(days=1)

    emp_list = []
    ordered_ids = ['8239'] + [x for x in TARGET_IDS if x != '8239']
    for eid in ordered_ids:
        if eid in all_employees:
            e = all_employees[eid]
            shifts = e['shifts']
            stats_a_todate = calc_stats(shifts, cycle_a_start, cycle_a_end, today)
            stats_a_full = calc_stats(shifts, cycle_a_start, cycle_a_end, None)
            stats_b_todate = calc_stats(shifts, cycle_b_start, cycle_b_end, today)
            stats_b_full = calc_stats(shifts, cycle_b_start, cycle_b_end, None)

            display_shifts = {}
            for d_str, s_items in shifts.items():
                if not s_items:
                    display_shifts[d_str] = ""
                    continue
                vals = [f"{x['ca']}: {x['val']}" if x['ca'] and x['ca'] != x['val'] else x['val'] for x in s_items]
                display_shifts[d_str] = " | ".join(vals)

            emp_list.append({
                'id': eid,
                'name': e['name'],
                'is_leader': (eid == '8239'),
                'role': 'Leader' if eid == '8239' else 'Nhân viên CS',
                'shifts': e['shifts'],
                'display_shifts': display_shifts,
                'stats': {
                    'cycle_a': {
                        'to_date': stats_a_todate,
                        'full': stats_a_full,
                        'start_str': cycle_a_start.strftime('%d/%m/%Y'),
                        'end_str': cycle_a_end.strftime('%d/%m/%Y')
                    },
                    'cycle_b': {
                        'to_date': stats_b_todate,
                        'full': stats_b_full,
                        'start_str': cycle_b_start.strftime('%d/%m/%Y'),
                        'end_str': cycle_b_end.strftime('%d/%m/%Y')
                    }
                }
            })

    result = {
        'updated_at': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'today': today.strftime('%Y-%m-%d'),
        'today_display': today.strftime('%d/%m/%Y'),
        'spreadsheet_url': SPREADSHEET_SCHEDULE_URL,
        'cycles': {
            'a': {
                'title': 'Chu kỳ 26 - 25',
                'label': f"26/{cycle_a_start.month:02d} -> 25/{cycle_a_end.month:02d}/{cycle_a_end.year}",
                'start': cycle_a_start.strftime('%Y-%m-%d'),
                'end': cycle_a_end.strftime('%Y-%m-%d')
            },
            'b': {
                'title': 'Chu kỳ Đầu - Cuối tháng',
                'label': f"01/{cycle_b_start.month:02d} -> {cycle_b_end.day:02d}/{cycle_b_end.month:02d}/{cycle_b_end.year}",
                'start': cycle_b_start.strftime('%Y-%m-%d'),
                'end': cycle_b_end.strftime('%Y-%m-%d')
            }
        },
        'dates': dates_list,
        'employees': emp_list
    }

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result
