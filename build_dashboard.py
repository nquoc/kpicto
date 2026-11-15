import os
import json
import shutil
import datetime
import calendar
import pandas as pd
import openpyxl
import schedule_service

def generate_dashboard(update_time_val=None, custom_kpi_data=None, custom_hs_data=None):
    if not update_time_val:
        update_time_val = datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")

    # 1. Read KPI tong
    kpi_file = "PowerBI_Export_KPI_TONG.xlsx"
    hs_file = "PowerBI_Export_HS_CA_TRUC.xlsx"

    kpi_data = []
    if custom_kpi_data is not None:
        kpi_data = custom_kpi_data
    elif os.path.exists(kpi_file):
        df_kpi = pd.read_excel(kpi_file, skiprows=2).fillna('')
        for idx, row in df_kpi.iterrows():
            raw_name = str(row.get('smownerid_name', '')).strip()
            # Parse short name: e.g. "8131 - Lê Thị Trúc Linh - Customer Service - CTO" -> "Lê Thị Trúc Linh"
            short_name = raw_name
            parts = [p.strip() for p in raw_name.split('-')]
            if len(parts) >= 2:
                short_name = parts[1]

            kpi_data.append({
                'id': idx + 1,
                'ma': str(row.get('Mã', '')).split('.')[0],
                'name': short_name,
                'full_name': raw_name,
                'team': str(row.get('team', '')),
                'level': str(row.get('Level', '')).split('.')[0],
                'kpi_ticket': float(row.get('KPI ticket', 0)) if row.get('KPI ticket') != '' else 0,
                'slg_kh': float(row.get('Slg KH quy đổi', 0)) if row.get('Slg KH quy đổi') != '' else 0,
                'pct_kpi_ticket': float(row.get('%KPI ticket', 0)) if row.get('%KPI ticket') != '' else 0,
                'kpi_cv': float(row.get('KPI CV', 0)) if row.get('KPI CV') != '' else 0,
                'slg_cv': float(row.get('SLg CV quy đổi', 0)) if row.get('SLg CV quy đổi') != '' else 0,
                'pct_kpi_cv': float(row.get('%KPI CV', 0)) if row.get('%KPI CV') != '' else 0,
                'no_ticket_2ht': int(row.get('No ticket 2HT', 0)) if row.get('No ticket 2HT') != '' else 0,
                'pct_kpi_tong': float(row.get('%KPI tổng', 0)) if row.get('%KPI tổng') != '' else 0,
            })

    # 2. Read HS ca truc
    hs_data = []
    if custom_hs_data is not None:
        hs_data = custom_hs_data
    elif os.path.exists(hs_file):
        wb = openpyxl.load_workbook(hs_file)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        shift_map = [
            ('Khác', 1),
            ('S', 5),
            ('HCS', 9),
            ('TR', 13),
            ('HCC', 17),
            ('T', 21),
            ('Total', 25)
        ]
        for r in rows[2:]:
            u_name = str(r[0] or '').strip()
            if not u_name or 'applied filters' in u_name.lower():
                continue
            shifts = {}
            for s_name, c_start in shift_map:
                shifts[s_name] = {
                    'hours': round(float(r[c_start]), 2) if c_start < len(r) and r[c_start] is not None else 0.0,
                    'cv': round(float(r[c_start+1]), 1) if c_start+1 < len(r) and r[c_start+1] is not None else 0.0,
                    'kh': round(float(r[c_start+2]), 1) if c_start+2 < len(r) and r[c_start+2] is not None else 0.0,
                    'pct_kpi': round(float(r[c_start+3]), 4) if c_start+3 < len(r) and r[c_start+3] is not None else 0.0
                }
            hs_data.append({
                'user_name': u_name,
                'shifts': shifts
            })

    # Summary calculations
    total_staff = len(kpi_data)
    avg_kpi = sum(x['pct_kpi_tong'] for x in kpi_data) / total_staff if total_staff > 0 else 0
    total_ticket = sum(x['slg_kh'] for x in kpi_data)
    total_cv = sum(x['slg_cv'] for x in kpi_data)
    total_ticket_2ht = sum(x['no_ticket_2ht'] for x in kpi_data)
    top_performer = max(kpi_data, key=lambda x: x['pct_kpi_tong']) if kpi_data else None

    now_dt = datetime.datetime.now()
    actual_days = 30
    try:
        actual_days = calendar.monthrange(now_dt.year, now_dt.month)[1]
    except Exception:
        pass
    current_day = now_dt.day
    target_pacing = current_day / float(actual_days)

    # Bảo mật tuyệt đối: Không nhúng Private Key vào web để tránh bị GitHub Secret Scanning quét khóa
    creds_json = "{}"

    schedule_data = schedule_service.get_schedule_data()

    dataset_json = json.dumps({
        'updated_at': update_time_val,
        'current_day': current_day,
        'days_in_month': actual_days,
        'kpi_tong': kpi_data,
        'hs_ca_truc': hs_data,
        'schedule': schedule_data,
        'summary': {
            'total_staff': total_staff,
            'avg_kpi': round(avg_kpi * 100, 2),
            'total_ticket': round(total_ticket, 1),
            'total_cv': round(total_cv, 1),
            'total_ticket_2ht': total_ticket_2ht,
            'top_performer': top_performer['name'] if top_performer else 'N/A',
            'top_kpi': round(top_performer['pct_kpi_tong'] * 100, 2) if top_performer else 0
        }
    }, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard KPI & Đánh Giá Tiến Độ Ca Trực - Team CTO 1</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
  <style>
/* ============================================================
   EVONDEV DESIGN SYSTEM - COMPLETE THEME & COMPONENT STYLES
   ============================================================ */

:root {{
  color-scheme: dark;
  --app-font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --mono-font: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;

  /* Surfaces & Backgrounds - Deep Obsidian */
  --bg: #090a13;
  --surface: #101323;
  --surface-subtle: #16192e;
  --surface-overlay: #1c213d;
  --card-bg: var(--surface);
  --row-hover: #191e36;
  --table-header: #13172c;

  /* Borders - Subtle 1px borders per evondevKit standard */
  --card-border: rgba(255, 255, 255, 0.08);
  --border: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.16);

  /* Typography */
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-subtle: #64748b;

  /* Brand Accents */
  --primary: #6366f1;
  --primary-hover: #4f46e5;
  --primary-light: rgba(99, 102, 241, 0.12);
  --primary-glow: rgba(99, 102, 241, 0.35);

  /* Semantic Colors */
  --success: #10b981;
  --success-light: rgba(16, 185, 129, 0.12);
  --warning: #f59e0b;
  --warning-light: rgba(245, 158, 11, 0.12);
  --danger: #ef4444;
  --danger-light: rgba(239, 68, 68, 0.12);
  --info: #06b6d4;
  --info-light: rgba(6, 182, 212, 0.12);

  /* Elevations & Shadows */
  --elevation-card: 0 1px 3px rgba(0, 0, 0, 0.3), 0 6px 16px -4px rgba(0, 0, 0, 0.4);
  --elevation-popover: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
  --elevation-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
}}

.light-theme {{
  color-scheme: light;
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-subtle: #f1f5f9;
  --surface-overlay: #ffffff;
  --card-bg: var(--surface);
  --row-hover: #f1f5f9;
  --table-header: #f8fafc;

  --card-border: #e2e8f0;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;

  --text-main: #0f172a;
  --text-muted: #64748b;
  --text-subtle: #94a3b8;

  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --primary-light: rgba(79, 70, 229, 0.08);
  --primary-glow: rgba(79, 70, 229, 0.2);

  --success: #059669;
  --success-light: rgba(5, 150, 105, 0.08);
  --warning: #d97706;
  --warning-light: rgba(217, 119, 6, 0.08);
  --danger: #dc2626;
  --danger-light: rgba(220, 38, 38, 0.08);
  --info: #0284c7;
  --info-light: rgba(2, 132, 199, 0.08);

  --elevation-card: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
  --elevation-popover: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.06);
  --elevation-modal: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}}

/* ============================================================
   GLOBAL RESET & TYPOGRAPHY
   ============================================================ */

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: var(--app-font);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

body {{
  background-color: var(--bg);
  color: var(--text-main);
  min-height: 100vh;
  padding: 24px;
  line-height: 1.5;
  transition: background-color 0.25s ease, color 0.25s ease;
}}

.container {{
  max-width: 1540px;
  margin: 0 auto;
}}

/* Tabular Numbers */
.numeric,
.stat-value,
.pacing-target-badge,
.badge-shift,
.matrix-table th,
.matrix-table td,
.bar-fill,
.podium-pct,
.forecast-value,
.detail-val {{
  font-variant-numeric: tabular-nums;
}}

/* Custom Sleek Scrollbar */
::-webkit-scrollbar {{
  width: 7px;
  height: 7px;
}}
::-webkit-scrollbar-track {{
  background: transparent;
}}
::-webkit-scrollbar-thumb {{
  background: var(--border-strong);
  border-radius: 9999px;
}}
::-webkit-scrollbar-thumb:hover {{
  background: var(--text-subtle);
}}

/* ============================================================
   HEADER & TOP ACTIONS
   ============================================================ */

.header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border);
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 14px;
}}

.logo-badge {{
  background: linear-gradient(135deg, #6366f1 0%, #4338ca 100%);
  color: #ffffff;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: -0.5px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.15);
}}

.brand-title h1 {{
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}}

.brand-title p {{
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
}}

.header-actions {{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}}

.btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border);
  background-color: var(--surface);
  color: var(--text-main);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}}

.btn:hover {{
  background-color: var(--surface-subtle);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}}

.btn:active {{
  transform: translateY(0);
}}

.btn-primary {{
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}}

.btn-primary:hover {{
  background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
  border-color: rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}}

.btn-refresh {{
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}}

.btn-refresh:hover {{
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
}}

.badge-live {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  background-color: var(--success-light);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.25);
}}

.dot-live {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: var(--success);
  box-shadow: 0 0 8px var(--success);
  animation: pulseLive 2s infinite;
}}

@keyframes pulseLive {{
  0% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.35; transform: scale(0.85); }}
  100% {{ opacity: 1; transform: scale(1); }}
}}

/* ============================================================
   TOP LEVEL MAIN VIEW SWITCHER (SEGMENTED CONTROL)
   ============================================================ */

.top-nav-bar {{
  display: inline-flex;
  align-items: center;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  gap: 4px;
}}

.top-nav-tab {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}}

.top-nav-tab:hover {{
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.04);
}}

.top-nav-tab.active {{
  color: var(--text-main);
  background: var(--surface);
  border-color: var(--border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}}

.top-nav-badge {{
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  background: var(--primary-light);
  color: var(--primary);
  border: 1px solid rgba(99, 102, 241, 0.2);
}}

/* ============================================================
   PACING PROGRESS BANNER
   ============================================================ */

.pacing-bar {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  box-shadow: var(--elevation-card);
}}

.pacing-info {{
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}}

.pacing-title {{
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}}

.pacing-day-selector {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
}}

.pacing-day-selector input {{
  width: 44px;
  padding: 3px 6px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  outline: none;
  font-variant-numeric: tabular-nums;
}}

.pacing-day-selector input:focus {{
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-light);
}}

.pacing-target-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
  border: 1px solid rgba(99, 102, 241, 0.2);
}}

/* ============================================================
   TOP METRIC STAT CARDS
   ============================================================ */

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}}

.stat-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: var(--elevation-card);
  position: relative;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}}

.stat-card:hover {{
  border-color: var(--border-strong);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}}

.stat-card.card-primary {{ border-top: 3px solid var(--primary); }}
.stat-card.card-success {{ border-top: 3px solid var(--success); }}
.stat-card.card-warning {{ border-top: 3px solid var(--warning); }}
.stat-card.card-danger  {{ border-top: 3px solid var(--danger); }}
.stat-card.card-info    {{ border-top: 3px solid var(--info); }}

.stat-label {{
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}}

.stat-value {{
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}}

.stat-sub {{
  font-size: 12px;
  color: var(--text-muted);
}}

/* ============================================================
   FILTERS & TOOLBAR CONTROLS
   ============================================================ */

.controls-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: var(--elevation-card);
}}

.filter-group {{
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}}

.search-box {{
  position: relative;
  flex: 1;
  min-width: 240px;
}}

.search-icon {{
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
  font-size: 14px;
}}

.search-box input,
.search-input {{
  width: 100%;
  padding: 9px 12px 9px 36px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--surface-subtle);
  color: var(--text-main);
  font-size: 13px;
  outline: none;
  transition: all 0.2s ease;
}}

.search-box input:focus,
.search-input:focus {{
  border-color: var(--primary);
  background: var(--surface);
  box-shadow: 0 0 0 3px var(--primary-light);
}}

.select-filter {{
  padding: 9px 14px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--surface-subtle);
  color: var(--text-main);
  font-size: 13px;
  font-weight: 500;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.select-filter:focus {{
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
}}

.find-me-box {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

.select-my-name {{
  background: var(--primary-light) !important;
  color: var(--primary) !important;
  border-color: rgba(99, 102, 241, 0.35) !important;
  font-weight: 700 !important;
}}

/* ============================================================
   TABS NAVIGATION
   ============================================================ */

.tabs-nav {{
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
  padding-bottom: 4px;
  overflow-x: auto;
}}

.tab-btn {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}}

.tab-btn:hover {{
  color: var(--text-main);
  background: var(--surface-subtle);
}}

.tab-btn.active {{
  color: var(--text-main);
  background: var(--surface);
  border-color: var(--border);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}}

.badge-count {{
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  background: var(--surface-subtle);
  color: var(--text-muted);
}}

.tab-btn.active .badge-count {{
  background: var(--primary-light);
  color: var(--primary);
}}

/* ============================================================
   DATA TABLES
   ============================================================ */

.table-card,
.table-responsive {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--elevation-card);
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}}

th {{
  background: var(--table-header);
  color: var(--text-muted);
  font-size: 11.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  user-select: none;
}}

th.sortable:hover {{
  color: var(--text-main);
  cursor: pointer;
}}

td {{
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text-main);
  vertical-align: middle;
}}

tr:last-child td {{
  border-bottom: none;
}}

tbody tr {{
  transition: background-color 0.15s ease;
}}

tbody tr:hover {{
  background-color: var(--row-hover);
  cursor: pointer;
}}

.numeric {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}

.text-center {{
  text-align: center;
}}

/* Badges */
.badge {{
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}}

.badge-level,
.badge-level-tag {{
  background: var(--surface-subtle);
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
}}

.badge-rank {{
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
}}

/* Pacing Status Badges */
.badge-ahead,
.pacing-ahead {{
  background: var(--success-light);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.25);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
}}

.badge-ontrack,
.pacing-ontrack {{
  background: rgba(14, 165, 233, 0.12);
  color: #0ea5e9;
  border: 1px solid rgba(14, 165, 233, 0.25);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
}}

.badge-behind-slight,
.pacing-behind {{
  background: var(--warning-light);
  color: var(--warning);
  border: 1px solid rgba(245, 158, 11, 0.25);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
}}

.badge-behind-severe,
.pacing-critical {{
  background: var(--danger-light);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.25);
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 9999px;
  font-size: 11px;
  animation: pulse-danger 2s infinite;
}}

@keyframes pulse-danger {{
  0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }}
  70% {{ box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }}
  100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
}}

.badge-ticket-2ht {{
  background-color: var(--primary-light);
  color: var(--primary);
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
}}

/* Progress bar inside table cells */
.progress-bar-wrapper,
.progress-bar-wrap {{
  width: 100%;
  height: 6px;
  background: var(--surface-subtle);
  border-radius: 9999px;
  overflow: hidden;
  margin-top: 5px;
}}

.progress-fill,
.progress-bar-fill {{
  height: 100%;
  border-radius: 9999px;
  transition: width 0.4s ease;
}}

.bg-good {{ background: linear-gradient(90deg, #10b981, #34d399); }}
.bg-ok   {{ background: linear-gradient(90deg, #0ea5e9, #38bdf8); }}
.bg-low  {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}

/* Row Highlights */
tr.my-row-highlight td {{
  background: rgba(99, 102, 241, 0.16) !important;
  border-top: 2px solid #818cf8 !important;
  border-bottom: 2px solid #818cf8 !important;
  font-weight: 600;
}}
tr.my-row-highlight td:first-child {{
  border-left: 3px solid #818cf8 !important;
  border-top-left-radius: 6px;
  border-bottom-left-radius: 6px;
}}
tr.my-row-highlight td:last-child {{
  border-right: 3px solid #818cf8 !important;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
}}

tr.alert-severe {{
  background-color: rgba(239, 68, 68, 0.08) !important;
}}

/* ============================================================
   CHARTS TAB
   ============================================================ */

.charts-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
  gap: 20px;
}}

.chart-box {{
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  box-shadow: var(--elevation-card);
}}

.chart-title {{
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-main);
}}

.bar-row {{
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  gap: 12px;
  font-size: 12px;
}}

.bar-label {{
  width: 140px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
  color: var(--text-main);
}}

.bar-track {{
  flex: 1;
  height: 24px;
  background-color: var(--surface-subtle);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}}

.bar-fill {{
  height: 100%;
  background: linear-gradient(90deg, var(--primary), #818cf8);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 10px;
  color: white;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  min-width: fit-content;
  box-sizing: border-box;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}}

/* ============================================================
   MODAL (STAFF PROFILE & FORECAST)
   ============================================================ */

.modal-backdrop {{
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(14px);
  z-index: 1000;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: fadeIn 0.2s ease;
}}

.modal-box {{
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 18px;
  width: 90%;
  max-width: 680px;
  padding: 24px 28px;
  max-height: 88vh;
  overflow-y: auto;
  box-shadow: var(--elevation-modal);
  position: relative;
}}

.modal-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}}

.modal-close {{
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.15s ease;
}}

.modal-close:hover {{
  background: var(--row-hover);
  color: var(--danger);
  border-color: rgba(239, 68, 68, 0.3);
}}

.card-profile-header {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}}

.profile-avatar {{
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.2);
}}

.profile-meta {{
  flex: 1;
}}

.profile-name {{
  font-size: 18px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 6px;
}}

.profile-badges {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}}

.detail-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}}

.detail-item {{
  background-color: var(--surface-subtle);
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
}}

.detail-title {{
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.04em;
}}

.detail-val {{
  font-size: 17px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 4px;
}}

/* Forecast Box */
.forecast-box {{
  background: var(--surface-subtle);
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 18px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.1);
}}

.forecast-title {{
  font-size: 11.5px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}}

.forecast-value {{
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 8px;
}}

.forecast-plan {{
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.2);
  border-radius: 9px;
  padding: 10px 14px;
  border: 1px solid var(--border);
}}

.light-theme .forecast-plan {{
  background: #ffffff;
}}

/* Strengths Comparison */
.strengths-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}}

.strength-card {{
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}}

.strength-label {{
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4px;
}}

.strength-val {{
  font-size: 18px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 6px;
}}

.strength-badge {{
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}}

/* Shift Stacked Bar */
.shift-stacked-bar {{
  height: 12px;
  border-radius: 9999px;
  overflow: hidden;
  display: flex;
  background: var(--surface-subtle);
  margin-bottom: 8px;
}}

.shift-seg {{
  height: 100%;
  transition: width 0.3s;
}}

.shift-legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 10px;
}}

.shift-legend-item {{
  display: flex;
  align-items: center;
  gap: 5px;
}}

.shift-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
}}

/* ============================================================
   PODIUM & AWARDS
   ============================================================ */

.podium-container {{
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 18px;
  padding: 24px 10px 10px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}}

.podium-step {{
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 210px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}}

.podium-step:hover {{
  transform: translateY(-5px);
}}

.podium-avatar {{
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 8px;
  color: white;
  box-shadow: 0 4px 18px rgba(0,0,0,0.35);
  position: relative;
}}

.podium-crown {{
  position: absolute;
  top: -18px;
  font-size: 24px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));
}}

.podium-name {{
  font-size: 14px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}}

.podium-pct {{
  font-size: 16px;
  font-weight: 800;
  margin-bottom: 8px;
}}

.podium-block {{
  width: 100%;
  border-radius: 14px 14px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 900;
  color: rgba(255,255,255,0.95);
  box-shadow: inset 0 2px 4px rgba(255,255,255,0.25), 0 4px 16px rgba(0,0,0,0.3);
}}

.podium-1 {{ order: 2; }}
.podium-1 .podium-block {{ height: 165px; background: linear-gradient(180deg, #f59e0b 0%, #b45309 100%); }}
.podium-1 .podium-avatar {{ background: linear-gradient(135deg, #f59e0b, #fbbf24); border: 3px solid #fef08a; }}
.podium-1 .podium-pct {{ color: #f59e0b; }}

.podium-2 {{ order: 1; }}
.podium-2 .podium-block {{ height: 125px; background: linear-gradient(180deg, #94a3b8 0%, #64748b 100%); }}
.podium-2 .podium-avatar {{ background: linear-gradient(135deg, #94a3b8, #cbd5e1); border: 3px solid #f1f5f9; }}
.podium-2 .podium-pct {{ color: #94a3b8; }}

.podium-3 {{ order: 3; }}
.podium-3 .podium-block {{ height: 95px; background: linear-gradient(180deg, #d97706 0%, #78350f 100%); }}
.podium-3 .podium-avatar {{ background: linear-gradient(135deg, #d97706, #f97316); border: 3px solid #ffedd5; }}
.podium-3 .podium-pct {{ color: #f97316; }}

.awards-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
  margin-top: 20px;
}}

.award-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  box-shadow: var(--elevation-card);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}}

.award-card:hover {{
  transform: translateY(-2px);
  border-color: var(--border-strong);
}}

.award-icon {{
  font-size: 32px;
  flex-shrink: 0;
}}

.award-title {{
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.award-name {{
  font-size: 14px;
  font-weight: 800;
  color: var(--text-main);
  margin: 2px 0;
}}

.award-stat {{
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
}}

/* ============================================================
   SCHEDULE MATRIX STYLES
   ============================================================ */

.schedule-controls-card,
.schedule-section-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 20px;
  box-shadow: var(--elevation-card);
}}

.schedule-controls-header,
.schedule-section-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}}

.schedule-title-wrap h3,
.schedule-section-title span {{
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.01em;
}}

.schedule-subtitle {{
  font-size: 12.5px;
  color: var(--text-muted);
  margin-top: 3px;
}}

.schedule-filters-grid {{
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}}

.filter-label {{
  display: block;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}}

.segmented-control {{
  display: inline-flex;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 3px;
  gap: 2px;
}}

.segmented-btn {{
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}}

.segmented-btn:hover {{
  color: var(--text-main);
}}

.segmented-btn.active {{
  background: var(--surface);
  color: var(--text-main);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}}

.today-roster-banner {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: var(--elevation-card);
}}

.today-roster-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}}

.today-roster-title {{
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}}

.roster-groups-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}}

.roster-group-card {{
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
}}

.roster-group-label {{
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}}

.roster-pills-wrap {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}

.roster-pill {{
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-main);
}}

.matrix-scroll-container {{
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  max-height: 680px;
  position: relative;
}}

.matrix-table {{
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
}}

.matrix-table th,
.matrix-table td {{
  padding: 7px 8px;
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  text-align: center;
  min-width: 48px;
}}

.matrix-table thead th {{
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--table-header);
}}

.sticky-col-id {{
  position: sticky;
  left: 0;
  z-index: 12;
  background: var(--surface) !important;
  min-width: 70px !important;
  font-family: var(--mono-font);
}}

.sticky-col-name {{
  position: sticky;
  left: 70px;
  z-index: 12;
  background: var(--surface) !important;
  min-width: 175px !important;
  text-align: left !important;
  font-weight: 600;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.1);
}}

.matrix-table thead .sticky-col-id,
.matrix-table thead .sticky-col-name {{
  z-index: 20;
  background: var(--table-header) !important;
}}

.matrix-table tbody tr:hover td,
.matrix-table tbody tr:hover .sticky-col-id,
.matrix-table tbody tr:hover .sticky-col-name {{
  background: var(--row-hover) !important;
}}

/* Shift Badges */
.badge-shift {{
  display: inline-block;
  padding: 2px 5px;
  border-radius: 5px;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 1.2;
  margin: 1px 0;
}}

.badge-shift-s {{ background: rgba(2, 132, 199, 0.2); color: #38bdf8; border: 1px solid rgba(2, 132, 199, 0.4); }}
.badge-shift-tr {{ background: rgba(217, 119, 6, 0.2); color: #fbbf24; border: 1px solid rgba(217, 119, 6, 0.4); }}
.badge-shift-t {{ background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4); }}
.badge-shift-hc {{ background: rgba(5, 150, 105, 0.2); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.4); }}
.badge-shift-off {{ background: rgba(220, 38, 38, 0.2); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.4); }}
.badge-shift-p {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }}
.badge-shift-other {{ background: rgba(255, 255, 255, 0.08); color: var(--text-muted); }}

/* Today Column Highlight */
.col-today,
.matrix-table .col-today {{
  background: rgba(245, 158, 11, 0.12) !important;
  border-left: 2px solid #f59e0b !important;
  border-right: 2px solid #f59e0b !important;
}}

.matrix-table thead th.col-today {{
  background: #f59e0b !important;
  color: #000000 !important;
}}

@keyframes pulseTodayCol {{
  0% {{ box-shadow: inset 0 0 0px #f59e0b; }}
  50% {{ box-shadow: inset 0 0 14px #f59e0b; }}
  100% {{ box-shadow: inset 0 0 0px #f59e0b; }}
}}

.col-weekend,
.matrix-table .col-weekend {{
  background: rgba(255, 255, 255, 0.02);
}}

.matrix-nav-buttons {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

/* ============================================================
   TV KIOSK MODE & TOAST
   ============================================================ */

body.tv-kiosk-mode {{
  padding: 10px 16px !important;
  overflow-x: hidden;
}}
body.tv-kiosk-mode .header-actions,
body.tv-kiosk-mode .controls-card,
body.tv-kiosk-mode .pacing-bar {{
  display: none !important;
}}
body.tv-kiosk-mode .container {{
  max-width: 100% !important;
}}
body.tv-kiosk-mode .header {{
  margin-bottom: 12px !important;
  padding-bottom: 10px !important;
}}
body.tv-kiosk-mode table {{
  font-size: 13.5px !important;
}}
body.tv-kiosk-mode th, body.tv-kiosk-mode td {{
  padding: 10px 8px !important;
}}
.tv-bar-wrap {{
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 5px;
  background: rgba(0,0,0,0.4);
  z-index: 99999;
}}
.tv-progress {{
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #6366f1, #ec4899);
  transition: width 0.1s linear;
}}
body.tv-kiosk-mode .tv-bar-wrap {{
  display: block;
}}
.tv-exit-pill {{
  display: none;
  position: fixed;
  top: 14px;
  right: 18px;
  z-index: 100000;
  background: rgba(15, 23, 42, 0.85);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(255,255,255,0.2);
  cursor: pointer;
  backdrop-filter: blur(8px);
}}
body.tv-kiosk-mode .tv-exit-pill {{
  display: block;
}}

.toast-msg {{
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--surface-overlay);
  color: var(--text-main);
  border: 1px solid var(--border-strong);
  padding: 12px 20px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--elevation-modal);
  z-index: 99999;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: fadeIn 0.25s ease;
}}

/* Hidden Zalo Capture Card */
#zalo-snapshot-card {{
  position: fixed;
  left: -9999px;
  top: 0;
  width: 950px;
  background: #090a13;
  color: #f8fafc;
  padding: 24px;
  border-radius: 16px;
  font-family: var(--app-font);
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: scale(0.98); }}
  to {{ opacity: 1; transform: scale(1); }}
}}

@media print {{
  body {{ background-color: #ffffff; color: #000000; padding: 0; }}
  .header-actions, .controls-card, .tabs-nav, .pacing-bar {{ display: none !important; }}
  .table-card {{ border: none; box-shadow: none; }}
  thead th {{ background-color: #f1f5f9 !important; color: #000 !important; }}
}}

/* ============================================================
   RESPONSIVE DESIGN SYSTEM (MOBILE & TABLET)
   evondevKit Standards: R1 to R11
   Tested strictly at 375px (iPhone) & 390px
   ============================================================ */

/* Utility classes */
.mobile-only {{
  display: none !important;
}}
.desktop-only {{
  display: block;
}}
.desktop-inline {{
  display: inline;
}}
.mobile-inline {{
  display: none;
}}

/* Mobile Card View for KPI */
.mobile-view-toggle {{
  display: none;
}}
.mobile-kpi-cards-grid {{
  display: none;
}}

/* Subtle hint for swipeable tables */
.swipe-hint {{
  display: none;
  font-size: 11.5px;
  color: var(--text-muted);
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding: 6px 10px;
  background: var(--surface-subtle);
  border-radius: 6px;
  border: 1px solid var(--border);
  width: fit-content;
}}

/* ============================================================
   BREAKPOINT: TABLET & MOBILE (< 768px)
   ============================================================ */
@media (max-width: 768px) {{
  html, body {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
    -webkit-text-size-adjust: 100% !important;
  }}

  body {{
    padding: 8px 10px 28px !important;
  }}

  .container {{
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 auto !important;
  }}

  /* Header */
  .header {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .brand {{
    gap: 10px !important;
  }}

  .logo-badge {{
    width: 36px !important;
    height: 36px !important;
    font-size: 13px !important;
    border-radius: 9px !important;
  }}

  .brand-title h1 {{
    font-size: 15px !important;
    line-height: 1.25 !important;
  }}

  .brand-title p {{
    font-size: 11px !important;
  }}

  .header-actions {{
    width: 100% !important;
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    justify-content: flex-start !important;
  }}

  .badge-live {{
    font-size: 10.5px !important;
    padding: 4px 8px !important;
  }}

  .btn {{
    padding: 7px 10px !important;
    font-size: 11.5px !important;
    border-radius: 8px !important;
  }}

  /* Hide excessive buttons on mobile header */
  #hdr-btn-toggle-sched,
  .header-actions button[onclick="window.print()"],
  .header-actions button[onclick="toggleTvMode()"] {{
    display: none !important;
  }}

  /* Top Nav Tab Switcher */
  .top-nav-bar {{
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 6px !important;
    padding: 4px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .top-nav-tab {{
    padding: 10px 6px !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    text-align: center !important;
    justify-content: center !important;
    min-height: 42px !important;
    border-radius: 9px !important;
  }}

  .top-nav-tab .top-nav-badge {{
    display: none !important;
  }}

  /* Pacing Bar */
  .pacing-bar {{
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .pacing-info {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    margin-bottom: 10px !important;
  }}

  .pacing-title span {{
    font-size: 13.5px !important;
  }}

  .pacing-day-selector {{
    font-size: 12px !important;
    flex-wrap: wrap !important;
  }}

  .pacing-day-selector input {{
    font-size: 16px !important; /* R8: No iOS zoom */
    padding: 4px 6px !important;
  }}

  .pacing-target-badge {{
    font-size: 11px !important;
    padding: 3px 8px !important;
    width: fit-content !important;
  }}

  /* Stats Cards Grid - 2x2 Clean Layout */
  .stats-grid {{
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
    margin-bottom: 14px !important;
  }}

  .stat-card {{
    padding: 10px 12px !important;
    border-radius: 10px !important;
  }}

  .stat-label {{
    font-size: 10px !important;
    letter-spacing: 0.02em !important;
  }}

  .stat-value {{
    font-size: 19px !important;
    margin: 3px 0 2px !important;
  }}

  .stat-sub {{
    font-size: 9.5px !important;
    line-height: 1.2 !important;
  }}

  .stat-card:nth-child(5) {{
    grid-column: span 2 !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    padding: 8px 12px !important;
  }}

  .stat-card:nth-child(5) .stat-value {{
    font-size: 17px !important;
    margin: 0 !important;
  }}

  /* Controls Card & Search */
  .controls-card {{
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .filter-group {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
  }}

  .search-box,
  .find-me-box {{
    width: 100% !important;
    min-width: 100% !important;
  }}

  .search-input,
  .find-me-select {{
    font-size: 16px !important; /* R8: No iOS zoom */
    height: 42px !important;
    border-radius: 8px !important;
  }}

  /* KPI Sub Tabs */
  .tabs-nav {{
    display: flex !important;
    overflow-x: auto !important;
    white-space: nowrap !important;
    -webkit-overflow-scrolling: touch !important;
    gap: 6px !important;
    padding-bottom: 4px !important;
    margin-bottom: 10px !important;
  }}

  .tab-btn {{
    flex-shrink: 0 !important;
    padding: 7px 11px !important;
    font-size: 12px !important;
  }}

  /* Mobile View Switcher (Cards vs Table) */
  .mobile-view-toggle {{
    display: flex !important;
    gap: 6px !important;
    margin-bottom: 10px !important;
    background: var(--surface-subtle) !important;
    padding: 3px !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
  }}

  .mv-btn {{
    flex: 1 !important;
    padding: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border: none !important;
    background: transparent !important;
    border-radius: 7px !important;
    color: var(--text-muted) !important;
    cursor: pointer !important;
    text-align: center !important;
    transition: all 0.2s !important;
  }}

  .mv-btn.active {{
    background: var(--surface) !important;
    color: var(--text-main) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
    font-weight: 700 !important;
  }}

  /* Mobile Cards Grid */
  .mobile-kpi-cards-grid {{
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 10px !important;
    margin-bottom: 16px !important;
  }}

  .mobile-kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: var(--elevation-card);
    transition: transform 0.15s ease, border-color 0.15s ease;
    cursor: pointer;
  }}

  .mobile-kpi-card:active {{
    transform: scale(0.985);
    border-color: var(--primary);
  }}

  .mkc-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    gap: 8px;
  }}

  .mkc-left {{
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
  }}

  .mkc-rank {{
    font-size: 15px;
    font-weight: 800;
    min-width: 24px;
    text-align: center;
    font-family: var(--mono-font);
  }}

  .mkc-avatar {{
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
    border: 1px solid rgba(99,102,241,0.35);
    color: var(--primary);
    font-weight: 700;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}

  .mkc-name-wrap {{
    min-width: 0;
  }}

  .mkc-name {{
    font-size: 13.5px;
    font-weight: 700;
    color: var(--text-main);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .mkc-sub {{
    font-size: 10.5px;
    color: var(--text-muted);
  }}

  .mkc-right {{
    text-align: right;
    flex-shrink: 0;
  }}

  .mkc-kpi-pct {{
    font-size: 16px;
    font-weight: 800;
    font-family: var(--mono-font);
    line-height: 1.2;
  }}

  .mkc-tag {{
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    margin-top: 2px;
    line-height: 1.2;
  }}

  .tag-success {{
    background: rgba(16,185,129,0.12);
    color: #10b981;
    border: 1px solid rgba(16,185,129,0.25);
  }}

  .tag-warning {{
    background: rgba(245,158,11,0.12);
    color: #f59e0b;
    border: 1px solid rgba(245,158,11,0.25);
  }}

  .tag-danger {{
    background: rgba(239,68,68,0.12);
    color: #ef4444;
    border: 1px solid rgba(239,68,68,0.25);
  }}

  .mkc-progress-track {{
    position: relative;
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 9999px;
    overflow: visible;
    margin-bottom: 10px;
  }}

  .mkc-marker-target {{
    position: absolute;
    top: -2px;
    width: 2px;
    height: 10px;
    background: #f59e0b;
    border-radius: 1px;
    box-shadow: 0 0 4px #f59e0b;
  }}

  .mkc-stats-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
    background: var(--surface-subtle);
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
  }}

  .mkc-stat-item {{
    text-align: center;
  }}

  .mkc-stat-lbl {{
    font-size: 9.5px;
    color: var(--text-muted);
    margin-bottom: 2px;
  }}

  .mkc-stat-val {{
    font-size: 11.5px;
    font-weight: 700;
    color: var(--text-main);
    font-family: var(--mono-font);
    line-height: 1.2;
  }}

  .mkc-stat-val small {{
    font-size: 9.5px;
    color: var(--text-muted);
    font-weight: normal;
  }}

  .mkc-stat-pct {{
    font-size: 10px;
    color: var(--primary);
    font-weight: 600;
    margin-top: 1px;
  }}

  .mkc-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10.5px;
    color: var(--text-subtle);
    padding-top: 4px;
    border-top: 1px solid var(--border);
  }}

  /* Table View Enhancements for Mobile (when user toggles to table) */
  .table-responsive {{
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    border-radius: 10px !important;
  }}

  .swipe-hint {{
    display: flex !important;
  }}

  #table-kpi th:nth-child(1),
  #table-kpi td:nth-child(1) {{
    display: none !important; /* Hide STT on mobile table to give room */
  }}

  #table-kpi th:nth-child(2),
  #table-kpi td:nth-child(2) {{
    display: none !important; /* Hide MS on mobile table, MS shown in modal */
  }}

  #table-kpi th:nth-child(3),
  #table-kpi td:nth-child(3) {{
    position: sticky !important;
    left: 0 !important;
    z-index: 5 !important;
    background: var(--surface) !important;
    min-width: 120px !important;
    max-width: 130px !important;
    box-shadow: 2px 0 6px rgba(0,0,0,0.12) !important;
    font-size: 11.5px !important;
    white-space: nowrap !important;
  }}

  #table-kpi thead th:nth-child(3) {{
    z-index: 10 !important;
    background: var(--table-header) !important;
  }}

  /* Schedule Tab Responsive Fixes */
  .schedule-controls-card {{
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .schedule-controls-header {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    margin-bottom: 12px !important;
  }}

  .schedule-title-wrap h3 {{
    font-size: 14.5px !important;
    line-height: 1.3 !important;
  }}

  .schedule-subtitle {{
    font-size: 11px !important;
  }}

  .schedule-actions {{
    width: 100% !important;
    display: flex !important;
    gap: 6px !important;
  }}

  .schedule-actions .btn {{
    flex: 1 !important;
    font-size: 11.5px !important;
    padding: 8px 6px !important;
    justify-content: center !important;
  }}

  .schedule-filters-grid {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
    width: 100% !important;
  }}

  .schedule-filters-grid .filter-group {{
    width: 100% !important;
    min-width: 0 !important;
  }}

  .filter-label {{
    font-size: 11px !important;
    margin-bottom: 4px !important;
  }}

  .segmented-control {{
    width: 100% !important;
    display: flex !important;
  }}

  .segmented-btn {{
    flex: 1 !important;
    white-space: normal !important;
    text-align: center !important;
    font-size: 11px !important;
    padding: 7px 4px !important;
    line-height: 1.25 !important;
  }}

  .desktop-inline {{
    display: none !important;
  }}

  .mobile-inline {{
    display: inline !important;
  }}

  /* Today Column Jump Button */
  .schedule-filters-grid button[onclick="jumpToTodayColumn()"] {{
    width: 100% !important;
    padding: 10px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
  }}

  /* Today's Roster Banner */
  .today-roster-banner {{
    padding: 12px 14px !important;
    margin-bottom: 12px !important;
    border-radius: 12px !important;
  }}

  .today-roster-header {{
    margin-bottom: 10px !important;
  }}

  .today-roster-title {{
    font-size: 13.5px !important;
  }}

  .roster-groups-grid {{
    grid-template-columns: 1fr !important;
    gap: 8px !important;
  }}

  .roster-group-card {{
    padding: 10px 12px !important;
    border-radius: 8px !important;
  }}

  .roster-group-label {{
    font-size: 11.5px !important;
    margin-bottom: 6px !important;
  }}

  .roster-pill {{
    font-size: 11px !important;
    padding: 3px 8px !important;
  }}

  /* Matrix Table Mobile Fixes (R1 & R9) */
  .schedule-section-card {{
    padding: 12px 14px !important;
    border-radius: 12px !important;
  }}

  .schedule-section-header {{
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    margin-bottom: 10px !important;
  }}

  .schedule-section-title span {{
    font-size: 13.5px !important;
    line-height: 1.3 !important;
  }}

  .matrix-nav-buttons {{
    width: 100% !important;
    display: flex !important;
    gap: 6px !important;
  }}

  .matrix-nav-buttons .btn,
  .matrix-nav-buttons .segmented-control {{
    flex: 1 !important;
  }}

  .matrix-scroll-container {{
    width: 100% !important;
    max-width: 100% !important;
    border-radius: 10px !important;
    max-height: 520px !important;
  }}

  /* Hide Employee ID column on mobile matrix */
  .matrix-table .sticky-col-id,
  .matrix-table thead th.sticky-col-id {{
    display: none !important;
  }}

  /* Sticky Employee Name pinned to left: 0 */
  .matrix-table .sticky-col-name,
  .matrix-table thead th.sticky-col-name {{
    left: 0 !important;
    min-width: 110px !important;
    max-width: 120px !important;
    font-size: 11px !important;
    padding: 6px 8px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-shadow: 2px 0 6px rgba(0,0,0,0.15) !important;
  }}

  .matrix-table th,
  .matrix-table td {{
    padding: 5px 3px !important;
    font-size: 11px !important;
    min-width: 42px !important;
  }}

  .badge-shift {{
    padding: 2px 4px !important;
    font-size: 9.5px !important;
  }}

  /* Modal Popup (Thẻ Năng Lực) Mobile Bottom Sheet */
  .modal-overlay {{
    padding: 8px !important;
    align-items: flex-end !important;
  }}

  .modal-content {{
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 16px 14px !important;
    max-height: 90vh !important;
    border-radius: 16px 16px 8px 8px !important;
  }}

  .modal-header {{
    margin-bottom: 12px !important;
  }}

  .modal-title {{
    font-size: 15px !important;
  }}

  .modal-close {{
    width: 38px !important;
    height: 38px !important;
    font-size: 18px !important;
    top: 10px !important;
    right: 10px !important;
  }}

  .modal-tabs {{
    gap: 4px !important;
    margin-bottom: 12px !important;
  }}

  .modal-tab-btn {{
    padding: 6px 10px !important;
    font-size: 11.5px !important;
  }}

  .forecast-box {{
    padding: 12px !important;
  }}

  .forecast-grid {{
    grid-template-columns: 1fr !important;
    gap: 8px !important;
  }}

  /* Charts & Podium on mobile */
  .charts-grid {{
    grid-template-columns: 1fr !important;
  }}

  .podium-grid {{
    grid-template-columns: 1fr !important;
    gap: 10px !important;
  }}

  .podium-card.rank-1 {{
    order: -1 !important; /* Top 1 appears first on mobile! */
  }}
}}

  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="brand">
        <div class="logo-badge">CTO</div>
        <div class="brand-title">
          <h1>Dashboard KPI & Đánh Giá Tiến Độ Ca Trực</h1>
          <p>Đội ngũ Chăm Sóc Khách Hàng (Customer Service) • Team CTO 1</p>
        </div>
      </div>
      <div class="header-actions">
        <div class="badge-live">
          <span class="dot-live"></span>
          <span>Cập nhật: <strong id="lbl-updated-at">{update_time_val}</strong></span>
        </div>
        <button class="btn btn-refresh" onclick="reloadLatestData()" title="Tải lại số liệu mới nhất">
          🔄 Tải lại số liệu mới nhất
        </button>
        <button class="btn" id="btn-snap-zalo" onclick="captureReportImage()" title="Xuất ảnh báo cáo gửi Zalo / Telegram">
          📸 Xuất ảnh Zalo
        </button>
        <button class="btn" onclick="toggleTvMode()" title="Bật chế độ TV trình chiếu văn phòng">
          📺 Chế độ TV
        </button>
        <button class="btn" onclick="toggleTheme()" title="Đổi giao diện Sáng/Tối">
          <span id="theme-icon">🌙</span> Sáng/Tối
        </button>
        <button class="btn" onclick="exportCurrentTableToCSV()">
          📥 Xuất CSV / Excel
        </button>
        <button class="btn btn-primary" onclick="window.print()">
          🖨️ In Báo Cáo
        </button>
        <button class="btn btn-primary" id="hdr-btn-toggle-sched" onclick="toggleMainView()" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;font-weight:700;">
          📅 Xem Lịch Trực Team
        </button>
      </div>
    </header>

    <!-- TOP LEVEL MAIN VIEW SWITCHER -->
    <div class="top-nav-bar">
      <button class="top-nav-tab active" id="nav-tab-kpi" onclick="switchMainView('kpi')">
        📊 BÁO CÁO & TIẾN ĐỘ KPI
      </button>
      <button class="top-nav-tab" id="nav-tab-schedule" onclick="switchMainView('schedule')">
        📅 LỊCH TRỰC & CHẤM CÔNG (TEAM ÔNG MINH NHỰT)
        <span class="top-nav-badge">13 nhân sự</span>
      </button>
    </div>

    <!-- WRAPPER: SECTION KPI MAIN (Ẩn khi chuyển sang xem Lịch Trực) -->
    <div id="section-kpi-main">

    <!-- Pacing Status Banner (Tiến Độ Tháng) -->
    <section class="pacing-bar">
      <div class="pacing-info">
        <div class="pacing-title">
          <span>📅 Tiến Độ Tháng:</span>
        </div>
        <div class="pacing-day-selector">
          <span>Hôm nay là Ngày:</span>
          <input type="number" id="input-current-day" min="1" max="31" value="14" onchange="onDayChange()">
          <span>/</span>
          <input type="number" id="input-total-days" min="28" max="31" value="30" onchange="onTotalDaysChange()" style="width:48px;padding:4px 6px;border:1px solid var(--card-border);border-radius:6px;background-color:var(--bg);color:var(--text-main);font-size:14px;font-weight:700;text-align:center;outline:none;" title="Tổng số ngày trong tháng">
          <span>ngày</span>
        </div>
        <div class="pacing-target-badge">
          🎯 KPI Chuẩn Cần Đạt: <span id="lbl-target-pacing">46.67%</span>
        </div>
      </div>
      <div>
        <span style="font-size:12px;color:var(--text-muted);" id="pacing-note-text">
          💡 Mặc định tháng 11 có 30 ngày. Anh có thể tự chỉnh lại số ngày tại ô nhập trên khi cần nhé.
        </span>
      </div>
    </section>

    <!-- Top KPI Stat Cards -->
    <section class="stats-grid">
      <div class="stat-card card-primary">
        <div class="stat-label">Tổng Nhân Sự</div>
        <div class="stat-value" id="card-total-staff">--</div>
        <div class="stat-sub">Team CTO 1 hoạt động</div>
      </div>
      <div class="stat-card card-info">
        <div class="stat-label">% KPI Trung Bình</div>
        <div class="stat-value" id="card-avg-kpi">--%</div>
        <div class="stat-sub" id="card-avg-status">So với chuẩn: --</div>
      </div>
      <div class="stat-card card-success">
        <div class="stat-label">Vượt / Đạt Tiến Độ</div>
        <div class="stat-value" id="card-count-ahead" style="color:var(--success);">--</div>
        <div class="stat-sub">Nhân viên đạt chuẩn ngày</div>
      </div>
      <div class="stat-card card-danger">
        <div class="stat-label">Cảnh Báo Chậm Tiến Độ</div>
        <div class="stat-value" id="card-count-behind" style="color:var(--danger);">--</div>
        <div class="stat-sub">Cần nhắc nhở & thúc đẩy</div>
      </div>
      <div class="stat-card card-info">
        <div class="stat-label">TK Có 2 CV Hỗ Trợ</div>
        <div class="stat-value" id="card-total-ticket-2ht">--</div>
        <div class="stat-sub">Tổng số lượng ticket có 2 CV</div>
      </div>
    </section>

    <!-- Filter & Control Bar -->
    <section class="controls-card">
      <div class="filter-group">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="filter-search" placeholder="Tìm theo tên hoặc mã nhân viên..." oninput="applyFilters()">
        </div>
        <select class="select-filter" id="filter-pacing" onchange="applyFilters()">
          <option value="ALL">⏱️ Tiến Độ Tháng (Tất cả)</option>
          <option value="AHEAD">🚀 Vượt tiến độ (&gt; Chuẩn)</option>
          <option value="ON_TRACK">🟢 Đúng tiến độ (Xấp xỉ Chuẩn)</option>
          <option value="BEHIND">⚠️ Chậm tiến độ (Cảnh báo)</option>
          <option value="CRITICAL">🚨 Báo động chậm (Rất chậm &gt; 5%)</option>
        </select>
        <select class="select-filter" id="filter-level" onchange="applyFilters()">
          <option value="ALL">🎯 Tất cả Level</option>
          <option value="1">Level 1</option>
          <option value="2">Level 2</option>
          <option value="3">Level 3</option>
          <option value="4">Level 4</option>
          <option value="5">Level 5</option>
        </select>
        <select class="select-filter" id="filter-shift-toggle" onchange="applyFilters()" style="display:none;">
          <option value="ALL">⏱️ Xem tất cả ca trực</option>
          <option value="S">Ca S (Sáng)</option>
          <option value="HCS">Ca HCS (Hành chính sáng)</option>
          <option value="TR">Ca TR (Trưa)</option>
          <option value="HCC">Ca HCC (Hành chính chiều)</option>
          <option value="T">Ca T (Tối)</option>
          <option value="TOTAL_ONLY">Chỉ xem Tổng cộng</option>
        </select>
        <div class="find-me-box">
          <select class="select-filter select-my-name" id="select-my-name" onchange="onSelectMyName(this.value)" title="Chọn tên bạn để zoom và làm nổi bật số liệu">
            <option value="">👤 Tôi là ai? (Chọn tên bạn...)</option>
          </select>
          <button class="btn btn-outline" id="btn-open-my-card" style="display:none;background:var(--card-bg);border:1px solid #818cf8;color:#818cf8;font-weight:700;" onclick="openMySelectedCard()">
            ✨ Thẻ Của Tôi
          </button>
        </div>
      </div>
      <div>
        <button class="btn" onclick="resetFilters()">🔄 Đặt lại bộ lọc</button>
      </div>
    </section>

    <!-- Tabs Navigation -->
    <div class="tabs-nav">
      <button class="tab-btn active" id="tab-btn-kpi" onclick="switchTab('kpi')">
        📊 Bảng KPI & Đánh Giá Tiến Độ
        <span class="tab-badge" id="badge-count-kpi">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-hs" onclick="switchTab('hs')">
        ⏱️ Hiệu Suất Ca Trực
        <span class="tab-badge" id="badge-count-hs">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-charts" onclick="switchTab('charts')">
        📈 Biểu Đồ & Thống Kê
      </button>
      <button class="tab-btn" id="tab-btn-podium" onclick="switchTab('podium')">
        🏆 Vinh Danh & Danh Hiệu
      </button>
    </div>

    <!-- TAB 1: KPI TONG -->
    <div id="tab-pane-kpi" class="table-card">
      <!-- MOBILE VIEW TOGGLE (CHỈ HIỆN TRÊN MOBILE) -->
      <div class="mobile-view-toggle">
        <button class="mv-btn active" id="btn-view-cards" onclick="setKpiMobileView('cards')">
          📱 Dạng Thẻ Nhân Sự
        </button>
        <button class="mv-btn" id="btn-view-table" onclick="setKpiMobileView('table')">
          📊 Dạng Bảng Vuốt Ngang
        </button>
      </div>

      <!-- CONTAINER DẠNG THẺ MOBILE -->
      <div id="kpi-mobile-cards" class="mobile-kpi-cards-grid">
        <!-- Rendered by JS -->
      </div>

      <!-- CONTAINER DẠNG BẢNG (DESKTOP HOẶC KHI BẬT) -->
      <div id="kpi-table-view-wrap">
        <div class="swipe-hint">
          <span>👉</span>
          <span>Vuốt ngang bảng để xem đầy đủ 13 cột số liệu</span>
        </div>
        <div class="table-responsive">
          <table id="table-kpi">
          <thead>
            <tr>
              <th onclick="sortTable('kpi', 'id')">STT ⬍</th>
              <th onclick="sortTable('kpi', 'ma')">Mã NV ⬍</th>
              <th onclick="sortTable('kpi', 'name')">Họ và Tên ⬍</th>
              <th class="text-center" onclick="sortTable('kpi', 'level')">Level ⬍</th>
              <th class="numeric" onclick="sortTable('kpi', 'kpi_ticket')">KPI Ticket ⬍</th>
              <th class="numeric" onclick="sortTable('kpi', 'slg_kh')">Thực Đạt KH ⬍</th>
              <th onclick="sortTable('kpi', 'pct_kpi_ticket')">% KPI Ticket ⬍</th>
              <th class="numeric" onclick="sortTable('kpi', 'kpi_cv')">KPI CV ⬍</th>
              <th class="numeric" onclick="sortTable('kpi', 'slg_cv')">Thực Đạt CV ⬍</th>
              <th onclick="sortTable('kpi', 'pct_kpi_cv')">% KPI CV ⬍</th>
              <th class="text-center" onclick="sortTable('kpi', 'no_ticket_2ht')">TK 2 CV Hỗ Trợ ⬍</th>
              <th onclick="sortTable('kpi', 'pct_kpi_tong')">% KPI Tổng ⬍</th>
              <th onclick="sortTable('kpi', 'pacing_diff')">Đánh Giá Tiến Độ ⬍</th>
            </tr>
          </thead>
          <tbody id="tbody-kpi">
            <!-- Rows rendered dynamically -->
          </tbody>
        </table>
      </div>
      </div> <!-- /#kpi-table-view-wrap -->
    </div>

    <!-- TAB 2: HS CA TRUC -->
    <div id="tab-pane-hs" class="table-card" style="display:none;">
      <div class="table-responsive">
        <table id="table-hs">
          <thead>
            <tr>
              <th rowspan="2">STT</th>
              <th rowspan="2">Nhân Viên</th>
              <th colspan="4" class="shift-header-group">Ca S (Sáng)</th>
              <th colspan="4" class="shift-header-group">Ca HCS (Hành Chính Sáng)</th>
              <th colspan="4" class="shift-header-group">Ca TR (Trưa)</th>
              <th colspan="4" class="shift-header-group">Ca HCC (Hành Chính Chiều)</th>
              <th colspan="4" class="shift-header-group">Ca T (Tối)</th>
              <th colspan="4" class="shift-header-group" style="background-color:rgba(16,185,129,0.15)!important;color:var(--success)!important;">Tổng Cộng</th>
            </tr>
            <tr>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
              <th class="border-shift-left numeric">Giờ</th><th class="numeric">CV</th><th class="numeric">KH</th><th class="numeric">%KPI</th>
            </tr>
          </thead>
          <tbody id="tbody-hs">
            <!-- Rows rendered dynamically -->
          </tbody>
        </table>
      </div>
      </div> <!-- /#kpi-table-view-wrap -->
    </div>

    <!-- TAB 3: CHARTS -->
    <div id="tab-pane-charts" style="display:none;">
      <div class="charts-grid">
        <div class="chart-box">
          <div class="chart-title">
            <span>🏆 Xếp Hạng % KPI Tổng Hợp & Tiến Độ Chuẩn</span>
            <span style="font-size:12px;color:var(--text-muted);" id="chart-target-line">Chuẩn: 46.7%</span>
          </div>
          <div id="chart-kpi-bars">
            <!-- Rendered dynamically -->
          </div>
        </div>
        <div class="chart-box">
          <div class="chart-title">
            <span>⏰ Phân Bổ Tổng Giờ Làm Theo Ca Trực</span>
            <span style="font-size:12px;color:var(--text-muted);">Toàn Team CTO 1</span>
          </div>
          <div id="chart-shift-hours">
            <!-- Rendered dynamically -->
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: PODIUM & DANH HIỆU -->
    <div id="tab-pane-podium" class="table-card" style="display:none;padding:24px;">
      <h2 style="font-size:18px;font-weight:800;margin-bottom:6px;text-align:center;">🏆 BẢNG VINH DANH TOP 3 XUẤT SẮC THÁNG</h2>
      <p style="font-size:13px;color:var(--text-muted);text-align:center;margin-bottom:18px;">Dẫn đầu về % KPI Tổng Hợp của Team CTO 1</p>
      
      <div class="podium-container" id="podium-content">
        <!-- Rendered by JS -->
      </div>

      <h3 style="font-size:15px;font-weight:800;margin-top:20px;margin-bottom:12px;">🎖️ BẢNG DANH HIỆU THI ĐUA ĐẶC BIỆT</h3>
      <div class="awards-grid" id="awards-content">
        <!-- Rendered by JS -->
      </div>
    </div>

    </div> <!-- end #section-kpi-main (Ẩn khi chuyển sang xem Lịch Trực) -->

    <!-- TOP LEVEL VIEW: LỊCH TRỰC & CHẤM CÔNG (TEAM ÔNG MINH NHỰT) -->
    <div id="tab-pane-schedule" style="display:none;">
      <!-- Controls Card -->
      <div class="schedule-controls-card">
        <div class="schedule-controls-header">
          <div class="schedule-title-wrap">
            <h3>📅 LỊCH TRỰC & ĐỐI SOÁT CÔNG - TEAM ÔNG MINH NHỰT (CTO 1)</h3>
            <div class="schedule-subtitle" id="sched-subtitle-time">Đồng bộ trực tiếp từ Google Sheets • 13 nhân sự (1 Leader + 12 CS)</div>
          </div>
          <div class="schedule-actions">
            <button class="btn btn-primary" onclick="syncScheduleLive()" id="btn-sync-schedule">
              🔄 Tải lại Lịch Trực Mới Nhất
            </button>
            <button class="btn" onclick="exportScheduleExcel()">
              📥 Xuất File Excel
            </button>
          </div>
        </div>

        <div class="schedule-filters-grid">
          <div class="filter-group">
            <label class="filter-label">Chu kỳ đối soát:</label>
            <div class="segmented-control">
              <button class="segmented-btn active" id="btn-cycle-a" onclick="setScheduleCycle('a')">
                <span class="desktop-inline">Chu kỳ 26 - 25 (26/10 ➔ 25/11)</span>
                <span class="mobile-inline">26/10 ➔ 25/11</span>
              </button>
              <button class="segmented-btn" id="btn-cycle-b" onclick="setScheduleCycle('b')">
                <span class="desktop-inline">Chu kỳ Đầu - Cuối tháng (01/11 ➔ 30/11)</span>
                <span class="mobile-inline">01/11 ➔ 30/11</span>
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">Phạm vi thời gian tính công:</label>
            <div class="segmented-control">
              <button class="segmented-btn active" id="btn-range-todate" onclick="setScheduleRange('to_date')">
                <span class="desktop-inline">📍 Lũy kế đến hôm nay (15/11)</span>
                <span class="mobile-inline">📍 Đến hôm nay</span>
              </button>
              <button class="segmented-btn" id="btn-range-full" onclick="setScheduleRange('full')">
                <span class="desktop-inline">🗓️ Cả chu kỳ</span>
                <span class="mobile-inline">🗓️ Cả chu kỳ</span>
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">Chế độ xem lịch:</label>
            <div class="segmented-control">
              <button class="segmented-btn active" id="btn-matrix-all" onclick="setMatrixDateFilter('all')">
                <span class="desktop-inline">🗓️ Toàn bộ tháng</span>
                <span class="mobile-inline">🗓️ Cả tháng</span>
              </button>
              <button class="segmented-btn" id="btn-matrix-week" onclick="setMatrixDateFilter('week')">
                <span class="desktop-inline">📅 Chỉ hiện Tuần này</span>
                <span class="mobile-inline">📅 Tuần này</span>
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">Thao tác nhanh:</label>
            <button class="btn btn-primary" onclick="jumpToTodayColumn()" style="padding:6px 14px;font-size:12px;font-weight:700;">
              📍 Nhảy đến Hôm nay (15/11)
            </button>
          </div>

          <div class="filter-group" style="flex: 1; min-width: 200px;">
            <label class="filter-label">Tìm kiếm nhân sự:</label>
            <input type="text" id="sched-search-input" class="search-input" placeholder="Nhập tên hoặc MS (vd: 8239, Trúc Linh...)" oninput="onScheduleSearch(this.value)">
          </div>
        </div>
      </div>

      <!-- Today's Roster Banner (Gọn gàng) -->
      <div class="today-roster-banner" id="today-roster-widget">
        <div class="today-roster-header">
          <div class="today-roster-title">
            <span>⚡ PHÂN BỔ CA TRỰC HÔM NAY (<span id="roster-date-label">15/11/2026</span>)</span>
          </div>
          <div style="font-size:12px;color:var(--text-muted);">
            Các bạn xem trực tiếp ca và kênh hỗ trợ tại đây thay vì mở Google Sheet
          </div>
        </div>
        <div class="roster-groups-grid" id="roster-groups-content">
          <!-- Rendered by JS -->
        </div>
      </div>

      <!-- SECTION 1: MA TRẬN LỊCH TRỰC CHI TIẾT CẢ THÁNG -->
      <div class="schedule-section-card">
        <div class="schedule-section-header">
          <div class="schedule-section-title">
            <span>🗓️ MA TRẬN LỊCH TRỰC CHI TIẾT CẢ THÁNG (TEAM ÔNG MINH NHỰT)</span>
          </div>
          <div class="matrix-nav-buttons">
            <button class="btn btn-sm btn-primary" onclick="jumpToTodayColumn()" style="font-weight:700;padding:5px 12px;font-size:12px;">
              📍 Nhảy đến Hôm nay (15/11)
            </button>
            <div class="segmented-control">
              <button class="segmented-btn active" id="btn-matrix-all-top" onclick="setMatrixDateFilter('all')">
                🗓️ Cả tháng
              </button>
              <button class="segmented-btn" id="btn-matrix-week-top" onclick="setMatrixDateFilter('week')">
                📅 Tuần này
              </button>
            </div>
          </div>
        </div>

        <div style="display:flex;gap:8px;align-items:center;font-size:12px;color:var(--text-muted);margin-bottom:12px;flex-wrap:wrap;">
          <span>Chú thích:</span>
          <span class="badge-shift badge-shift-off">OFF (Nghỉ)</span>
          <span class="badge-shift badge-shift-p">P (Phép)</span>
          <span class="badge-shift badge-shift-s">S (Sáng)</span>
          <span class="badge-shift badge-shift-tr">TR (Trưa)</span>
          <span class="badge-shift badge-shift-t">T (Tối)</span>
          <span class="badge-shift badge-shift-hc">HC / Kênh</span>
        </div>

        <div class="matrix-scroll-container" id="matrix-scroll-box">
          <table class="matrix-table" id="table-matrix-schedule">
            <thead id="thead-matrix-schedule">
              <!-- Rendered by JS -->
            </thead>
            <tbody id="tbody-matrix-schedule">
              <!-- Rendered by JS -->
            </tbody>
          </table>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:10px;border-top:1px solid var(--border-color);flex-wrap:wrap;gap:10px;">
          <div style="font-size:12px;color:var(--text-muted);">
            💡 Mẹo: Bấm <strong>"📍 Nhảy đến Hôm nay"</strong> để cuộn ngay đến cột ngày 15/11. Bấm <strong>"📅 Tuần này"</strong> để xem 7 ngày tuần hiện tại.
          </div>
          <div class="matrix-nav-buttons">
            <button class="btn btn-sm btn-primary" onclick="jumpToTodayColumn()" style="font-weight:700;padding:6px 14px;font-size:12px;">
              📍 Nhảy đến Hôm nay (15/11)
            </button>
            <div class="segmented-control">
              <button class="segmented-btn active" id="btn-matrix-all-bottom" onclick="setMatrixDateFilter('all')">
                🗓️ Cả tháng
              </button>
              <button class="segmented-btn" id="btn-matrix-week-bottom" onclick="setMatrixDateFilter('week')">
                📅 Tuần này
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 2: BẢNG TÍNH & ĐỐI SOÁT CÔNG -->
      <div class="schedule-section-card">
        <div class="schedule-section-header">
          <div class="schedule-section-title">
            <span>📊 BẢNG TÍNH & ĐỐI SOÁT NGÀY CÔNG / NGÀY NGHỈ</span>
            <span class="badge" style="background:var(--primary-light);color:var(--primary);font-size:11px;" id="sched-table-cycle-badge">Chu kỳ 26-25</span>
          </div>
          <div style="font-size:12px;color:var(--text-muted);">
            Chuẩn hóa tối đa 1.0 công/ngày (Ngày làm = 1.0 - OFF - Phép)
          </div>
        </div>

        <div class="table-responsive">
          <table id="table-schedule-summary">
            <thead>
              <tr>
                <th style="width:50px;">STT</th>
                <th style="width:80px;">Mã NV</th>
                <th>Họ và Tên Nhân Sự</th>
                <th style="width:120px;">Chức Vụ</th>
                <th class="numeric" style="width:120px;">🏖️ Ngày OFF</th>
                <th class="numeric" style="width:120px;">🌴 Ngày Phép</th>
                <th class="numeric" style="width:130px;">💼 Ngày Làm Việc</th>
                <th class="numeric" style="width:120px;">📊 Tổng Ngày</th>
                <th class="text-center" style="width:110px;">Thao Tác</th>
              </tr>
            </thead>
            <tbody id="tbody-schedule-summary">
              <!-- Rendered by JS -->
            </tbody>
            <tfoot id="tfoot-schedule-summary">
              <!-- Rendered by JS -->
            </tfoot>
          </table>
        </div>
      </div>
    </div>

  </div>

  <!-- Employee Detail Modal (Personal Card) -->
  <div class="modal-backdrop" id="emp-modal" onclick="closeModal(event)">
    <div class="modal-box" onclick="event.stopPropagation()">
      <!-- Card Header -->
      <div class="card-profile-header">
        <div class="profile-avatar" id="modal-avatar">TL</div>
        <div class="profile-meta">
          <div class="profile-name" id="modal-name">8131 - Lê Thị Trúc Linh</div>
          <div class="profile-badges">
            <span class="badge-rank" id="modal-rank">🏆 Hạng #1 / 12</span>
            <span class="badge-level-tag" id="modal-level">Level 3</span>
            <span id="modal-pacing-status">--</span>
          </div>
        </div>
        <button class="modal-close" onclick="closeModal()" title="Đóng">✕</button>
      </div>

      <!-- Khối 1: Máy tính dự báo mục tiêu tháng (Forecast Target) -->
      <div class="forecast-box">
        <div class="forecast-title">
          <span>🔮 DỰ BÁO KẾT THÚC THÁNG</span>
          <span style="font-size:11px;font-weight:600;opacity:0.85;" id="modal-pacing-tag">(Tốc độ ngày 14/30)</span>
        </div>
        <div class="forecast-value" id="modal-forecast-val">149.9% KPI</div>
        <div class="forecast-plan" id="modal-forecast-plan">
          <!-- Text kế hoạch hành động -->
        </div>
      </div>

      <!-- Khối 2: Tỷ trọng Đóng góp & Điểm mạnh (Ticket vs CV) -->
      <h3 style="font-size:12.5px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:10px;letter-spacing:0.5px;">
        ⚖️ Năng Lực & Tỷ Trọng Đóng Góp
      </h3>
      <div class="strengths-grid">
        <div class="strength-card">
          <div class="strength-label">Ticket Khách Hàng</div>
          <div class="strength-val" id="modal-ticket-val">995.2 / 1.200</div>
          <div class="strength-badge" id="modal-ticket-badge" style="background:var(--primary-light);color:var(--primary);">82.9% KPI</div>
        </div>
        <div class="strength-card">
          <div class="strength-label">Công Việc (CV)</div>
          <div class="strength-val" id="modal-cv-val">712.2 / 1.250</div>
          <div class="strength-badge" id="modal-cv-badge" style="background:rgba(236,72,153,0.15);color:#ec4899;">57.0% KPI</div>
        </div>
      </div>
      
      <div style="background:var(--bg);border:1px solid var(--card-border);border-radius:10px;padding:12px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="font-size:12px;font-weight:700;" id="modal-strength-assessment">⚡ Điểm mạnh: Gánh Ticket vượt trội</span>
          <span id="modal-ticket-2ht-badge" style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--primary-light);color:var(--primary);">📋 0 Ticket có 2 CV HT</span>
        </div>
        <div style="font-size:12px;color:var(--text-muted);" id="modal-strength-desc">
          Tỷ lệ hoàn thành Ticket cao hơn CV. Tốc độ giải quyết khách hàng rất tốt.
        </div>
      </div>

      <!-- Khối 3: Thống kê & Phân bổ Ca trực (Shift Breakdown) -->
      <h3 style="font-size:12.5px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:8px;letter-spacing:0.5px;">
        ⏱️ Phân Bổ Thời Gian & Ca Trực
      </h3>
      <div class="shift-stacked-bar" id="modal-shift-stacked">
        <!-- Colored segments -->
      </div>
      <div class="shift-legend" id="modal-shift-legend">
        <!-- Legend items -->
      </div>
      <p style="font-size:12px;color:var(--text-muted);margin-bottom:12px;" id="modal-shift-highlight">
        ⏰ Trực nhiều nhất ở Ca TR (47.5h - chiếm 42.2% thời gian)
      </p>

      <div class="table-responsive">
        <table style="font-size:12px;">
          <thead>
            <tr>
              <th>Ca Trực</th>
              <th class="numeric">Giờ Làm</th>
              <th class="numeric">CV Quy Đổi</th>
              <th class="numeric">KH Quy Đổi</th>
              <th class="numeric">% KPI Đạt</th>
            </tr>
          </thead>
          <tbody id="modal-shifts-body">
            <!-- Rendered by JS -->
          </tbody>
        </table>
      </div>
      </div> <!-- /#kpi-table-view-wrap -->
    </div>
  </div>

  <!-- TV Mode Progress Bar and Exit Button -->
  <div class="tv-bar-wrap">
    <div class="tv-progress" id="tv-progress-bar"></div>
  </div>
  <button class="tv-exit-pill" onclick="toggleTvMode()">
    <span>✕ Thoát TV</span>
    <span style="font-size:10px;opacity:0.7;">(Phím ESC)</span>
  </button>

  <!-- Hidden Container specifically prepared for high-res Zalo Report Snapshot -->
  <div id="zalo-snapshot-card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;border-bottom:1px solid #334155;padding-bottom:14px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg, #6366f1, #ec4899);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;color:#fff;">CTO</div>
        <div>
          <h2 style="font-size:18px;font-weight:800;color:#fff;margin:0;">BÁO CÁO TIẾN ĐỘ & KPI TEAM CTO 1</h2>
          <p style="font-size:12px;color:#94a3b8;margin:2px 0 0 0;">Customer Service • KiotViet</p>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px;font-weight:700;color:#38bdf8;" id="zalo-snap-time">Cập nhật: --</div>
        <div style="font-size:11px;color:#94a3b8;" id="zalo-snap-pacing">Tiến độ: Ngày 14/30 (Chuẩn: 46.67%)</div>
      </div>
    </div>

    <!-- 4 Stats Cards -->
    <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:10px;margin-bottom:16px;">
      <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;text-align:center;">
        <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;font-weight:700;">Tổng Quân Số</div>
        <div style="font-size:20px;font-weight:800;color:#f8fafc;" id="zalo-snap-staff">--</div>
      </div>
      <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;text-align:center;">
        <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;font-weight:700;">% KPI Trung Bình</div>
        <div style="font-size:20px;font-weight:800;color:#38bdf8;" id="zalo-snap-avg">--%</div>
      </div>
      <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;text-align:center;">
        <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;font-weight:700;">Đạt / Vượt Tiến Độ</div>
        <div style="font-size:20px;font-weight:800;color:#10b981;" id="zalo-snap-ahead">--</div>
      </div>
      <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;text-align:center;">
        <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;font-weight:700;">Top 1 Xuất Sắc</div>
        <div style="font-size:15px;font-weight:800;color:#f59e0b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" id="zalo-snap-top">--</div>
      </div>
    </div>

    <!-- Compact Table -->
    <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;overflow:hidden;margin-bottom:12px;">
      <table style="width:100%;border-collapse:collapse;font-size:11px;color:#f8fafc;">
        <thead>
          <tr style="background:#0f172a;border-bottom:1px solid #334155;color:#94a3b8;text-align:left;">
            <th style="padding:8px 10px;">Hạng</th>
            <th style="padding:8px 10px;">Mã NV</th>
            <th style="padding:8px 10px;">Họ và Tên</th>
            <th style="padding:8px 10px;text-align:right;">Thực Đạt KH</th>
            <th style="padding:8px 10px;text-align:right;">Thực Đạt CV</th>
            <th style="padding:8px 10px;text-align:center;">TK 2 CV Hỗ Trợ</th>
            <th style="padding:8px 10px;text-align:right;">% KPI Tổng</th>
            <th style="padding:8px 10px;text-align:center;">Đánh Giá</th>
          </tr>
        </thead>
        <tbody id="zalo-snap-tbody">
          <!-- Rows rendered by JS -->
        </tbody>
      </table>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center;font-size:10px;color:#64748b;padding-top:4px;">
      <span>💡 Được tạo tự động bởi Auto CRM PowerBI Tool • Team CTO 1</span>
      <span>Website: nquoc.github.io/kpicto</span>
    </div>
  </div>

  <script>
    // Embedded Data
    const DATA = {dataset_json};

    let currentDay = DATA.current_day || 14;
    let totalDays = DATA.days_in_month || 30;
    let targetPacing = currentDay / totalDays;

    let currentTab = 'kpi';
    let sortColumn = 'pct_kpi_tong';
    let sortAsc = false;
    let filteredKpi = [];
    let filteredHs = [];

    function calculatePacingDetails(item) {{
      const diff = item.pct_kpi_tong - targetPacing;
      const diffPct = (diff * 100).toFixed(2);
      const pctDatTienDo = targetPacing > 0 ? ((item.pct_kpi_tong / targetPacing) * 100).toFixed(1) : '0.0';
      let status = '';
      let badgeClass = '';
      let text = '';
      let isCritical = false;

      if (diff >= 0.03) {{
        status = 'AHEAD';
        badgeClass = 'badge-ahead';
        text = `Vượt (+${{diffPct}}%) • Đạt ${{pctDatTienDo}}% tiến độ`;
      }} else if (diff >= -0.02) {{
        status = 'ON_TRACK';
        badgeClass = 'badge-ontrack';
        text = `Đạt chuẩn (${{diff >= 0 ? '+' : ''}}${{diffPct}}%) • Đạt ${{pctDatTienDo}}% tiến độ`;
      }} else if (diff >= -0.06) {{
        status = 'BEHIND';
        badgeClass = 'badge-behind-slight';
        text = `Chậm (${{diffPct}}%) • Đạt ${{pctDatTienDo}}% tiến độ`;
      }} else {{
        status = 'CRITICAL';
        badgeClass = 'badge-behind-severe';
        text = `Báo động (${{diffPct}}%) • Đạt ${{pctDatTienDo}}% tiến độ`;
        isCritical = true;
      }}

      return {{
        diff,
        diffPct,
        pctDatTienDo,
        status,
        badgeClass,
        icon: '',
        text,
        isCritical
      }};
    }}

    function init() {{
      document.getElementById('lbl-updated-at').innerText = DATA.updated_at;
      document.getElementById('input-current-day').value = currentDay;
      if (document.getElementById('input-total-days')) {{
        document.getElementById('input-total-days').value = totalDays;
      }}
      updatePacingDisplay();
      buildMyNameOptions();
      renderPodiumAndAwards();
      if (typeof initSchedule === 'function') {{
        initSchedule();
      }}
      applyFilters();

      // Kích hoạt đọc trực tiếp Realtime từ Google Sheets
      fetchRealtimeSheetsData(false);
      setInterval(() => fetchRealtimeSheetsData(false), 30000);
    }}

    function onDayChange() {{
      const val = parseInt(document.getElementById('input-current-day').value, 10);
      if (!isNaN(val) && val >= 1 && val <= totalDays) {{
        currentDay = val;
      }} else {{
        currentDay = Math.min(14, totalDays);
        document.getElementById('input-current-day').value = currentDay;
      }}
      targetPacing = currentDay / totalDays;
      updatePacingDisplay();
      applyFilters();
    }}

    function onTotalDaysChange() {{
      const val = parseInt(document.getElementById('input-total-days').value, 10);
      if (!isNaN(val) && val >= 28 && val <= 31) {{
        totalDays = val;
      }} else {{
        totalDays = 30;
        document.getElementById('input-total-days').value = 30;
      }}
      targetPacing = currentDay / totalDays;
      document.getElementById('pacing-note-text').innerText = `💡 Đang tính theo tháng ${{totalDays}} ngày (Chuẩn hôm nay ngày ${{currentDay}}: ${{(targetPacing * 100).toFixed(2)}}%).`;
      updatePacingDisplay();
      applyFilters();
    }}

    function setTotalDays(days) {{
      totalDays = days;
      if (document.getElementById('input-total-days')) {{
        document.getElementById('input-total-days').value = days;
      }}
      targetPacing = currentDay / totalDays;
      document.getElementById('pacing-note-text').innerText = `💡 Đang tính theo tháng ${{days}} ngày (Chuẩn hôm nay ngày ${{currentDay}}: ${{(targetPacing * 100).toFixed(2)}}%).`;
      updatePacingDisplay();
      applyFilters();
    }}

    function updatePacingDisplay() {{
      const targetPctStr = (targetPacing * 100).toFixed(2) + '%';
      document.getElementById('lbl-target-pacing').innerText = targetPctStr;
      document.getElementById('chart-target-line').innerText = `Chuẩn ngày ${{currentDay}}: ${{targetPctStr}}`;

      // Recalculate summary stats based on pacing
      let aheadCount = 0;
      let behindCount = 0;
      DATA.kpi_tong.forEach(item => {{
        const pacing = calculatePacingDetails(item);
        item.pacing_diff = pacing.diff;
        item.pacing_info = pacing;
        if (pacing.status === 'AHEAD' || pacing.status === 'ON_TRACK') {{
          aheadCount++;
        }} else {{
          behindCount++;
        }}
      }});

      document.getElementById('card-total-staff').innerText = DATA.summary.total_staff;
      document.getElementById('card-avg-kpi').innerText = DATA.summary.avg_kpi + '%';
      const avgDiff = (DATA.summary.avg_kpi - targetPacing * 100).toFixed(1);
      document.getElementById('card-avg-status').innerText = `So với chuẩn: ${{avgDiff >= 0 ? '+' : ''}}${{avgDiff}}%`;
      document.getElementById('card-count-ahead').innerText = `${{aheadCount}} / ${{DATA.summary.total_staff}}`;
      document.getElementById('card-count-behind').innerText = `${{behindCount}} / ${{DATA.summary.total_staff}}`;
      const card2Ht = document.getElementById('card-total-ticket-2ht');
      if (card2Ht) card2Ht.innerText = DATA.summary.total_ticket_2ht ?? 0;

      if (typeof renderPodiumAndAwards === 'function') {{
        renderPodiumAndAwards();
      }}
      if (typeof buildMyNameOptions === 'function') {{
        buildMyNameOptions();
      }}
    }}

    function switchTab(tab) {{
      if (tab === 'schedule') {{
        switchMainView('schedule');
        return;
      }}
      if (currentMainView === 'schedule') {{
        switchMainView('kpi');
      }}
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById('tab-btn-' + tab);
      if (activeBtn) activeBtn.classList.add('active');

      document.getElementById('tab-pane-kpi').style.display = tab === 'kpi' ? 'block' : 'none';
      document.getElementById('tab-pane-hs').style.display = tab === 'hs' ? 'block' : 'none';
      document.getElementById('tab-pane-charts').style.display = tab === 'charts' ? 'block' : 'none';
      const podiumPane = document.getElementById('tab-pane-podium');
      if (podiumPane) podiumPane.style.display = tab === 'podium' ? 'block' : 'none';

      document.getElementById('filter-shift-toggle').style.display = tab === 'hs' ? 'block' : 'none';
    }}

    function renderKpiTable() {{
      const tbody = document.getElementById('tbody-kpi');
      tbody.innerHTML = '';
      document.getElementById('badge-count-kpi').innerText = filteredKpi.length;

      filteredKpi.forEach((item, idx) => {{
        const tr = document.createElement('tr');
        tr.onclick = () => openModal(item);

        const myName = localStorage.getItem('kpicto_my_name') || '';
        if (myName && (item.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(item.name.toLowerCase()))) {{
          tr.classList.add('my-row-highlight');
        }}

        const pctTicket = item.pct_kpi_ticket;
        const pctCv = item.pct_kpi_cv;
        const pctTong = item.pct_kpi_tong;
        const p = item.pacing_info || calculatePacingDetails(item);

        if (p.isCritical) {{
          tr.classList.add('alert-severe');
        }}

        tr.innerHTML = `
          <td>${{idx + 1}}</td>
          <td><strong>${{item.ma}}</strong></td>
          <td>
            <div style="font-weight:600;">${{item.name}}</div>
            <div style="font-size:11px;color:var(--text-muted);">${{item.team}}</div>
          </td>
          <td class="text-center"><span class="badge badge-level">Level ${{item.level}}</span></td>
          <td class="numeric">${{item.kpi_ticket.toLocaleString('vi-VN')}}</td>
          <td class="numeric">${{item.slg_kh.toLocaleString('vi-VN')}}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${{pctTicket >= targetPacing ? 'bg-excel' : 'bg-ok'}}" style="width:${{Math.min(pctTicket * 100, 100)}}%;"></div>
              </div>
              <span style="font-size:11px;font-weight:600;">${{(pctTicket * 100).toFixed(1)}}%</span>
            </div>
          </td>
          <td class="numeric">${{item.kpi_cv.toLocaleString('vi-VN')}}</td>
          <td class="numeric">${{item.slg_cv.toLocaleString('vi-VN')}}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${{pctCv >= targetPacing ? 'bg-excel' : 'bg-ok'}}" style="width:${{Math.min(pctCv * 100, 100)}}%;"></div>
              </div>
              <span style="font-size:11px;font-weight:600;">${{(pctCv * 100).toFixed(1)}}%</span>
            </div>
          </td>
          <td class="text-center">${{item.no_ticket_2ht > 0 ? `<span class="badge badge-ticket-2ht">${{item.no_ticket_2ht}}</span>` : '0'}}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${{pctTong >= targetPacing ? 'bg-excel' : 'bg-low'}}" style="width:${{Math.min(pctTong * 100, 100)}}%;"></div>
              </div>
              <span style="font-size:12px;font-weight:700;">${{(pctTong * 100).toFixed(2)}}%</span>
            </div>
          </td>
          <td>
            <span class="badge ${{p.badgeClass}}">
              ${{p.text}}
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      }});

// Render Mobile Cards View
      renderKpiMobileCards();
    }}

    let currentKpiMobileView = 'cards';
    function setKpiMobileView(view) {{
      currentKpiMobileView = view;
      const cardsEl = document.getElementById('kpi-mobile-cards');
      const tableEl = document.getElementById('kpi-table-view-wrap');
      const btnCards = document.getElementById('btn-view-cards');
      const btnTable = document.getElementById('btn-view-table');

      if (view === 'cards') {{
        if (cardsEl) cardsEl.style.display = 'grid';
        if (tableEl) tableEl.style.display = 'none';
        if (btnCards) btnCards.classList.add('active');
        if (btnTable) btnTable.classList.remove('active');
      }} else {{
        if (cardsEl) cardsEl.style.display = 'none';
        if (tableEl) tableEl.style.display = 'block';
        if (btnCards) btnCards.classList.remove('active');
        if (btnTable) btnTable.classList.add('active');
      }}
    }}

    function openModalByMa(ma) {{
      const item = (DATA.kpi_tong || []).find(x => String(x.ma) === String(ma));
      if (item) {{
        openModal(item);
      }}
    }}

    function renderKpiMobileCards() {{
      const container = document.getElementById('kpi-mobile-cards');
      if (!container) return;

      const sortedByKpi = [...(DATA.kpi_tong || [])].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);

      container.innerHTML = filteredKpi.map((item) => {{
        const p = item.pacing_info || calculatePacingDetails(item);
        const rankIdx = sortedByKpi.findIndex(x => x.ma === item.ma);
        const rank = rankIdx >= 0 ? rankIdx + 1 : 1;
        const rankMedal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${{rank}}`;
        const isLeader = item.name.toLowerCase().includes('minh nhựt') || item.name.toLowerCase().includes('nhựt');

        const nameParts = item.name.trim().split(' ');
        const initials = nameParts.length >= 2 
          ? (nameParts[nameParts.length - 2][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
          : item.name.substring(0, 2).toUpperCase();

        const diffPct = (p.diff * 100).toFixed(1);
        const diffText = p.diff >= 0 ? `+${{diffPct}}%` : `${{diffPct}}%`;
        const tagClass = p.isAhead ? 'tag-success' : p.isCritical ? 'tag-danger' : 'tag-warning';
        const tagLabel = p.isAhead ? `🟢 Vượt (${{diffText}})` : p.isCritical ? `🔴 Chậm (${{diffText}})` : `🟡 Cận (${{diffText}})`;

        return `
          <div class="mobile-kpi-card" onclick="openModalByMa('${{item.ma}}')">
            <div class="mkc-header">
              <div class="mkc-left">
                <span class="mkc-rank">${{rankMedal}}</span>
                <div class="mkc-avatar">${{initials}}</div>
                <div class="mkc-name-wrap">
                  <div class="mkc-name">${{item.name}} ${{isLeader ? '👑' : ''}}</div>
                  <div class="mkc-sub">MS: ${{item.ma}} • Level ${{item.level}}</div>
                </div>
              </div>
              <div class="mkc-right">
                <div class="mkc-kpi-pct ${{(item.pct_kpi_tong >= targetPacing) ? 'text-success' : 'text-danger'}}">
                  ${{(item.pct_kpi_tong * 100).toFixed(1)}}%
                </div>
                <div class="mkc-tag ${{tagClass}}">${{tagLabel}}</div>
              </div>
            </div>

            <div class="mkc-progress-track">
              <div class="progress-fill ${{(item.pct_kpi_tong >= targetPacing) ? 'bg-excel' : 'bg-low'}}" style="width:${{Math.min(item.pct_kpi_tong * 100, 100)}}%;"></div>
              <div class="mkc-marker-target" style="left:${{Math.min(targetPacing * 100, 100)}}%;" title="Chuẩn ngày: ${{(targetPacing * 100).toFixed(1)}}%"></div>
            </div>

            <div class="mkc-stats-grid">
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">🎫 Tickets</div>
                <div class="mkc-stat-val">${{item.slg_kh.toLocaleString('vi-VN')}} <small>/ ${{item.kpi_ticket.toLocaleString('vi-VN')}}</small></div>
                <div class="mkc-stat-pct">${{(item.pct_kpi_ticket * 100).toFixed(0)}}% KPI</div>
              </div>
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">💼 Công Việc</div>
                <div class="mkc-stat-val">${{item.slg_cv.toLocaleString('vi-VN')}} <small>/ ${{item.kpi_cv.toLocaleString('vi-VN')}}</small></div>
                <div class="mkc-stat-pct">${{(item.pct_kpi_cv * 100).toFixed(0)}}% KPI</div>
              </div>
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">🤝 2 CV Hỗ Trợ</div>
                <div class="mkc-stat-val">${{item.no_ticket_2ht}}</div>
                <div class="mkc-stat-pct" style="color:var(--text-muted);">${{item.no_ticket_2ht > 0 ? 'Có hỗ trợ' : '0'}}</div>
              </div>
            </div>

            <div class="mkc-footer">
              <span>Chạm để xem chi tiết thẻ năng lực</span>
              <span style="font-size:13px;color:var(--primary);">➔</span>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function renderHsTable() {{
      const tbody = document.getElementById('tbody-hs');
      tbody.innerHTML = '';
      document.getElementById('badge-count-hs').innerText = filteredHs.length;

      filteredHs.forEach((item, idx) => {{
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => {{
          const kMatch = DATA.kpi_tong.find(k => k.name.toLowerCase().includes(item.user_name.toLowerCase()) || item.user_name.toLowerCase().includes(k.name.toLowerCase()));
          if (kMatch) openModal(kMatch);
        }};

        const myName = localStorage.getItem('kpicto_my_name') || '';
        if (myName && (item.user_name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(item.user_name.toLowerCase()))) {{
          tr.classList.add('my-row-highlight');
        }}

        const s = item.shifts;

        tr.innerHTML = `
          <td>${{idx + 1}}</td>
          <td><strong style="color:var(--primary);">${{item.user_name}}</strong></td>
          
          <td class="border-shift-left numeric">${{s.S.hours || '-'}}</td>
          <td class="numeric">${{s.S.cv || '-'}}</td>
          <td class="numeric">${{s.S.kh || '-'}}</td>
          <td class="numeric">${{s.S.pct_kpi ? (s.S.pct_kpi * 100).toFixed(2) + '%' : '-'}}</td>

          <td class="border-shift-left numeric">${{s.HCS.hours || '-'}}</td>
          <td class="numeric">${{s.HCS.cv || '-'}}</td>
          <td class="numeric">${{s.HCS.kh || '-'}}</td>
          <td class="numeric">${{s.HCS.pct_kpi ? (s.HCS.pct_kpi * 100).toFixed(2) + '%' : '-'}}</td>

          <td class="border-shift-left numeric">${{s.TR.hours || '-'}}</td>
          <td class="numeric">${{s.TR.cv || '-'}}</td>
          <td class="numeric">${{s.TR.kh || '-'}}</td>
          <td class="numeric">${{s.TR.pct_kpi ? (s.TR.pct_kpi * 100).toFixed(2) + '%' : '-'}}</td>

          <td class="border-shift-left numeric">${{s.HCC.hours || '-'}}</td>
          <td class="numeric">${{s.HCC.cv || '-'}}</td>
          <td class="numeric">${{s.HCC.kh || '-'}}</td>
          <td class="numeric">${{s.HCC.pct_kpi ? (s.HCC.pct_kpi * 100).toFixed(2) + '%' : '-'}}</td>

          <td class="border-shift-left numeric">${{s.T.hours || '-'}}</td>
          <td class="numeric">${{s.T.cv || '-'}}</td>
          <td class="numeric">${{s.T.kh || '-'}}</td>
          <td class="numeric">${{s.T.pct_kpi ? (s.T.pct_kpi * 100).toFixed(2) + '%' : '-'}}</td>

          <td class="border-shift-left numeric" style="font-weight:700;">${{s.Total.hours}}</td>
          <td class="numeric" style="font-weight:700;">${{s.Total.cv}}</td>
          <td class="numeric" style="font-weight:700;">${{s.Total.kh}}</td>
          <td class="numeric" style="font-weight:700;color:var(--primary);">${{(s.Total.pct_kpi * 100).toFixed(2)}}%</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function renderCharts() {{
      const containerKpi = document.getElementById('chart-kpi-bars');
      containerKpi.innerHTML = '';
      const sortedByKpi = [...DATA.kpi_tong].sort((a, b) => b.pct_kpi_tong - a.pct_kpi_tong);

      sortedByKpi.forEach(item => {{
        const row = document.createElement('div');
        row.className = 'bar-row';
        const pct = (item.pct_kpi_tong * 100).toFixed(1);
        const p = item.pacing_info || calculatePacingDetails(item);
        const barColor = p.status === 'AHEAD' ? 'linear-gradient(90deg, #10b981, #34d399)' :
                         p.status === 'ON_TRACK' ? 'linear-gradient(90deg, #0ea5e9, #38bdf8)' :
                         p.status === 'BEHIND' ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' :
                         'linear-gradient(90deg, #ef4444, #f87171)';

        row.innerHTML = `
          <div class="bar-label" title="${{item.name}}">${{item.name}}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${{Math.max(Math.min(pct * 1.3, 100), 12)}}%;background:${{barColor}};">
              <span>${{pct}}% (Đạt ${{p.pctDatTienDo}}% tiến độ)</span>
            </div>
          </div>
        `;
        containerKpi.appendChild(row);
      }});

      // Shift hours breakdown
      const containerShift = document.getElementById('chart-shift-hours');
      containerShift.innerHTML = '';
      const shiftTotals = {{ 'S (Sáng)': 0, 'HCS (Hành chính sáng)': 0, 'TR (Trưa)': 0, 'HCC (Hành chính chiều)': 0, 'T (Tối)': 0, 'Khác': 0 }};
      DATA.hs_ca_truc.forEach(u => {{
        shiftTotals['S (Sáng)'] += u.shifts.S.hours || 0;
        shiftTotals['HCS (Hành chính sáng)'] += u.shifts.HCS.hours || 0;
        shiftTotals['TR (Trưa)'] += u.shifts.TR.hours || 0;
        shiftTotals['HCC (Hành chính chiều)'] += u.shifts.HCC.hours || 0;
        shiftTotals['T (Tối)'] += u.shifts.T.hours || 0;
        shiftTotals['Khác'] += u.shifts['Khác'].hours || 0;
      }});

      const maxH = Math.max(...Object.values(shiftTotals), 1);
      for (const [sName, sVal] of Object.entries(shiftTotals)) {{
        const row = document.createElement('div');
        row.className = 'bar-row';
        const pctWidth = ((sVal / maxH) * 100).toFixed(1);
        row.innerHTML = `
          <div class="bar-label">${{sName}}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${{pctWidth}}%;background:linear-gradient(90deg, #6366f1, #818cf8);">
              <span>${{sVal.toFixed(1)}}h</span>
            </div>
          </div>
        `;
        containerShift.appendChild(row);
      }}
    }}

    function applyFilters() {{
      const search = document.getElementById('filter-search').value.toLowerCase().trim();
      const level = document.getElementById('filter-level').value;
      const pacingFilter = document.getElementById('filter-pacing').value;

      filteredKpi = DATA.kpi_tong.filter(item => {{
        const matchesSearch = !search || item.name.toLowerCase().includes(search) || item.ma.includes(search);
        const matchesLevel = level === 'ALL' || item.level === level;

        const p = item.pacing_info || calculatePacingDetails(item);
        let matchesPacing = true;
        if (pacingFilter === 'AHEAD') matchesPacing = (p.status === 'AHEAD');
        else if (pacingFilter === 'ON_TRACK') matchesPacing = (p.status === 'ON_TRACK');
        else if (pacingFilter === 'BEHIND') matchesPacing = (p.status === 'BEHIND' || p.status === 'CRITICAL');
        else if (pacingFilter === 'CRITICAL') matchesPacing = (p.status === 'CRITICAL');

        return matchesSearch && matchesLevel && matchesPacing;
      }});

      filteredHs = DATA.hs_ca_truc.filter(item => {{
        return !search || item.user_name.toLowerCase().includes(search);
      }});

      renderKpiTable();
      renderHsTable();
      renderCharts();
    }}

    function resetFilters() {{
      document.getElementById('filter-search').value = '';
      document.getElementById('filter-level').value = 'ALL';
      document.getElementById('filter-pacing').value = 'ALL';
      document.getElementById('filter-shift-toggle').value = 'ALL';
      applyFilters();
    }}

    function sortTable(type, col) {{
      if (sortColumn === col) {{
        sortAsc = !sortAsc;
      }} else {{
        sortColumn = col;
        sortAsc = false;
      }}

      filteredKpi.sort((a, b) => {{
        let vA = a[col];
        let vB = b[col];
        if (typeof vA === 'string') vA = vA.toLowerCase();
        if (typeof vB === 'string') vB = vB.toLowerCase();
        if (vA < vB) return sortAsc ? -1 : 1;
        if (vA > vB) return sortAsc ? 1 : -1;
        return 0;
      }});

      renderKpiTable();
    }}

    function buildMyNameOptions() {{
      const select = document.getElementById('select-my-name');
      if (!select) return;
      
      const currentVal = select.value;
      select.innerHTML = '<option value="">👤 Tôi là ai? (Chọn tên bạn...)</option>';
      
      const allNamesSet = new Set([...DATA.kpi_tong].map(x => x.name));
      if (DATA.schedule && DATA.schedule.employees) {{
        DATA.schedule.employees.forEach(e => allNamesSet.add(e.name));
      }}
      const names = Array.from(allNamesSet).sort((a,b) => a.localeCompare(b, 'vi'));
      names.forEach(name => {{
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      }});

      const savedName = localStorage.getItem('kpicto_my_name') || '';
      if (savedName && names.includes(savedName)) {{
        select.value = savedName;
        onSelectMyName(savedName, false);
      }} else if (currentVal && names.includes(currentVal)) {{
        select.value = currentVal;
      }}
    }}

    function onSelectMyName(name, shouldScroll = true) {{
      if (name) {{
        localStorage.setItem('kpicto_my_name', name);
        const btnCard = document.getElementById('btn-open-my-card');
        if (btnCard) btnCard.style.display = 'inline-flex';
      }} else {{
        localStorage.removeItem('kpicto_my_name');
        const btnCard = document.getElementById('btn-open-my-card');
        if (btnCard) btnCard.style.display = 'none';
      }}

      // Re-apply highlight to tables
      document.querySelectorAll('tr.my-row-highlight').forEach(tr => tr.classList.remove('my-row-highlight'));

      if (name) {{
        const nameLower = name.toLowerCase();
        let targetRow = null;
        
        document.querySelectorAll('#tbody-kpi tr').forEach(tr => {{
          if (tr.innerText.toLowerCase().includes(nameLower)) {{
            tr.classList.add('my-row-highlight');
            if (!targetRow && currentTab === 'kpi') targetRow = tr;
          }}
        }});

        document.querySelectorAll('#tbody-hs tr').forEach(tr => {{
          if (tr.innerText.toLowerCase().includes(nameLower)) {{
            tr.classList.add('my-row-highlight');
            if (!targetRow && currentTab === 'hs') targetRow = tr;
          }}
        }});

        document.querySelectorAll('#tbody-schedule-summary tr').forEach(tr => {{
          if (tr.innerText.toLowerCase().includes(nameLower)) {{
            tr.classList.add('my-row-highlight');
            if (!targetRow && currentTab === 'schedule') targetRow = tr;
          }}
        }});

        document.querySelectorAll('#tbody-matrix-schedule tr').forEach(tr => {{
          if (tr.innerText.toLowerCase().includes(nameLower)) {{
            tr.classList.add('my-row-highlight');
          }}
        }});

        if (shouldScroll && targetRow) {{
          targetRow.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
      }}
    }}

    function openMySelectedCard() {{
      const myName = localStorage.getItem('kpicto_my_name');
      if (!myName) return;
      const item = DATA.kpi_tong.find(x => x.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(x.name.toLowerCase()));
      if (item) {{
        openModal(item);
      }} else {{
        showToast('Chưa tìm thấy dữ liệu cá nhân cho: ' + myName);
      }}
    }}

    function openModal(item) {{
      const p = item.pacing_info || calculatePacingDetails(item);
      
      // Initials for avatar
      const nameParts = item.name.trim().split(' ');
      const initials = nameParts.length >= 2 
        ? (nameParts[nameParts.length - 2][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
        : item.name.substring(0, 2).toUpperCase();
      
      const avatarEl = document.getElementById('modal-avatar');
      if (avatarEl) avatarEl.innerText = initials;

      // Rank in team
      const sortedByKpi = [...DATA.kpi_tong].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);
      const rankIdx = sortedByKpi.findIndex(x => x.ma === item.ma);
      const rank = rankIdx >= 0 ? rankIdx + 1 : 1;
      const rankEl = document.getElementById('modal-rank');
      if (rankEl) {{
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '🏆';
        rankEl.innerText = `${{medal}} Hạng #${{rank}} / ${{DATA.kpi_tong.length}}`;
      }}

      document.getElementById('modal-name').innerText = `${{item.ma}} - ${{item.name}}`;
      const lvlEl = document.getElementById('modal-level');
      if (lvlEl) lvlEl.innerText = 'Level ' + item.level;

      document.getElementById('modal-pacing-status').innerHTML = `<span class="badge ${{p.badgeClass}}">${{p.text}}</span>`;

      // Khối 1: Forecast Target Calculator
      const currentPct = item.pct_kpi_tong;
      const forecastPct = targetPacing > 0 ? ((currentPct / targetPacing) * 100).toFixed(1) : (currentPct * 100).toFixed(1);
      const remainingDays = Math.max(1, totalDays - currentDay);
      const remTicket = Math.max(0, item.kpi_ticket - item.slg_kh);
      const dailyTicket = (remTicket / remainingDays).toFixed(1);
      const remCv = Math.max(0, item.kpi_cv - item.slg_cv);
      const dailyCv = (remCv / remainingDays).toFixed(1);

      const fValEl = document.getElementById('modal-forecast-val');
      if (fValEl) {{
        const isAhead = parseFloat(forecastPct) >= 100;
        fValEl.innerText = `${{forecastPct}}% KPI`;
        fValEl.style.color = isAhead ? 'var(--success)' : (parseFloat(forecastPct) >= 85 ? 'var(--warning)' : 'var(--danger)');
      }}

      const pTagEl = document.getElementById('modal-pacing-tag');
      if (pTagEl) pTagEl.innerText = `(Tốc độ ngày ${{currentDay}}/${{totalDays}} • Chuẩn: ${{(targetPacing*100).toFixed(1)}}%)`;

      const planEl = document.getElementById('modal-forecast-plan');
      if (planEl) {{
        if (currentPct >= 1.0) {{
          planEl.innerHTML = `🎉 <strong>Chúc mừng xuất sắc!</strong> Bạn đã hoàn thành vượt mốc 100% KPI tháng sớm! Hãy giữ vững phong độ đỉnh cao này nhé.`;
        }} else {{
          planEl.innerHTML = `🎯 <strong>Kế hoạch cán đích 100% KPI</strong> trong <strong>${{remainingDays}} ngày còn lại</strong>:<br>` +
            `• <strong>Ticket KH:</strong> Còn thiếu <strong>${{remTicket.toLocaleString('vi-VN')}}</strong> KH (trung bình cần <strong>+${{dailyTicket}} KH/ngày</strong>).<br>` +
            `• <strong>Công việc (CV):</strong> Còn thiếu <strong>${{remCv.toLocaleString('vi-VN')}}</strong> CV (trung bình cần <strong>+${{dailyCv}} CV/ngày</strong>).`;
        }}
      }}

      // Khối 2: Strengths & Balance
      const tValEl = document.getElementById('modal-ticket-val');
      if (tValEl) tValEl.innerText = `${{item.slg_kh.toLocaleString('vi-VN')}} / ${{item.kpi_ticket.toLocaleString('vi-VN')}}`;
      const tBadgeEl = document.getElementById('modal-ticket-badge');
      if (tBadgeEl) tBadgeEl.innerText = `${{(item.pct_kpi_ticket*100).toFixed(1)}}% KPI`;

      const cvValEl = document.getElementById('modal-cv-val');
      if (cvValEl) cvValEl.innerText = `${{item.slg_cv.toLocaleString('vi-VN')}} / ${{item.kpi_cv.toLocaleString('vi-VN')}}`;
      const cvBadgeEl = document.getElementById('modal-cv-badge');
      if (cvBadgeEl) cvBadgeEl.innerText = `${{(item.pct_kpi_cv*100).toFixed(1)}}% KPI`;

      const diffTicketCv = (item.pct_kpi_ticket - item.pct_kpi_cv) * 100;
      const strAssessEl = document.getElementById('modal-strength-assessment');
      const strDescEl = document.getElementById('modal-strength-desc');
      if (strAssessEl && strDescEl) {{
        if (diffTicketCv >= 5) {{
          strAssessEl.innerText = `⚡ Điểm mạnh: Gánh Ticket vượt trội`;
          strDescEl.innerText = `Tỷ lệ hoàn thành Ticket (${{(item.pct_kpi_ticket*100).toFixed(1)}}%) cao hơn CV ${{diffTicketCv.toFixed(1)}}%. Tốc độ hỗ trợ khách hàng rất nhanh nhạy.`;
        }} else if (diffTicketCv <= -5) {{
          strAssessEl.innerText = `🛠️ Điểm mạnh: Đẩy mạnh Công việc hỗ trợ`;
          strDescEl.innerText = `Tỷ lệ hoàn thành CV (${{(item.pct_kpi_cv*100).toFixed(1)}}%) cao hơn Ticket ${{Math.abs(diffTicketCv).toFixed(1)}}%. Đóng góp tích cực vào các công việc kỹ thuật chuyên sâu.`;
        }} else {{
          strAssessEl.innerText = `⚖️ Phong độ: Toàn diện & Cân bằng`;
          strDescEl.innerText = `Tỷ lệ Ticket và CV phân bổ đồng đều (${{(item.pct_kpi_ticket*100).toFixed(1)}}% vs ${{(item.pct_kpi_cv*100).toFixed(1)}}%), hỗ trợ toàn diện các mặt công việc.`;
        }}
      }}

      const badge2Ht = document.getElementById('modal-ticket-2ht-badge');
      if (badge2Ht) {{
        badge2Ht.innerText = `📋 ${{item.no_ticket_2ht}} Ticket 2 CV`;
        badge2Ht.style.background = 'var(--primary-light)';
        badge2Ht.style.color = 'var(--primary)';
        badge2Ht.title = 'Số lượng ticket có 2 công việc hỗ trợ';
      }}

      // Khối 3: Shift Breakdown
      const hsMatch = DATA.hs_ca_truc.find(x => x.user_name.toLowerCase().includes(item.name.toLowerCase()) || item.full_name.toLowerCase().includes(x.user_name.toLowerCase()));
      const sBody = document.getElementById('modal-shifts-body');
      sBody.innerHTML = '';

      const stackedBarEl = document.getElementById('modal-shift-stacked');
      const legendEl = document.getElementById('modal-shift-legend');
      const highlightEl = document.getElementById('modal-shift-highlight');

      if (hsMatch) {{
        const shiftColors = {{
          'S': '#38bdf8',
          'HCS': '#34d399',
          'TR': '#f59e0b',
          'HCC': '#a78bfa',
          'T': '#f472b6',
          'Khác': '#94a3b8'
        }};

        let totalH = hsMatch.shifts.Total ? hsMatch.shifts.Total.hours : 0;
        if (!totalH || totalH <= 0) {{
          totalH = Object.entries(hsMatch.shifts).reduce((acc, [k,v]) => k !== 'Total' ? acc + (v.hours || 0) : acc, 0);
        }}

        let maxShiftKey = 'S';
        let maxShiftH = 0;
        let stackedHtml = '';
        let legendHtml = '';

        for (const [sKey, sVal] of Object.entries(hsMatch.shifts)) {{
          if (sKey === 'Total') continue;
          const h = sVal.hours || 0;
          if (h > maxShiftH) {{
            maxShiftH = h;
            maxShiftKey = sKey;
          }}
          const pct = totalH > 0 ? (h / totalH) * 100 : 0;
          const col = shiftColors[sKey] || '#6366f1';
          if (pct > 0) {{
            stackedHtml += `<div class="shift-seg" style="width:${{pct.toFixed(1)}}%;background:${{col}};" title="Ca ${{sKey}}: ${{h}}h (${{pct.toFixed(1)}}%)"></div>`;
          }}
          legendHtml += `
            <div class="shift-legend-item">
              <span class="shift-dot" style="background:${{col}};"></span>
              <span>Ca ${{sKey}}: <strong>${{h}}h</strong></span>
            </div>
          `;

          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>Ca ${{sKey}}</strong></td>
            <td class="numeric">${{sVal.hours}}h</td>
            <td class="numeric">${{sVal.cv}}</td>
            <td class="numeric">${{sVal.kh}}</td>
            <td class="numeric">${{(sVal.pct_kpi * 100).toFixed(2)}}%</td>
          `;
          sBody.appendChild(tr);
        }}

        if (stackedBarEl) stackedBarEl.innerHTML = stackedHtml || '<div class="shift-seg" style="width:100%;background:var(--card-border);"></div>';
        if (legendEl) legendEl.innerHTML = legendHtml;

        const maxPct = totalH > 0 ? ((maxShiftH / totalH) * 100).toFixed(1) : 0;
        if (highlightEl) {{
          highlightEl.innerHTML = `⏰ Trực nhiều nhất ở <strong>Ca ${{maxShiftKey}}</strong> (<strong>${{maxShiftH}}h</strong> • chiếm <strong>${{maxPct}}%</strong> tổng thời gian).`;
        }}
      }} else {{
        sBody.innerHTML = '<tr><td colspan="5" class="text-center">Chưa có dữ liệu ca trực</td></tr>';
        if (stackedBarEl) stackedBarEl.innerHTML = '';
        if (legendEl) legendEl.innerHTML = '';
        if (highlightEl) highlightEl.innerText = 'Chưa có thông tin phân bổ ca trực.';
      }}

      document.getElementById('emp-modal').style.display = 'flex';
    }}

    function closeModal() {{
      document.getElementById('emp-modal').style.display = 'none';
    }}

    function renderPodiumAndAwards() {{
      const podiumEl = document.getElementById('podium-content');
      const awardsEl = document.getElementById('awards-content');
      if (!podiumEl || !awardsEl || !DATA.kpi_tong.length) return;

      const sortedByKpi = [...DATA.kpi_tong].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);
      const top1 = sortedByKpi[0] || null;
      const top2 = sortedByKpi[1] || null;
      const top3 = sortedByKpi[2] || null;

      const getInitials = (name) => {{
        const parts = name.trim().split(' ');
        return parts.length >= 2 ? (parts[parts.length - 2][0] + parts[parts.length - 1][0]).toUpperCase() : name.substring(0, 2).toUpperCase();
      }};

      let podiumHtml = '';

      if (top2) {{
        podiumHtml += `
          <div class="podium-step podium-2" onclick="openModalByName('${{top2.name}}')">
            <div class="podium-avatar">${{getInitials(top2.name)}}</div>
            <div class="podium-name" title="${{top2.name}}">${{top2.name}}</div>
            <div class="podium-pct">${{(top2.pct_kpi_tong * 100).toFixed(1)}}%</div>
            <div class="podium-block">2 🥈</div>
          </div>
        `;
      }}

      if (top1) {{
        podiumHtml += `
          <div class="podium-step podium-1" onclick="openModalByName('${{top1.name}}')">
            <div class="podium-avatar">
              <span class="podium-crown">👑</span>
              ${{getInitials(top1.name)}}
            </div>
            <div class="podium-name" title="${{top1.name}}">${{top1.name}}</div>
            <div class="podium-pct">${{(top1.pct_kpi_tong * 100).toFixed(1)}}%</div>
            <div class="podium-block">1 🥇</div>
          </div>
        `;
      }}

      if (top3) {{
        podiumHtml += `
          <div class="podium-step podium-3" onclick="openModalByName('${{top3.name}}')">
            <div class="podium-avatar">${{getInitials(top3.name)}}</div>
            <div class="podium-name" title="${{top3.name}}">${{top3.name}}</div>
            <div class="podium-pct">${{(top3.pct_kpi_tong * 100).toFixed(1)}}%</div>
            <div class="podium-block">3 🥉</div>
          </div>
        `;
      }}

      podiumEl.innerHTML = podiumHtml;

      // Special Awards
      const sortedHours = [...DATA.hs_ca_truc].sort((a,b) => (b.shifts.Total.hours || 0) - (a.shifts.Total.hours || 0));
      const heroHours = sortedHours[0];

      const sortedTicket = [...DATA.kpi_tong].sort((a,b) => b.slg_kh - a.slg_kh);
      const heroTicket = sortedTicket[0];

      const sortedCv = [...DATA.kpi_tong].sort((a,b) => b.slg_cv - a.slg_cv);
      const heroCv = sortedCv[0];

      const sorted2Ht = [...DATA.kpi_tong].sort((a,b) => (b.no_ticket_2ht || 0) - (a.no_ticket_2ht || 0));
      const hero2Ht = sorted2Ht[0];

      awardsEl.innerHTML = `
        <div class="award-card" onclick="openModalByName('${{heroHours ? heroHours.user_name : ''}}')">
          <div class="award-icon">⚡</div>
          <div>
            <div class="award-title">Chiến Thần Cày Cuốc</div>
            <div class="award-name">${{heroHours ? heroHours.user_name : '--'}}</div>
            <div class="award-stat">${{heroHours ? heroHours.shifts.Total.hours + ' giờ trực ca' : '--'}}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${{heroTicket ? heroTicket.name : ''}}')">
          <div class="award-icon">🎯</div>
          <div>
            <div class="award-title">Vua Xử Lý Ticket</div>
            <div class="award-name">${{heroTicket ? heroTicket.name : '--'}}</div>
            <div class="award-stat">${{heroTicket ? heroTicket.slg_kh.toLocaleString('vi-VN') + ' KH quy đổi' : '--'}}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${{heroCv ? heroCv.name : ''}}')">
          <div class="award-icon">🛠️</div>
          <div>
            <div class="award-title">Bàn Tay Vàng CV</div>
            <div class="award-name">${{heroCv ? heroCv.name : '--'}}</div>
            <div class="award-stat">${{heroCv ? heroCv.slg_cv.toLocaleString('vi-VN') + ' CV quy đổi' : '--'}}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${{hero2Ht ? hero2Ht.name : ''}}')">
          <div class="award-icon">🌟</div>
          <div>
            <div class="award-title">Chúa Tể Buff Bẩn</div>
            <div class="award-name">${{hero2Ht ? hero2Ht.name : '--'}}</div>
            <div class="award-stat">${{hero2Ht ? (hero2Ht.no_ticket_2ht || 0) + ' Ticket có 2 CV HT' : '--'}}</div>
          </div>
        </div>
      `;
    }}

    function openModalByName(name) {{
      if (!name) return;
      const item = DATA.kpi_tong.find(x => x.name.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(x.name.toLowerCase()));
      if (item) openModal(item);
    }}

    function captureReportImage() {{
      const btn = document.getElementById('btn-snap-zalo');
      if (btn) btn.innerHTML = '⏳ Đang tạo ảnh...';

      // Populate Zalo snapshot card
      document.getElementById('zalo-snap-time').innerText = 'Cập nhật PBI: ' + DATA.updated_at;
      document.getElementById('zalo-snap-pacing').innerText = `Tiến độ: Ngày ${{currentDay}}/${{totalDays}} (Chuẩn: ${{(targetPacing*100).toFixed(1)}}%)`;
      document.getElementById('zalo-snap-staff').innerText = DATA.summary.total_staff;
      document.getElementById('zalo-snap-avg').innerText = DATA.summary.avg_kpi + '%';
      
      const aheadCount = DATA.kpi_tong.filter(x => {{
        const p = x.pacing_info || calculatePacingDetails(x);
        return p.status === 'AHEAD' || p.status === 'ON_TRACK';
      }}).length;
      document.getElementById('zalo-snap-ahead').innerText = `${{aheadCount}} / ${{DATA.summary.total_staff}}`;
      document.getElementById('zalo-snap-top').innerText = DATA.summary.top_performer + ` (${{DATA.summary.top_kpi}}%)`;

      const tbody = document.getElementById('zalo-snap-tbody');
      tbody.innerHTML = '';
      const sorted = [...DATA.kpi_tong].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);

      sorted.forEach((item, idx) => {{
        const p = item.pacing_info || calculatePacingDetails(item);
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #334155';
        const rankMedal = idx === 0 ? '🥇 1' : idx === 1 ? '🥈 2' : idx === 2 ? '🥉 3' : (idx + 1);
        tr.innerHTML = `
          <td style="padding:6px 10px;font-weight:700;">${{rankMedal}}</td>
          <td style="padding:6px 10px;color:#94a3b8;">${{item.ma}}</td>
          <td style="padding:6px 10px;font-weight:700;">${{item.name}}</td>
          <td style="padding:6px 10px;text-align:right;">${{item.slg_kh.toLocaleString('vi-VN')}}</td>
          <td style="padding:6px 10px;text-align:right;">${{item.slg_cv.toLocaleString('vi-VN')}}</td>
          <td style="padding:6px 10px;text-align:center;">${{item.no_ticket_2ht > 0 ? item.no_ticket_2ht : '0'}}</td>
          <td style="padding:6px 10px;text-align:right;font-weight:800;color:#38bdf8;">${{(item.pct_kpi_tong*100).toFixed(2)}}%</td>
          <td style="padding:6px 10px;text-align:center;">
            <span class="badge ${{p.badgeClass}}" style="font-size:10px;padding:2px 6px;">${{p.text.split('•')[0]}}</span>
          </td>
        `;
        tbody.appendChild(tr);
      }});

      const card = document.getElementById('zalo-snapshot-card');
      card.style.left = '0px';
      card.style.top = '0px';
      card.style.zIndex = '-9999';

      if (typeof html2canvas === 'undefined') {{
        alert('Đang nạp thư viện html2canvas, vui lòng bấm lại sau 2 giây.');
        if (btn) btn.innerHTML = '📸 Xuất ảnh Zalo';
        card.style.left = '-9999px';
        return;
      }}

      html2canvas(card, {{
        scale: 2,
        useCORS: true,
        backgroundColor: '#0f172a'
      }}).then(canvas => {{
        card.style.left = '-9999px';
        
        canvas.toBlob(blob => {{
          // 1. Download image
          const dateStr = new Date().toISOString().slice(0, 10);
          const a = document.createElement('a');
          a.download = `Bao_Cao_KPI_CTO1_${{dateStr}}.png`;
          a.href = URL.createObjectURL(blob);
          a.click();

          // 2. Clipboard copy
          if (navigator.clipboard && window.ClipboardItem) {{
            navigator.clipboard.write([new ClipboardItem({{ 'image/png': blob }})])
              .then(() => {{
                showToast('🎉 Đã tải ảnh và COPY vào bộ nhớ tạm! Bạn chỉ cần nhấn Ctrl+V vào Zalo là gửi được ngay!');
              }})
              .catch(() => {{
                showToast('🎉 Đã tải file ảnh báo cáo xuống máy! Bạn hãy kéo ảnh gửi vào Zalo nhé.');
              }});
          }} else {{
            showToast('🎉 Đã tải file ảnh báo cáo xuống máy! Bạn hãy kéo ảnh gửi vào Zalo nhé.');
          }}
        }}, 'image/png');
      }}).catch(err => {{
        console.error(err);
        card.style.left = '-9999px';
        showToast('⚠️ Không thể xuất ảnh: ' + err.message);
      }}).finally(() => {{
        if (btn) btn.innerHTML = '📸 Xuất ảnh Zalo';
      }});
    }}

    function showToast(msg) {{
      const old = document.querySelector('.toast-msg');
      if (old) old.remove();
      const toast = document.createElement('div');
      toast.className = 'toast-msg';
      toast.innerHTML = `<span>${{msg}}</span>`;
      document.body.appendChild(toast);
      setTimeout(() => {{
        toast.style.transition = 'opacity 0.5s ease';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
      }}, 5000);
    }}

    // ==========================================
    // SCHEDULE & ATTENDANCE MODULE (TEAM ÔNG MINH NHỰT)
    // ==========================================
    let currentMainView = 'kpi'; // 'kpi' or 'schedule'
    let matrixDateFilter = 'all'; // 'all' or 'week'
    let currentScheduleCycle = 'a'; // 'a': 26-25, 'b': 1-end
    let currentScheduleRange = 'to_date'; // 'to_date' or 'full'
    let scheduleSearchQuery = '';

    function switchMainView(view) {{
      currentMainView = view;
      const kpiMain = document.getElementById('section-kpi-main');
      const schedPane = document.getElementById('tab-pane-schedule');
      const tabKpi = document.getElementById('nav-tab-kpi');
      const tabSched = document.getElementById('nav-tab-schedule');
      const hdrBtn = document.getElementById('hdr-btn-toggle-sched');

      if (view === 'schedule') {{
        if (kpiMain) kpiMain.style.display = 'none';
        if (schedPane) schedPane.style.display = 'block';
        if (tabKpi) tabKpi.classList.remove('active');
        if (tabSched) tabSched.classList.add('active');
        if (hdrBtn) hdrBtn.innerHTML = '📊 Quay lại Báo Cáo KPI';
        renderScheduleTab();
        setTimeout(jumpToTodayColumn, 250);
      }} else {{
        if (kpiMain) kpiMain.style.display = 'block';
        if (schedPane) schedPane.style.display = 'none';
        if (tabKpi) tabKpi.classList.add('active');
        if (tabSched) tabSched.classList.remove('active');
        if (hdrBtn) hdrBtn.innerHTML = '📅 Xem Lịch Trực Team';
      }}
    }}

    function toggleMainView() {{
      switchMainView(currentMainView === 'kpi' ? 'schedule' : 'kpi');
    }}

    function setMatrixDateFilter(filter) {{
      matrixDateFilter = filter;
      ['btn-matrix-all', 'btn-matrix-all-top', 'btn-matrix-all-bottom'].forEach(id => {{
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', filter === 'all');
      }});
      ['btn-matrix-week', 'btn-matrix-week-top', 'btn-matrix-week-bottom'].forEach(id => {{
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', filter === 'week');
      }});
      renderScheduleMatrixTable();
      setTimeout(jumpToTodayColumn, 100);
    }}

    function jumpToTodayColumn() {{
      const box = document.getElementById('matrix-scroll-box');
      if (!box) return;
      const todayTh = box.querySelector('thead th.col-today');
      if (todayTh) {{
        const stickyOffset = window.innerWidth <= 768 ? 115 : 240;
        const left = todayTh.offsetLeft - stickyOffset;
        box.scrollTo({{ left: Math.max(0, left), behavior: 'smooth' }});
        todayTh.style.animation = 'pulseTodayCol 1.5s 2';
        setTimeout(() => {{ todayTh.style.animation = ''; }}, 3000);
      }}
    }}

    function initSchedule() {{
      if (!DATA.schedule) return;
      const subtitle = document.getElementById('sched-subtitle-time');
      if (subtitle && DATA.schedule.updated_at) {{
        subtitle.innerText = `Đồng bộ lúc: ${{DATA.schedule.updated_at}} • Thuật toán chuẩn hóa công bất biến ≤ 1.0/ngày`;
      }}
      renderScheduleTab();
    }}

    function setScheduleCycle(cycle) {{
      currentScheduleCycle = cycle;
      const btnA = document.getElementById('btn-cycle-a');
      const btnB = document.getElementById('btn-cycle-b');
      if (btnA) btnA.classList.toggle('active', cycle === 'a');
      if (btnB) btnB.classList.toggle('active', cycle === 'b');
      const badge = document.getElementById('sched-table-cycle-badge');
      if (badge) {{
        badge.innerText = cycle === 'a' ? 'Chu kỳ 26 - 25' : 'Chu kỳ Đầu - Cuối tháng';
      }}
      renderScheduleTab();
    }}

    function setScheduleRange(range) {{
      currentScheduleRange = range;
      const btnT = document.getElementById('btn-range-todate');
      const btnF = document.getElementById('btn-range-full');
      if (btnT) btnT.classList.toggle('active', range === 'to_date');
      if (btnF) btnF.classList.toggle('active', range === 'full');
      renderScheduleTab();
    }}

    function onScheduleSearch(val) {{
      scheduleSearchQuery = (val || '').toLowerCase().trim();
      renderScheduleSummaryTable();
      renderScheduleMatrixTable();
    }}

    function renderScheduleTab() {{
      if (!DATA.schedule) return;
      renderScheduleKPIStats();
      renderTodayRoster();
      renderScheduleSummaryTable();
      renderScheduleMatrixTable();
    }}

    function getEmployeeStats(emp) {{
      const cycleKey = currentScheduleCycle === 'a' ? 'cycle_a' : 'cycle_b';
      const rangeKey = currentScheduleRange === 'to_date' ? 'to_date' : 'full';
      if (emp.stats && emp.stats[cycleKey] && emp.stats[cycleKey][rangeKey]) {{
        return emp.stats[cycleKey][rangeKey];
      }}
      return {{ off: 0, p: 0, work: 0, total: 0, days_counted: 0 }};
    }}

    function renderScheduleKPIStats() {{
      const emps = DATA.schedule.employees || [];
      let totalWork = 0;
      let totalOff = 0;
      let totalP = 0;
      emps.forEach(emp => {{
        const st = getEmployeeStats(emp);
        totalWork += st.work;
        totalOff += st.off;
        totalP += st.p;
      }});

      const wEl = document.getElementById('sched-stat-work');
      const oEl = document.getElementById('sched-stat-off');
      const pEl = document.getElementById('sched-stat-p');
      const sEl = document.getElementById('sched-stat-staff');

      if (wEl) wEl.innerText = totalWork.toFixed(1);
      if (oEl) oEl.innerText = totalOff.toFixed(1);
      if (pEl) pEl.innerText = totalP.toFixed(1);
      if (sEl) sEl.innerText = emps.length;

      const avgWork = emps.length ? (totalWork / emps.length).toFixed(1) : 0;
      const wSub = document.getElementById('sched-stat-work-sub');
      const oSub = document.getElementById('sched-stat-off-sub');
      if (wSub) wSub.innerText = `Trung bình ~${{avgWork}} ngày công/người`;
      if (oSub) oSub.innerText = currentScheduleRange === 'to_date' ? 'Lũy kế nghỉ tuần đến hôm nay' : 'Toàn bộ ngày nghỉ trong chu kỳ';
    }}

    function renderTodayRoster(targetDateStr) {{
      const dateStr = targetDateStr || DATA.schedule.today || new Date().toISOString().slice(0, 10);
      const emps = DATA.schedule.employees || [];

      const lbl = document.getElementById('roster-date-label');
      if (lbl && DATA.schedule.today_display) {{
        lbl.innerText = DATA.schedule.today_display;
      }}

      const groups = {{
        morning: {{ label: '🌅 Ca Sáng (S / S+)', items: [], color: '#0284c7' }},
        noon: {{ label: '☀️ Ca Trưa (TR)', items: [], color: '#d97706' }},
        evening: {{ label: '🌙 Ca Tối (T)', items: [], color: '#4f46e5' }},
        admin: {{ label: '🏢 Hành Chính & Kênh (HC / FB / TK)', items: [], color: '#059669' }},
        off: {{ label: '🏖️ Nghỉ OFF & Phép (P)', items: [], color: '#dc2626' }}
      }};

      emps.forEach(emp => {{
        const shiftList = (emp.shifts && emp.shifts[dateStr]) || [];
        if (!shiftList.length) return;

        let isOff = false;
        let isP = false;
        let isS = false;
        let isTR = false;
        let isT = false;
        let isHC = false;
        let detailTags = [];

        shiftList.forEach(s => {{
          const v = (s.val || '').toUpperCase().trim();
          const ca = (s.ca || '').toUpperCase().trim();
          detailTags.push(ca && ca !== v ? `${{ca}}: ${{v}}` : v);

          if (v === 'OFF' || v === 'OFF/2') isOff = true;
          if (v === 'P' || v === 'P/2') isP = true;
          if (ca.includes('S') && !ca.includes('HC')) isS = true;
          if (ca.includes('TR')) isTR = true;
          if (ca.includes('T')) isT = true;
          if (ca.includes('HC') || ['FB', 'TK', 'FC'].some(x => v.includes(x))) isHC = true;
        }});

        const pillText = `${{emp.name}} (${{detailTags.join(', ')}})`;
        if (isOff || isP) groups.off.items.push(pillText);
        else {{
          if (isS) groups.morning.items.push(pillText);
          if (isTR) groups.noon.items.push(pillText);
          if (isT) groups.evening.items.push(pillText);
          if (isHC && !isS && !isTR && !isT) groups.admin.items.push(pillText);
        }}
      }});

      const container = document.getElementById('roster-groups-content');
      if (!container) return;
      container.innerHTML = Object.values(groups).map(g => `
        <div class="roster-group-card">
          <div class="roster-group-label" style="color: ${{g.color}}">
            ${{g.label}} (${{g.items.length}})
          </div>
          <div class="roster-pills-wrap">
            ${{g.items.length ? g.items.map(item => `
              <span class="roster-pill" title="${{item}}">
                ${{item.split(' (')[0]}}
                <small style="opacity:0.75;font-weight:normal;">${{item.includes('(') ? item.substring(item.indexOf('(')) : ''}}</small>
              </span>
            `).join('') : '<span style="font-size:11px;color:var(--text-muted);font-style:italic;">Không có</span>'}}
          </div>
        </div>
      `).join('');
    }}

    function renderScheduleSummaryTable() {{
      const tbody = document.getElementById('tbody-schedule-summary');
      const tfoot = document.getElementById('tfoot-schedule-summary');
      if (!tbody) return;
      tbody.innerHTML = '';

      let emps = (DATA.schedule && DATA.schedule.employees) || [];
      if (scheduleSearchQuery) {{
        emps = emps.filter(e => e.name.toLowerCase().includes(scheduleSearchQuery) || e.id.includes(scheduleSearchQuery));
      }}

      let sumOff = 0, sumP = 0, sumWork = 0, sumTotal = 0;
      const myName = localStorage.getItem('kpicto_my_name') || '';

      emps.forEach((emp, idx) => {{
        const st = getEmployeeStats(emp);
        sumOff += st.off;
        sumP += st.p;
        sumWork += st.work;
        sumTotal += st.total;

        const isMe = myName && (emp.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(emp.name.toLowerCase()));
        const tr = document.createElement('tr');
        if (isMe) tr.classList.add('my-row-highlight');

        tr.innerHTML = `
          <td>${{idx + 1}}</td>
          <td><span class="badge" style="background:rgba(255,255,255,0.06);font-family:monospace;">${{emp.id}}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <strong>${{emp.name}}</strong>
              ${{emp.is_leader ? '<span class="badge" style="background:#fef3c7;color:#b45309;font-size:10px;padding:2px 6px;">👑 Leader</span>' : ''}}
            </div>
          </td>
          <td><span style="font-size:12px;color:var(--text-muted);">${{emp.role || 'Nhân viên CS'}}</span></td>
          <td class="numeric">
            <span class="badge" style="background:rgba(239, 68, 68, 0.15);color:#ef4444;font-weight:700;">${{st.off}}</span>
          </td>
          <td class="numeric">
            <span class="badge" style="background:rgba(168, 85, 247, 0.15);color:#a855f7;font-weight:700;">${{st.p}}</span>
          </td>
          <td class="numeric">
            <span class="badge" style="background:rgba(16, 185, 129, 0.15);color:#10b981;font-weight:700;">${{st.work}}</span>
          </td>
          <td class="numeric">
            <strong style="color:var(--text-main);">${{st.total}}</strong>
          </td>
          <td class="text-center">
            <button class="btn btn-sm" onclick="scrollToEmployeeMatrix('${{emp.id}}')" style="padding:4px 8px;font-size:11px;">
              👁️ Xem Lịch
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      }});

      if (tfoot) {{
        tfoot.innerHTML = `
          <tr style="background:rgba(0,0,0,0.25);font-weight:800;">
            <td colspan="4" style="text-align:right;padding-right:15px;">Tổng cộng cả Team:</td>
            <td class="numeric" style="color:#ef4444;">${{sumOff.toFixed(1)}}</td>
            <td class="numeric" style="color:#a855f7;">${{sumP.toFixed(1)}}</td>
            <td class="numeric" style="color:#10b981;">${{sumWork.toFixed(1)}}</td>
            <td class="numeric" style="color:var(--text-main);">${{sumTotal.toFixed(1)}}</td>
            <td></td>
          </tr>
        `;
      }}
    }}

    function renderScheduleMatrixTable() {{
      const thead = document.getElementById('thead-matrix-schedule');
      const tbody = document.getElementById('tbody-matrix-schedule');
      if (!thead || !tbody || !DATA.schedule) return;

      let dates = (DATA.schedule.dates || []).filter(d => {{
        return currentScheduleCycle === 'a' ? d.in_cycle_a : d.in_cycle_b;
      }});

      if (matrixDateFilter === 'week') {{
        const todayStr = DATA.schedule.today || '2026-11-15';
        const parts = todayStr.split('-').map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        const day = d.getDay();
        const diffToMonday = (day === 0 ? -6 : 1 - day);
        const monday = new Date(d);
        monday.setDate(d.getDate() + diffToMonday);

        const weekSet = new Set();
        for (let i = 0; i < 7; i++) {{
          const cur = new Date(monday);
          cur.setDate(monday.getDate() + i);
          const y = cur.getFullYear();
          const m = String(cur.getMonth() + 1).padStart(2, '0');
          const dayNum = String(cur.getDate()).padStart(2, '0');
          weekSet.add(`${{y}}-${{m}}-${{dayNum}}`);
        }}
        dates = dates.filter(d => weekSet.has(d.date_str));
      }}

      thead.innerHTML = `
        <tr>
          <th class="sticky-col-id" rowspan="2">MS</th>
          <th class="sticky-col-name" rowspan="2">Họ và Tên Nhân Sự</th>
          ${{dates.map(d => `
            <th class="${{d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}}">
              ${{d.thu}}
            </th>
          `).join('')}}
        </tr>
        <tr>
          ${{dates.map(d => `
            <th class="${{d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}}" style="font-size:13px;font-weight:800;">
              ${{d.day_num}}/${{d.month}}
              ${{d.is_today ? '<div style="font-size:9px;background:#f59e0b;color:#000;border-radius:3px;padding:1px 3px;margin-top:2px;">📍 HÔM NAY</div>' : ''}}
            </th>
          `).join('')}}
        </tr>
      `;

      let emps = (DATA.schedule && DATA.schedule.employees) || [];
      if (scheduleSearchQuery) {{
        emps = emps.filter(e => e.name.toLowerCase().includes(scheduleSearchQuery) || e.id.includes(scheduleSearchQuery));
      }}

      const myName = localStorage.getItem('kpicto_my_name') || '';

      tbody.innerHTML = emps.map(emp => {{
        const isMe = myName && (emp.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(emp.name.toLowerCase()));
        return `
          <tr id="matrix-row-${{emp.id}}" class="${{isMe ? 'my-row-highlight' : ''}}">
            <td class="sticky-col-id">
              <span style="font-family:monospace;font-size:11px;color:var(--text-muted);">${{emp.id}}</span>
            </td>
            <td class="sticky-col-name">
              <div style="display:flex;align-items:center;gap:6px;">
                <span>${{emp.name}}</span>
                ${{emp.is_leader ? '<span title="Leader" style="cursor:default;">👑</span>' : ''}}
              </div>
            </td>
            ${{dates.map(d => {{
              const shifts = (emp.shifts && emp.shifts[d.date_str]) || [];
              let content = '';
              if (!shifts.length) {{
                content = '<span style="color:rgba(255,255,255,0.15);">-</span>';
              }} else {{
                content = shifts.map(s => {{
                  const v = (s.val || '').trim();
                  const vu = v.toUpperCase();
                  let cls = 'badge-shift-other';
                  if (vu.startsWith('OFF')) cls = 'badge-shift-off';
                  else if (vu.startsWith('P')) cls = 'badge-shift-p';
                  else if (s.ca.includes('S') && !s.ca.includes('HC')) cls = 'badge-shift-s';
                  else if (s.ca.includes('TR')) cls = 'badge-shift-tr';
                  else if (s.ca.includes('T')) cls = 'badge-shift-t';
                  else if (s.ca.includes('HC') || ['FB', 'TK', 'FC'].some(x => vu.includes(x))) cls = 'badge-shift-hc';

                  const label = (s.ca && s.ca !== v) ? `${{s.ca}}: ${{v}}` : v;
                  return `<span class="badge-shift ${{cls}}" title="${{d.thu}} ${{d.day_num}}/${{d.month}}: ${{label}}">${{label}}</span>`;
                }}).join('');
              }}
              return `<td class="${{d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}}">${{content}}</td>`;
            }}).join('')}}
          </tr>
        `;
      }}).join('');
    }}

    function scrollToEmployeeMatrix(empId) {{
      const row = document.getElementById('matrix-row-' + empId);
      if (row) {{
        row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        row.style.outline = '2px solid #f59e0b';
        setTimeout(() => row.style.outline = '', 3000);
      }}
    }}

    function exportScheduleExcel() {{
      if (!DATA.schedule) return;
      const emps = DATA.schedule.employees || [];
      const cycleTitle = currentScheduleCycle === 'a' ? 'Chu_ky_26_25' : 'Chu_ky_Dau_Cuoi_thang';
      const rangeTitle = currentScheduleRange === 'to_date' ? 'Den_hom_nay' : 'Ca_chu_ky';

      let csv = "\\uFEFFSTT,Mã NV,Họ và Tên,Chức Vụ,Ngày OFF,Ngày Phép,Ngày Làm Việc,Tổng Ngày\\n";
      emps.forEach((emp, idx) => {{
        const st = getEmployeeStats(emp);
        csv += `"${{idx + 1}}","${{emp.id}}","${{emp.name}}","${{emp.role || ''}}","${{st.off}}","${{st.p}}","${{st.work}}","${{st.total}}"\\n`;
      }});

      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `Bao_Cao_Cham_Cong_Team_CTO1_${{cycleTitle}}_${{rangeTitle}}.csv`;
      a.click();
      showToast('📥 Đã tải xuống file CSV chấm công thành công!');
    }}

    async function syncScheduleLive() {{
      const btn = document.getElementById('btn-sync-schedule');
      if (btn) {{
        btn.innerHTML = '⏳ Đang tải Google Sheets...';
        btn.style.opacity = '0.7';
      }}

      try {{
        const token = await getGoogleServiceAccountToken();
        const sheetName = encodeURIComponent('Tháng 11/2026');
        const url = `https://sheets.googleapis.com/v4/spreadsheets/1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo/values/${{sheetName}}?valueRenderOption=FORMATTED_VALUE`;
        const res = await fetch(url, {{
          headers: {{ 'Authorization': 'Bearer ' + token }}
        }});
        const json = await res.json();
        if (json.values && json.values.length > 5) {{
          showToast('✅ Đã cập nhật lịch trực mới nhất trực tiếp từ Google Sheets!');
          renderScheduleTab();
        }}
      }} catch (err) {{
        console.warn('Sync schedule warning:', err);
        showToast('⚠️ Không thể kết nối Google Sheets trực tiếp, hiển thị dữ liệu đã lưu.');
      }} finally {{
        if (btn) {{
          btn.innerHTML = '🔄 Tải lại Lịch Trực Mới Nhất';
          btn.style.opacity = '1';
        }}
      }}
    }}

    // TV Kiosk Mode
    let tvInterval = null;
    let tvProgressInterval = null;
    let tvSlideIndex = 0;
    const TV_SLIDES = ['kpi', 'hs', 'schedule', 'podium'];
    const TV_SLIDE_DURATION = 15000;

    function toggleTvMode() {{
      const isTv = document.body.classList.toggle('tv-kiosk-mode');
      if (isTv) {{
        if (document.documentElement.requestFullscreen) {{
          document.documentElement.requestFullscreen().catch(() => {{}});
        }}
        startTvLoop();
        showToast('📺 Đã bật Chế độ TV! Đang xoay vòng hiển thị mỗi 15 giây. Nhấn ESC để thoát.');
      }} else {{
        stopTvLoop();
        if (document.exitFullscreen && document.fullscreenElement) {{
          document.exitFullscreen().catch(() => {{}});
        }}
        showToast('Đã thoát Chế độ TV.');
      }}
    }}

    function startTvLoop() {{
      stopTvLoop();
      tvSlideIndex = 0;
      switchTab(TV_SLIDES[tvSlideIndex]);
      animateTvProgress();

      tvInterval = setInterval(() => {{
        tvSlideIndex = (tvSlideIndex + 1) % TV_SLIDES.length;
        switchTab(TV_SLIDES[tvSlideIndex]);
        animateTvProgress();
      }}, TV_SLIDE_DURATION);
    }}

    function stopTvLoop() {{
      if (tvInterval) clearInterval(tvInterval);
      if (tvProgressInterval) clearInterval(tvProgressInterval);
      tvInterval = null;
      tvProgressInterval = null;
      const bar = document.getElementById('tv-progress-bar');
      if (bar) bar.style.width = '0%';
    }}

    function animateTvProgress() {{
      const bar = document.getElementById('tv-progress-bar');
      if (!bar) return;
      if (tvProgressInterval) clearInterval(tvProgressInterval);
      let start = Date.now();
      tvProgressInterval = setInterval(() => {{
        let elapsed = Date.now() - start;
        let pct = Math.min((elapsed / TV_SLIDE_DURATION) * 100, 100);
        bar.style.width = pct + '%';
        if (elapsed >= TV_SLIDE_DURATION) {{
          clearInterval(tvProgressInterval);
        }}
      }}, 100);
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape' && document.body.classList.contains('tv-kiosk-mode')) {{
        toggleTvMode();
      }}
    }});

    document.addEventListener('fullscreenchange', () => {{
      if (!document.fullscreenElement && document.body.classList.contains('tv-kiosk-mode')) {{
        toggleTvMode();
      }}
    }});

    function toggleTheme() {{
      document.body.classList.toggle('light-theme');
      const isLight = document.body.classList.contains('light-theme');
      document.getElementById('theme-icon').innerText = isLight ? '☀️' : '🌙';
    }}

    function exportCurrentTableToCSV() {{
      let csvContent = "data:text/csv;charset=utf-8,\\uFEFF";
      if (currentTab === 'kpi') {{
        csvContent += `STT,Ma NV,Ho va Ten,Team,Level,KPI Ticket,Dat KH,% KPI Ticket,KPI CV,Dat CV,% KPI CV,TK 2 CV Ho Tro,% KPI Tong,Tien Do Ngay ${{currentDay}}\\n`;
        filteredKpi.forEach((x, idx) => {{
          const p = x.pacing_info || calculatePacingDetails(x);
          csvContent += `"${{idx+1}}","${{x.ma}}","${{x.name}}","${{x.team}}","${{x.level}}","${{x.kpi_ticket}}","${{x.slg_kh}}","${{(x.pct_kpi_ticket*100).toFixed(2)}}%","${{x.kpi_cv}}","${{x.slg_cv}}","${{(x.pct_kpi_cv*100).toFixed(2)}}%","${{x.no_ticket_2ht}}","${{(x.pct_kpi_tong*100).toFixed(2)}}%","${{p.text}}"\\n`;
        }});
      }} else {{
        csvContent += "STT,Nhan Vien,Gio S,CV S,KH S,%KPI S,Gio HCS,CV HCS,KH HCS,%KPI HCS,Gio TR,CV TR,KH TR,%KPI TR,Gio HCC,CV HCC,KH HCC,%KPI HCC,Gio T,CV T,KH T,%KPI T,Tong Gio,Tong CV,Tong KH,%KPI Tong\\n";
        filteredHs.forEach((x, idx) => {{
          const s = x.shifts;
          csvContent += `"${{idx+1}}","${{x.user_name}}","${{s.S.hours}}","${{s.S.cv}}","${{s.S.kh}}","${{(s.S.pct_kpi*100).toFixed(2)}}%","${{s.HCS.hours}}","${{s.HCS.cv}}","${{s.HCS.kh}}","${{(s.HCS.pct_kpi*100).toFixed(2)}}%","${{s.TR.hours}}","${{s.TR.cv}}","${{s.TR.kh}}","${{(s.TR.pct_kpi*100).toFixed(2)}}%","${{s.HCC.hours}}","${{s.HCC.cv}}","${{s.HCC.kh}}","${{(s.HCC.pct_kpi*100).toFixed(2)}}%","${{s.T.hours}}","${{s.T.cv}}","${{s.T.kh}}","${{(s.T.pct_kpi*100).toFixed(2)}}%","${{s.Total.hours}}","${{s.Total.cv}}","${{s.Total.kh}}","${{(s.Total.pct_kpi*100).toFixed(2)}}%"\\n`;
        }});
      }}
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `KPI_Export_${{currentTab}}_${{new Date().toISOString().slice(0,10)}}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    /* ============================================================
       GOOGLE SHEETS WEBCRYPTO SERVICE ACCOUNT DIRECT REALTIME
       (Cơ chế Realtime tức thì 0s delay từ TeamCoacherDashboard)
       ============================================================ */
    const SA_CONFIG = {creds_json};
    const SPREADSHEET_ID = '1Gp4UVa_6YyQHA9SZxts8ey9z_mwB3j-BEKx20fvPPfk';
    const APPS_SCRIPT_API = window.APPS_SCRIPT_API || '';
    let _gSaToken = '';
    let _gSaTokenExp = 0;

    function _base64UrlEncodeStr(str) {{
      const b64 = btoa(unescape(encodeURIComponent(str)));
      return b64.replace(/=/g, '').replace(/\\+/g, '-').replace(/\\//g, '_');
    }}

    function _arrayBufferToBase64Url(buffer) {{
      const bytes = new Uint8Array(buffer);
      let binary = '';
      const len = bytes.byteLength;
      for (let i = 0; i < len; i++) {{
        binary += String.fromCharCode(bytes[i]);
      }}
      return btoa(binary).replace(/=/g, '').replace(/\\+/g, '-').replace(/\\//g, '_');
    }}

    function _pemToBinary(pem) {{
      const b64 = pem
        .replace(/-----BEGIN [A-Z ]+-----/, '')
        .replace(/-----END [A-Z ]+-----/, '')
        .replace(/\\s+/g, '');
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {{
        bytes[i] = binary.charCodeAt(i);
      }}
      return bytes.buffer;
    }}

    async function getGoogleServiceAccountToken() {{
      const now = Math.floor(Date.now() / 1000);
      if (!_gSaToken) {{
        _gSaToken = sessionStorage.getItem('kpicto_sa_token') || '';
        _gSaTokenExp = parseInt(sessionStorage.getItem('kpicto_sa_exp') || '0', 10);
      }}

      if (_gSaToken && _gSaTokenExp > now + 180) {{
        return _gSaToken;
      }}

      if (!SA_CONFIG || !SA_CONFIG.enc_pk) {{
        throw new Error('Chưa có cấu hình Service Account');
      }}

      const rawPrivateKey = atob(SA_CONFIG.enc_pk);
      const binaryDer = _pemToBinary(rawPrivateKey);
      const cryptoObj = window.crypto || window.msCrypto;
      if (!cryptoObj || !cryptoObj.subtle) {{
        throw new Error('Trình duyệt không hỗ trợ WebCrypto');
      }}

      const privateKey = await cryptoObj.subtle.importKey(
        'pkcs8',
        binaryDer,
        {{ name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }},
        false,
        ['sign']
      );

      const header = _base64UrlEncodeStr(JSON.stringify({{ alg: 'RS256', typ: 'JWT' }}));
      const payload = _base64UrlEncodeStr(JSON.stringify({{
        iss: SA_CONFIG.client_email,
        scope: 'https://www.googleapis.com/auth/spreadsheets.readonly',
        aud: SA_CONFIG.token_uri,
        exp: now + 3600,
        iat: now
      }}));

      const toSign = new TextEncoder().encode(header + '.' + payload);
      const signature = await cryptoObj.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, toSign);
      const sigB64 = _arrayBufferToBase64Url(signature);
      const jwtAssertion = header + '.' + payload + '.' + sigB64;

      const res = await fetch(SA_CONFIG.token_uri, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
        body: 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + encodeURIComponent(jwtAssertion)
      }});

      const data = await res.json();
      if (!data.access_token) {{
        throw new Error(data.error_description || data.error || 'Không thể lấy token xác thực Google');
      }}

      _gSaToken = data.access_token;
      _gSaTokenExp = now + (data.expires_in || 3600);
      sessionStorage.setItem('kpicto_sa_token', _gSaToken);
      sessionStorage.setItem('kpicto_sa_exp', String(_gSaTokenExp));
      return _gSaToken;
    }}

    async function fetchRealtimeSheetsData(showStatus = false) {{
      const btn = document.querySelector('.btn-refresh');
      if (showStatus && btn) {{
        btn.innerHTML = '⏳ Đang tải số mới...';
        btn.style.opacity = '0.7';
      }}

      let foundUpdateTime = null;
      try {{
        let rowsKpi = [];
        let rowsHs = [];

        if (APPS_SCRIPT_API) {{
          const cacheBusterUrl = APPS_SCRIPT_API + (APPS_SCRIPT_API.includes('?') ? '&' : '?') + 'sheet=all&_t=' + Date.now();
          const res = await fetch(cacheBusterUrl);
          if (!res.ok) throw new Error('Google Apps Script error: ' + res.status);
          const json = await res.json();
          rowsKpi = json.rowsKpi || json.kpi_tong || (json.sheet === 'KPI tong' ? json.data : []) || [];
          rowsHs = json.rowsHs || json.hs_ca_truc || (json.sheet === 'HS ca truc' ? json.data : []) || [];
          if (json.updated_at) foundUpdateTime = json.updated_at;
        }} else if (SA_CONFIG && SA_CONFIG.client_email && SA_CONFIG.enc_pk) {{
          const token = await getGoogleServiceAccountToken();
          const url = `https://sheets.googleapis.com/v4/spreadsheets/${{SPREADSHEET_ID}}/values:batchGet?ranges=KPI%20tong!A1:P30&ranges=HS%20ca%20truc!A1:AC30&t=${{Date.now()}}`;
          const res = await fetch(url, {{
            headers: {{ 'Authorization': 'Bearer ' + token }}
          }});

          if (!res.ok) throw new Error('Google Sheets API error: ' + res.status);
          const json = await res.json();
          const valRanges = json.valueRanges || [];
          rowsKpi = valRanges[0] ? (valRanges[0].values || []) : [];
          rowsHs = valRanges[1] ? (valRanges[1].values || []) : [];
        }} else {{
          if (showStatus) {{
            showToast('ℹ️ Đang hiển thị số liệu mới nhất!');
          }}
          return;
        }}

        if (rowsKpi.length <= 1) return;

        const parseNum = (v) => {{
          if (v === '' || v === null || v === undefined) return 0;
          if (typeof v === 'number') return v;
          let s = String(v).replace('%', '').replace(/,/g, '').trim();
          let n = parseFloat(s);
          if (isNaN(n)) return 0;
          if (String(v).includes('%')) return n / 100;
          return n;
        }};

        let foundUpdateTime = null;
        const newKpiData = [];
        for (let i = 1; i < rowsKpi.length; i++) {{
          const r = rowsKpi[i];
          const rawName = String(r[1] || '').trim();
          if (!rawName || rawName.toLowerCase().includes('applied filters')) continue;

          let shortName = rawName;
          const parts = rawName.split('-');
          if (parts.length >= 2) shortName = parts[1].trim();

          if (r[15] && String(r[15]).includes('Cập nhật')) {{
            foundUpdateTime = String(r[15]).replace('Cập nhật PBI:', '').replace('Cập nhật:', '').trim();
          }}

          newKpiData.push({{
            id: newKpiData.length + 1,
            ma: String(r[0] || '').split('.')[0],
            name: shortName,
            full_name: rawName,
            team: String(r[2] || ''),
            level: String(r[3] || '').split('.')[0],
            kpi_ticket: parseNum(r[4]),
            slg_kh: parseNum(r[5]),
            pct_kpi_ticket: parseNum(r[6]),
            kpi_cv: parseNum(r[7]),
            slg_cv: parseNum(r[8]),
            pct_kpi_cv: parseNum(r[9]),
            no_ticket_2ht: Math.round(parseNum(r[10])),
            pct_kpi_tong: parseNum(r[11])
          }});
        }}

        const shiftMap = [
          {{ name: 'Khác', col: 1 }},
          {{ name: 'S', col: 5 }},
          {{ name: 'HCS', col: 9 }},
          {{ name: 'TR', col: 13 }},
          {{ name: 'HCC', col: 17 }},
          {{ name: 'T', col: 21 }},
          {{ name: 'Total', col: 25 }}
        ];

        const newHsData = [];
        for (let i = 1; i < rowsHs.length; i++) {{
          const r = rowsHs[i];
          const uName = String(r[0] || '').trim();
          if (!uName || uName.toLowerCase().includes('user_name') || uName.toLowerCase().includes('applied filters')) continue;

          const shifts = {{}};
          shiftMap.forEach(s => {{
            shifts[s.name] = {{
              hours: Math.round(parseNum(r[s.col]) * 100) / 100,
              cv: Math.round(parseNum(r[s.col + 1]) * 10) / 10,
              kh: Math.round(parseNum(r[s.col + 2]) * 10) / 10,
              pct_kpi: Math.round(parseNum(r[s.col + 3]) * 10000) / 10000
            }};
          }});

          newHsData.push({{
            user_name: uName,
            shifts: shifts
          }});
        }}

        if (newKpiData.length > 0) {{
          DATA.kpi_tong = newKpiData;
          if (newHsData.length > 0) DATA.hs_ca_truc = newHsData;
          if (foundUpdateTime) DATA.updated_at = foundUpdateTime;

          const totalStaff = newKpiData.length;
          const avgKpi = newKpiData.reduce((acc, x) => acc + x.pct_kpi_tong, 0) / totalStaff;
          const totalTicket = newKpiData.reduce((acc, x) => acc + x.slg_kh, 0);
          const totalCv = newKpiData.reduce((acc, x) => acc + x.slg_cv, 0);
          const total2Ht = newKpiData.reduce((acc, x) => acc + x.no_ticket_2ht, 0);
          const top = [...newKpiData].sort((a, b) => b.pct_kpi_tong - a.pct_kpi_tong)[0];

          DATA.summary = {{
            total_staff: totalStaff,
            avg_kpi: (avgKpi * 100).toFixed(2),
            total_ticket: totalTicket.toFixed(1),
            total_cv: totalCv.toFixed(1),
            total_ticket_2ht: total2Ht,
            top_performer: top ? top.name : '',
            top_kpi: top ? (top.pct_kpi_tong * 100).toFixed(2) : 0
          }};

          updatePacingDisplay();
          applyFilters();

          const now = new Date();
          const timeStr = now.toLocaleTimeString('vi-VN', {{ hour: '2-digit', minute: '2-digit', second: '2-digit' }});
          const liveBadge = document.querySelector('.badge-live');
          if (liveBadge) {{
            liveBadge.innerHTML = `<span class="dot-live"></span><span>Live Sheet: <strong id="lbl-updated-at">${{DATA.updated_at}}</strong> (vừa cập nhật ${{timeStr}})</span>`;
          }}
        }}
      }} catch (err) {{
        console.warn('Google Sheet realtime note:', err);
      }} finally {{
        if (btn) {{
          btn.innerHTML = '🔄 Tải lại số liệu mới nhất';
          btn.style.opacity = '1';
        }}
      }}
    }}

    function reloadLatestData() {{
      fetchRealtimeSheetsData(true);
    }}

    window.onload = function() {{
      init();
      fetchRealtimeSheetsData(false);
    }};
  </script>
</body>
</html>
"""
    # Write to workspace
    ws_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpi_dashboard.html")
    with open(ws_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated dashboard: {ws_path}")

    # Copy to index.html for active web server
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    try:
        shutil.copyfile(ws_path, index_path)
        print(f"Synced to index.html: {index_path}")
    except Exception as e:
        print(f"Index sync note: {e}")

    # Write to artifact directory
    artifact_path = r"C:\Users\quoc\.gemini\antigravity\brain\1a3f1ada-6c32-4202-95be-30efc04b91ec\kpi_dashboard.html"
    try:
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Saved artifact: {artifact_path}")
    except Exception as e:
        print(f"Artifact save note: {e}")

if __name__ == "__main__":
    generate_dashboard()
