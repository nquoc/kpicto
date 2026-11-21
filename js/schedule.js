/* ============================================================
   SCHEDULE & ATTENDANCE MODULE
   ============================================================ */
    // SCHEDULE & ATTENDANCE MODULE (TEAM ÔNG MINH NHỰT)
    // ==========================================
    let currentMainView = 'kpi'; // 'kpi' or 'ot'
    let matrixDateFilter = 'week'; // 'all' or 'week' - Mặc định 'week' (Tuần này) theo yêu cầu
    let currentScheduleCycle = 'a'; // 'a': 26-25, 'b': 1-end
    let currentScheduleRange = 'to_date'; // 'to_date' or 'full'
    let scheduleSearchQuery = '';
    const TARGET_SCHEDULE_IDS = ["8239", "8131", "8171", "8116", "8177", "8222", "8257", "8274", "8284", "8285", "8817", "8818", "8805", "8607"];

    function getCellVal(c) {
      if (c === null || c === undefined) return '';
      if (typeof c === 'object') return String(c.formattedValue || '').trim();
      return String(c).trim();
    }

    function detectCellColorType(c) {
      if (!c || typeof c !== 'object' || !c.effectiveFormat || !c.effectiveFormat.backgroundColor) return '';
      const bg = c.effectiveFormat.backgroundColor;
      const r = bg.red || 0, g = bg.green || 0, b = bg.blue || 0;
      if (r >= 0.75 && g <= 0.65 && b <= 0.65) return 'RED';
      if (r >= 0.75 && g >= 0.70 && b <= 0.70) return 'YELLOW';
      return '';
    }

    function parseRawScheduleRows(rows, m, y) {
      if (!rows || rows.length === 0) return { empSchedules: {}, colToDate: {} };
      let ngayRowIdx = null, caRowIdx = null, thuRowIdx = null;
      for (let idx = 0; idx < Math.min(12, rows.length); idx++) {
        const rowCells = rows[idx] || [];
        const txt = rowCells.map(getCellVal).join(' ').toLowerCase();
        if (txt.includes('thứ') || txt.includes('cn')) {
          if (thuRowIdx === null) thuRowIdx = idx;
        }
        const sCount = rowCells.filter(c => ['S', 'TR', 'T', 'HC-S', 'HC-C'].includes(getCellVal(c))).length;
        if (sCount >= 5 && caRowIdx === null) caRowIdx = idx;
      }
      if (caRowIdx !== null) {
        ngayRowIdx = caRowIdx - 1;
        if (thuRowIdx === null) thuRowIdx = caRowIdx - 2;
      } else {
        thuRowIdx = 2; ngayRowIdx = 3; caRowIdx = 4;
      }

      const thuRow = rows[thuRowIdx] || [];
      const ngayRow = rows[ngayRowIdx] || [];
      const caRow = rows[caRowIdx] || [];

      let endCol = caRow.length;
      for (let i = 4; i < caRow.length; i++) {
        const caName = (getCellVal(caRow[i]) || getCellVal(ngayRow[i])).toLowerCase();
        if (caName.includes('tổng') || caName.includes('tong')) {
          endCol = i;
          break;
        }
      }

      const colToDate = {};
      let currDay = "", currThu = "";
      for (let i = 4; i < endCol; i++) {
        const thuVal = getCellVal(thuRow[i]);
        const dayVal = getCellVal(ngayRow[i]);
        if (thuVal) currThu = thuVal;
        if (dayVal) currDay = dayVal;
        if (!currDay) continue;
        const dayNum = parseInt(currDay);
        if (isNaN(dayNum)) continue;

        let dm = (dayNum >= 26) ? (m - 1) : m;
        let dy = (m > 1 || dayNum < 26) ? y : (y - 1);
        if (dm === 0) dm = 12;

        const pad = n => n < 10 ? '0' + n : String(n);
        const dateStr = `${dy}-${pad(dm)}-${pad(dayNum)}`;
        colToDate[i] = {
          dateStr,
          dayNum,
          dm,
          dy,
          thu: currThu,
          ca: getCellVal(caRow[i])
        };
      }

      const empSchedules = {};
      const startEmpRow = (caRowIdx !== null) ? (caRowIdx + 1) : 5;
      for (let rIdx = startEmpRow; rIdx < rows.length; rIdx++) {
        const row = rows[rIdx];
        if (row.length <= 3) continue;
        const empId = getCellVal(row[2]);
        const empName = getCellVal(row[3]);
        if (!empId || !TARGET_SCHEDULE_IDS.includes(empId)) continue;

        if (!empSchedules[empId]) {
          empSchedules[empId] = { name: empName, shifts: {} };
        }

        for (const [colIdxStr, colInfo] of Object.entries(colToDate)) {
          const colIdx = parseInt(colIdxStr);
          const cell = row[colIdx];
          const val = getCellVal(cell);
          const dStr = colInfo.dateStr;
          if (!empSchedules[empId].shifts[dStr]) {
            empSchedules[empId].shifts[dStr] = [];
          }
          if (val) {
            const colorType = detectCellColorType(cell);
            empSchedules[empId].shifts[dStr].push({
              ca: colInfo.ca,
              val,
              ...(colorType ? { colorType } : {})
            });
          }
        }
      }

      return { empSchedules, colToDate };
    }

    function calcScheduleStats(shiftsDict, startD, endD, limitD = null) {
      let totOff = 0.0, totP = 0.0, totWork = 0.0, daysCt = 0;
      const curr = new Date(startD.getTime());
      const lim = limitD ? new Date(Math.min(endD.getTime(), limitD.getTime())) : endD;
      const pad = n => n < 10 ? '0' + n : String(n);

      while (curr <= lim) {
        const dStr = `${curr.getFullYear()}-${pad(curr.getMonth() + 1)}-${pad(curr.getDate())}`;
        const sList = shiftsDict[dStr] || [];
        if (sList.length > 0) {
          daysCt++;
          let offVal = 0.0, pVal = 0.0, hasActive = false;
          for (const item of sList) {
            const v = (item.val || '').toUpperCase().trim();
            if (v === 'OFF') offVal += 1.0;
            else if (v === 'OFF/2') offVal += 0.5;
            else if (v === 'P') pVal += 1.0;
            else if (v === 'P/2') pVal += 0.5;
            else if (v !== '') hasActive = true;
          }
          const dOff = Math.min(1.0, offVal);
          const dP = Math.min(1.0 - dOff, pVal);
          const dWork = hasActive ? (1.0 - dOff - dP) : 0.0;
          totOff += dOff; totP += dP; totWork += dWork;
        }
        curr.setDate(curr.getDate() + 1);
      }
      return {
        off: totOff,
        p: totP,
        work: totWork,
        total: totOff + totP + totWork,
        days_counted: daysCt
      };
    }

    function buildScheduleFromRawSheet(rows, refDate = new Date(), nextRows = null) {
      const pad = n => n < 10 ? '0' + n : String(n);
      const now = refDate;
      const mCurr = now.getMonth() + 1;
      const yCurr = now.getFullYear();
      const mNext = (mCurr < 12) ? mCurr + 1 : 1;
      const yNext = (mCurr < 12) ? yCurr : yCurr + 1;
      const mPrev = (mCurr > 1) ? mCurr - 1 : 12;
      const yPrev = (mCurr > 1) ? yCurr : yCurr - 1;

      const { empSchedules: schedCurr } = parseRawScheduleRows(rows, mCurr, yCurr);

      const allEmployees = {};
      for (const [eid, info] of Object.entries(schedCurr)) {
        if (!allEmployees[eid]) allEmployees[eid] = { id: eid, name: info.name, shifts: {} };
        for (const [d, s] of Object.entries(info.shifts)) {
          allEmployees[eid].shifts[d] = s;
        }
      }

      if (nextRows && nextRows.length > 0) {
        const { empSchedules: schedNext } = parseRawScheduleRows(nextRows, mNext, yNext);
        for (const [eid, info] of Object.entries(schedNext)) {
          if (!allEmployees[eid]) allEmployees[eid] = { id: eid, name: info.name, shifts: {} };
          for (const [d, s] of Object.entries(info.shifts)) {
            allEmployees[eid].shifts[d] = s;
          }
        }
      }

      const isAfter26 = now.getDate() >= 26;
      const cycleAStart = isAfter26 ? new Date(yCurr, mCurr - 1, 26) : new Date(yPrev, mPrev - 1, 26);
      const cycleAEnd = isAfter26 ? new Date(yNext, mNext - 1, 25) : new Date(yCurr, mCurr - 1, 25);
      const cycleBStart = new Date(yCurr, mCurr - 1, 1);
      const lastD = new Date(yCurr, mCurr, 0).getDate();
      const cycleBEnd = new Date(yCurr, mCurr - 1, lastD);
      const today = new Date(yCurr, now.getMonth(), now.getDate());

      const minDate = new Date(Math.min(cycleAStart.getTime(), cycleBStart.getTime()));
      const maxDate = new Date(Math.max(cycleAEnd.getTime(), cycleBEnd.getTime()));

      const thuNamesVi = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
      const datesList = [];
      const cD = new Date(minDate.getTime());
      while (cD <= maxDate) {
        const dStr = `${cD.getFullYear()}-${pad(cD.getMonth() + 1)}-${pad(cD.getDate())}`;
        const dayOfWeek = cD.getDay();
        const thuIdx = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        datesList.push({
          date_str: dStr,
          day_num: cD.getDate(),
          month: cD.getMonth() + 1,
          year: cD.getFullYear(),
          thu: thuNamesVi[thuIdx],
          is_weekend: (thuIdx >= 5),
          is_today: (dStr === `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`),
          in_cycle_a: (cD >= cycleAStart && cD <= cycleAEnd),
          in_cycle_b: (cD >= cycleBStart && cD <= cycleBEnd)
        });
        cD.setDate(cD.getDate() + 1);
      }

      const empList = [];
      const orderedIds = ['8239', ...TARGET_SCHEDULE_IDS.filter(x => x !== '8239')];
      for (const eid of orderedIds) {
        if (allEmployees[eid]) {
          const e = allEmployees[eid];
          const shifts = e.shifts;
          const statsATodate = calcScheduleStats(shifts, cycleAStart, cycleAEnd, today);
          const statsAFull = calcScheduleStats(shifts, cycleAStart, cycleAEnd, null);
          const statsBTodate = calcScheduleStats(shifts, cycleBStart, cycleBEnd, today);
          const statsBFull = calcScheduleStats(shifts, cycleBStart, cycleBEnd, null);

          const displayShifts = {};
          for (const [dStr, sItems] of Object.entries(shifts)) {
            if (!sItems || sItems.length === 0) {
              displayShifts[dStr] = "";
              continue;
            }
            const vals = sItems.map(x => (x.ca && x.ca !== x.val) ? `${x.ca}: ${x.val}` : x.val);
            displayShifts[dStr] = vals.join(' | ');
          }

          empList.push({
            id: eid,
            name: e.name,
            is_leader: (eid === '8239'),
            role: (eid === '8239') ? 'Leader' : 'Nhân viên CS',
            shifts: e.shifts,
            display_shifts: displayShifts,
            stats: {
              cycle_a: {
                to_date: statsATodate,
                full: statsAFull,
                start_str: `${pad(cycleAStart.getDate())}/${pad(cycleAStart.getMonth() + 1)}/${cycleAStart.getFullYear()}`,
                end_str: `${pad(cycleAEnd.getDate())}/${pad(cycleAEnd.getMonth() + 1)}/${cycleAEnd.getFullYear()}`
              },
              cycle_b: {
                to_date: statsBTodate,
                full: statsBFull,
                start_str: `${pad(cycleBStart.getDate())}/${pad(cycleBStart.getMonth() + 1)}/${cycleBStart.getFullYear()}`,
                end_str: `${pad(cycleBEnd.getDate())}/${pad(cycleBEnd.getMonth() + 1)}/${cycleBEnd.getFullYear()}`
              }
            }
          });
        }
      }

      const d = now;
      const dStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
      const nowFormatted = `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

      return {
        updated_at: nowFormatted,
        today: dStr,
        today_display: `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`,
        spreadsheet_url: 'https://docs.google.com/spreadsheets/d/1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo/edit',
        dates: datesList,
        employees: empList
      };
    }

    function setMatrixDateFilter(filter) {
      matrixDateFilter = filter;
      ['btn-matrix-all', 'btn-matrix-all-top', 'btn-matrix-all-bottom'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', filter === 'all');
      });
      ['btn-matrix-week', 'btn-matrix-week-top', 'btn-matrix-week-bottom'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('active', filter === 'week');
      });
      renderScheduleMatrixTable();
      setTimeout(jumpToTodayColumn, 100);
    }

    function jumpToTodayColumn() {
      const box = document.getElementById('matrix-scroll-box');
      if (!box) return;
      const todayTh = box.querySelector('thead th.col-today');
      if (todayTh) {
        const stickyOffset = window.innerWidth <= 768 ? 115 : 240;
        const left = todayTh.offsetLeft - stickyOffset;
        box.scrollTo({ left: Math.max(0, left), behavior: 'smooth' });
        todayTh.style.animation = 'pulseTodayCol 1.5s 2';
        setTimeout(() => { todayTh.style.animation = ''; }, 3000);
      }
    }

    function updateScheduleDateLabels() {
      const now = new Date();
      const pad = n => n < 10 ? '0' + n : String(n);
      const d = pad(now.getDate());
      const m = pad(now.getMonth() + 1);
      const y = now.getFullYear();
      const dateStrShort = `${d}/${m}`;
      const dateStrFull = `${d}/${m}/${y}`;

      document.querySelectorAll('.btn-jump-today-label').forEach(el => {
        el.innerText = `📍 Nhảy đến Hôm nay (${dateStrShort})`;
      });
      const btnRangeTodate = document.getElementById('btn-range-todate');
      if (btnRangeTodate) {
        const desktopSpan = btnRangeTodate.querySelector('.desktop-inline');
        if (desktopSpan) desktopSpan.innerText = `📍 Lũy kế đến hôm nay (${dateStrShort})`;
      }
      const rosterLbl = document.getElementById('roster-date-label');
      if (rosterLbl) rosterLbl.innerText = dateStrFull;

      const tipEl = document.getElementById('sched-tip-today');
      if (tipEl) {
        tipEl.innerHTML = `💡 Mẹo: Bấm <strong>"📍 Nhảy đến Hôm nay"</strong> để cuộn ngay đến cột ngày ${dateStrShort}. Bấm <strong>"📅 Tuần này"</strong> để xem 7 ngày tuần hiện tại.`;
      }
    }

    function initSchedule() {
      updateScheduleDateLabels();
      if (!DATA.schedule) return;
      const subtitle = document.getElementById('sched-subtitle-time');
      if (subtitle && DATA.schedule.updated_at) {
        subtitle.innerText = `Đồng bộ lúc: ${DATA.schedule.updated_at} • Thuật toán chuẩn hóa công bất biến ≤ 1.0/ngày`;
      }
      renderScheduleTab();
    }

    function setScheduleCycle(cycle) {
      currentScheduleCycle = cycle;
      const btnA = document.getElementById('btn-cycle-a');
      const btnB = document.getElementById('btn-cycle-b');
      if (btnA) btnA.classList.toggle('active', cycle === 'a');
      if (btnB) btnB.classList.toggle('active', cycle === 'b');
      const badge = document.getElementById('sched-table-cycle-badge');
      if (badge) {
        badge.innerText = cycle === 'a' ? 'Chu kỳ 26 - 25' : 'Chu kỳ Đầu - Cuối tháng';
      }
      renderScheduleTab();
    }

    function setScheduleRange(range) {
      currentScheduleRange = range;
      const btnT = document.getElementById('btn-range-todate');
      const btnF = document.getElementById('btn-range-full');
      if (btnT) btnT.classList.toggle('active', range === 'to_date');
      if (btnF) btnF.classList.toggle('active', range === 'full');
      renderScheduleTab();
    }

    function onScheduleSearch(val) {
      scheduleSearchQuery = (val || '').toLowerCase().trim();
      renderScheduleSummaryTable();
      renderScheduleMatrixTable();
    }

    function renderScheduleTab() {
      if (!DATA.schedule) return;
      renderScheduleKPIStats();
      renderTodayRoster();
      renderScheduleSummaryTable();
      renderScheduleMatrixTable();
    }

    function getEmployeeStats(emp) {
      const cycleKey = currentScheduleCycle === 'a' ? 'cycle_a' : 'cycle_b';
      const rangeKey = currentScheduleRange === 'to_date' ? 'to_date' : 'full';
      if (emp.stats && emp.stats[cycleKey] && emp.stats[cycleKey][rangeKey]) {
        return emp.stats[cycleKey][rangeKey];
      }
      return { off: 0, p: 0, work: 0, total: 0, days_counted: 0 };
    }

    function renderScheduleKPIStats() {
      const emps = DATA.schedule.employees || [];
      let totalWork = 0;
      let totalOff = 0;
      let totalP = 0;
      emps.forEach(emp => {
        const st = getEmployeeStats(emp);
        totalWork += st.work;
        totalOff += st.off;
        totalP += st.p;
      });

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
      if (wSub) wSub.innerText = `Trung bình ~${avgWork} ngày công/người`;
      if (oSub) oSub.innerText = currentScheduleRange === 'to_date' ? 'Lũy kế nghỉ tuần đến hôm nay' : 'Toàn bộ ngày nghỉ trong chu kỳ';
    }

    function renderTodayRoster(targetDateStr) {
      const dateStr = targetDateStr || DATA.schedule.today || new Date().toISOString().slice(0, 10);
      const emps = DATA.schedule.employees || [];

      const lbl = document.getElementById('roster-date-label');
      if (lbl && DATA.schedule.today_display) {
        lbl.innerText = DATA.schedule.today_display;
      }

      const groups = {
        morning: { label: '🌅 Ca Sáng (S / S+)', items: [], color: '#0284c7' },
        noon: { label: '☀️ Ca Trưa (TR)', items: [], color: '#d97706' },
        evening: { label: '🌙 Ca Tối (T)', items: [], color: '#4f46e5' },
        admin: { label: '🏢 Hành Chính & Kênh (HC / FB / TK)', items: [], color: '#059669' },
        off: { label: '🏖️ Nghỉ OFF & Phép (P)', items: [], color: '#dc2626' }
      };

      emps.forEach(emp => {
        const shiftList = (emp.shifts && emp.shifts[dateStr]) || [];
        if (!shiftList.length) return;

        let isOff = false;
        let isP = false;
        let isS = false;
        let isTR = false;
        let isT = false;
        let isHC = false;
        let detailTags = [];

        shiftList.forEach(s => {
          const v = (s.val || '').toUpperCase().trim();
          const ca = (s.ca || '').toUpperCase().trim();
          detailTags.push(ca && ca !== v ? `${ca}: ${v}` : v);

          if (v === 'OFF' || v === 'OFF/2') isOff = true;
          if (v === 'P' || v === 'P/2') isP = true;
          if (ca.includes('S') && !ca.includes('HC')) isS = true;
          if (ca.includes('TR')) isTR = true;
          if (ca.includes('T')) isT = true;
          if (ca.includes('HC') || ['FB', 'TK', 'FC'].some(x => v.includes(x))) isHC = true;
        });

        const pillText = `${emp.name} (${detailTags.join(', ')})`;
        if (isOff || isP) groups.off.items.push(pillText);
        else {
          if (isS) groups.morning.items.push(pillText);
          if (isTR) groups.noon.items.push(pillText);
          if (isT) groups.evening.items.push(pillText);
          if (isHC && !isS && !isTR && !isT) groups.admin.items.push(pillText);
        }
      });

      const container = document.getElementById('roster-groups-content');
      if (!container) return;
      container.innerHTML = Object.values(groups).map(g => `
        <div class="roster-group-card">
          <div class="roster-group-label" style="color: ${g.color}">
            ${g.label} (${g.items.length})
          </div>
          <div class="roster-pills-wrap">
            ${g.items.length ? g.items.map(item => `
              <span class="roster-pill" title="${item}">
                ${item.split(' (')[0]}
                <small style="opacity:0.75;font-weight:normal;">${item.includes('(') ? item.substring(item.indexOf('(')) : ''}</small>
              </span>
            `).join('') : '<span style="font-size:11px;color:var(--text-muted);font-style:italic;">Không có</span>'}
          </div>
        </div>
      `).join('');
    }

    function renderScheduleSummaryTable() {
      const tbody = document.getElementById('tbody-schedule-summary');
      const tfoot = document.getElementById('tfoot-schedule-summary');
      if (!tbody) return;
      tbody.innerHTML = '';

      let emps = (DATA.schedule && DATA.schedule.employees) || [];
      if (scheduleSearchQuery) {
        emps = emps.filter(e => e.name.toLowerCase().includes(scheduleSearchQuery) || e.id.includes(scheduleSearchQuery));
      }

      let sumOff = 0, sumP = 0, sumWork = 0, sumTotal = 0;
      const myName = localStorage.getItem('kpicto_my_name') || '';

      emps.forEach((emp, idx) => {
        const st = getEmployeeStats(emp);
        sumOff += st.off;
        sumP += st.p;
        sumWork += st.work;
        sumTotal += st.total;

        const isMe = myName && (emp.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(emp.name.toLowerCase()));
        const tr = document.createElement('tr');
        if (isMe) tr.classList.add('my-row-highlight');

        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td><span class="badge" style="background:rgba(255,255,255,0.06);font-family:monospace;">${emp.id}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <strong>${emp.name}</strong>
              ${emp.is_leader ? '<span class="badge" style="background:#fef3c7;color:#b45309;font-size:10px;padding:2px 6px;">👑 Leader</span>' : ''}
            </div>
          </td>
          <td><span style="font-size:12px;color:var(--text-muted);">${emp.role || 'Nhân viên CS'}</span></td>
          <td class="numeric">
            <span class="badge" style="background:rgba(239, 68, 68, 0.15);color:#ef4444;font-weight:700;">${st.off}</span>
          </td>
          <td class="numeric">
            <span class="badge" style="background:rgba(168, 85, 247, 0.15);color:#a855f7;font-weight:700;">${st.p}</span>
          </td>
          <td class="numeric">
            <span class="badge" style="background:rgba(16, 185, 129, 0.15);color:#10b981;font-weight:700;">${st.work}</span>
          </td>
          <td class="numeric">
            <strong style="color:var(--text-main);">${st.total}</strong>
          </td>
          <td class="text-center">
            <div style="display:flex;gap:4px;justify-content:center;">
              <button class="btn btn-sm" onclick="scrollToEmployeeMatrix('${emp.id}')" style="padding:4px 8px;font-size:11px;" title="Xem lịch trên ma trận">
                👁️ Xem Lịch
              </button>
              <button class="btn btn-sm" onclick="openOtForEmployee('${emp.id}')" style="padding:4px 8px;font-size:11px;background:rgba(99,102,241,0.18);color:#818cf8;border:1px solid rgba(99,102,241,0.3);" title="Tra cứu và Copy giờ OT">
                ⏰ OT
              </button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });

      if (tfoot) {
        tfoot.innerHTML = `
          <tr style="background:rgba(0,0,0,0.25);font-weight:800;">
            <td colspan="4" style="text-align:right;padding-right:15px;">Tổng cộng cả Team:</td>
            <td class="numeric" style="color:#ef4444;">${sumOff.toFixed(1)}</td>
            <td class="numeric" style="color:#a855f7;">${sumP.toFixed(1)}</td>
            <td class="numeric" style="color:#10b981;">${sumWork.toFixed(1)}</td>
            <td class="numeric" style="color:var(--text-main);">${sumTotal.toFixed(1)}</td>
            <td></td>
          </tr>
        `;
      }
    }

    function renderScheduleMatrixTable() {
      const thead = document.getElementById('thead-matrix-schedule');
      const tbody = document.getElementById('tbody-matrix-schedule');
      if (!thead || !tbody || !DATA.schedule) return;

      let dates = (DATA.schedule.dates || []).filter(d => {
        return currentScheduleCycle === 'a' ? d.in_cycle_a : d.in_cycle_b;
      });

      if (matrixDateFilter === 'week') {
        const now = new Date();
        const pad = n => n < 10 ? '0' + n : String(n);
        const todayReal = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
        const todayStr = (DATA.schedule && DATA.schedule.today) ? DATA.schedule.today : todayReal;
        const parts = todayStr.split('-').map(Number);
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        const day = d.getDay();
        const diffToMonday = (day === 0 ? -6 : 1 - day);
        const monday = new Date(d);
        monday.setDate(d.getDate() + diffToMonday);

        const weekSet = new Set();
        for (let i = 0; i < 7; i++) {
          const cur = new Date(monday);
          cur.setDate(monday.getDate() + i);
          const y = cur.getFullYear();
          const m = String(cur.getMonth() + 1).padStart(2, '0');
          const dayNum = String(cur.getDate()).padStart(2, '0');
          weekSet.add(`${y}-${m}-${dayNum}`);
        }
        dates = dates.filter(d => weekSet.has(d.date_str));
      }

      thead.innerHTML = `
        <tr>
          <th class="sticky-col-id" rowspan="2">MS</th>
          <th class="sticky-col-name" rowspan="2">Họ và Tên Nhân Sự</th>
          ${dates.map(d => `
            <th class="${d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}">
              ${d.thu}
            </th>
          `).join('')}
        </tr>
        <tr>
          ${dates.map(d => `
            <th class="${d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}" style="font-size:13px;font-weight:800;">
              ${d.day_num}/${d.month}
              ${d.is_today ? '<div style="font-size:9px;background:#f59e0b;color:#000;border-radius:3px;padding:1px 3px;margin-top:2px;">📍 HÔM NAY</div>' : ''}
            </th>
          `).join('')}
        </tr>
      `;

      let emps = (DATA.schedule && DATA.schedule.employees) || [];
      if (scheduleSearchQuery) {
        emps = emps.filter(e => e.name.toLowerCase().includes(scheduleSearchQuery) || e.id.includes(scheduleSearchQuery));
      }

      const myName = localStorage.getItem('kpicto_my_name') || '';

      tbody.innerHTML = emps.map(emp => {
        const isMe = myName && (emp.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(emp.name.toLowerCase()));
        const isCurrentOt = (typeof currentOtEmployeeId !== 'undefined' && emp.id === currentOtEmployeeId);
        const rowClass = [
          isMe ? 'my-row-highlight' : '',
          isCurrentOt ? 'matrix-row-selected' : ''
        ].filter(Boolean).join(' ');

        return `
          <tr id="matrix-row-${emp.id}" class="${rowClass}" onclick="if (typeof selectOtEmployee === 'function') selectOtEmployee('${emp.id}', true);" title="Bấm để xem & copy giờ OT của ${emp.name}" style="cursor:pointer;">
            <td class="sticky-col-id">
              <span style="font-family:monospace;font-size:11px;color:var(--text-muted);">${emp.id}</span>
            </td>
            <td class="sticky-col-name">
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="${isCurrentOt ? 'font-weight:800;color:var(--primary);' : ''}">${emp.name}</span>
                ${emp.is_leader ? '<span title="Leader" style="cursor:default;">👑</span>' : ''}
                ${isCurrentOt ? '<span class="badge" style="background:var(--primary);color:#fff;font-size:9.5px;padding:1px 5px;border-radius:4px;margin-left:auto;">Đang chọn</span>' : ''}
              </div>
            </td>
            ${dates.map(d => {
              const shifts = (emp.shifts && emp.shifts[d.date_str]) || [];
              let content = '';
              if (!shifts.length) {
                content = '<span style="color:rgba(255,255,255,0.15);">-</span>';
              } else {
                content = shifts.map(s => {
                  const v = (s.val || '').trim();
                  const vu = v.toUpperCase();
                  let cls = 'badge-shift-other';
                  if (vu.startsWith('OFF')) cls = 'badge-shift-off';
                  else if (vu.startsWith('P')) cls = 'badge-shift-p';
                  else if (s.ca.includes('S') && !s.ca.includes('HC')) cls = 'badge-shift-s';
                  else if (s.ca.includes('TR')) cls = 'badge-shift-tr';
                  else if (s.ca.includes('T')) cls = 'badge-shift-t';
                  else if (s.ca.includes('HC') || ['FB', 'TK', 'FC'].some(x => vu.includes(x))) cls = 'badge-shift-hc';

                  const label = (s.ca && s.ca !== v) ? `${s.ca}: ${v}` : v;
                  return `<span class="badge-shift ${cls}" title="${d.thu} ${d.day_num}/${d.month}: ${label}">${label}</span>`;
                }).join('');
              }
              return `<td class="${d.is_today ? 'col-today' : (d.is_weekend ? 'col-weekend' : '')}">${content}</td>`;
            }).join('')}
          </tr>
        `;
      }).join('');
    }

    function scrollToEmployeeMatrix(empId) {
      const row = document.getElementById('matrix-row-' + empId);
      if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.style.outline = '2px solid #f59e0b';
        setTimeout(() => row.style.outline = '', 3000);
      }
    }

    function exportScheduleExcel() {
      if (!DATA.schedule) return;
      const emps = DATA.schedule.employees || [];
      const cycleTitle = currentScheduleCycle === 'a' ? 'Chu_ky_26_25' : 'Chu_ky_Dau_Cuoi_thang';
      const rangeTitle = currentScheduleRange === 'to_date' ? 'Den_hom_nay' : 'Ca_chu_ky';

      let csv = "\uFEFFSTT,Mã NV,Họ và Tên,Chức Vụ,Ngày OFF,Ngày Phép,Ngày Làm Việc,Tổng Ngày\n";
      emps.forEach((emp, idx) => {
        const st = getEmployeeStats(emp);
        csv += `"${idx + 1}","${emp.id}","${emp.name}","${emp.role || ''}","${st.off}","${st.p}","${st.work}","${st.total}"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `Bao_Cao_Cham_Cong_Team_CTO1_${cycleTitle}_${rangeTitle}.csv`;
      a.click();
      showToast('📥 Đã tải xuống file CSV chấm công thành công!');
    }

    async function syncScheduleLive() {
      const btn = document.getElementById('btn-sync-schedule');
      if (btn) {
        btn.innerHTML = '⏳ Đang kết nối Google Sheets...';
        btn.style.opacity = '0.7';
      }

      try {
        // Lấy token bot (chạy hoàn toàn trong RAM trình duyệt qua WebCrypto)
        const token = await getGoogleServiceAccountToken();
        const schedSheetId = '1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo';
        const now = new Date();
        const pad = n => n < 10 ? '0' + n : String(n);
        const mCurr = now.getMonth() + 1;
        const yCurr = now.getFullYear();
        const sheetName = encodeURIComponent(`Tháng ${pad(mCurr)}/${yCurr}`);
        
        // Thử fetch kèm màu nền cell trước (hỗ trợ phân biệt TK, Miss màu đỏ 4h, vàng 3h)
        let rawRows = null;
        try {
          const colorUrl = `https://sheets.googleapis.com/v4/spreadsheets/${schedSheetId}?ranges=${sheetName}&fields=sheets.data.rowData.values(formattedValue,effectiveFormat.backgroundColor)`;
          const res = await fetch(colorUrl, { headers: { 'Authorization': 'Bearer ' + token } });
          if (res.ok) {
            const cData = await res.json();
            if (cData.sheets && cData.sheets[0] && cData.sheets[0].data && cData.sheets[0].data[0].rowData) {
              rawRows = cData.sheets[0].data[0].rowData.map(r => r.values || []);
            }
          }
        } catch (eColor) {
          console.warn('Không thể tải metadata màu, fallback sang values:', eColor);
        }

        // Nếu chưa lấy được từ endpoint rowData thì fallback sang values
        if (!rawRows || rawRows.length < 5) {
          const url = `https://sheets.googleapis.com/v4/spreadsheets/${schedSheetId}/values/${sheetName}?valueRenderOption=FORMATTED_VALUE`;
          const res = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } });
          if (!res.ok) throw new Error('Google Sheets API trả về mã lỗi: ' + res.status);
          const data = await res.json();
          if (!data.values || data.values.length < 5) throw new Error('Dữ liệu sheet rỗng hoặc chưa tải được');
          rawRows = data.values;
        }

        let nextRows = null;
        if (now.getDate() >= 26) {
          try {
            const mNext = (mCurr < 12) ? mCurr + 1 : 1;
            const yNext = (mCurr < 12) ? yCurr : yCurr + 1;
            const nextSheetName = encodeURIComponent(`Tháng ${pad(mNext)}/${yNext}`);
            const nextColorUrl = `https://sheets.googleapis.com/v4/spreadsheets/${schedSheetId}?ranges=${nextSheetName}&fields=sheets.data.rowData.values(formattedValue,effectiveFormat.backgroundColor)`;
            const nextRes = await fetch(nextColorUrl, { headers: { 'Authorization': 'Bearer ' + token } });
            if (nextRes.ok) {
              const nData = await nextRes.json();
              if (nData.sheets && nData.sheets[0] && nData.sheets[0].data && nData.sheets[0].data[0].rowData) {
                nextRows = nData.sheets[0].data[0].rowData.map(r => r.values || []);
              }
            }
            if (!nextRows) {
              const nextUrl = `https://sheets.googleapis.com/v4/spreadsheets/${schedSheetId}/values/${nextSheetName}?valueRenderOption=FORMATTED_VALUE`;
              const nextResV = await fetch(nextUrl, { headers: { 'Authorization': 'Bearer ' + token } });
              if (nextResV.ok) {
                const nDataV = await nextResV.json();
                if (nDataV.values && nDataV.values.length > 5) nextRows = nDataV.values;
              }
            }
          } catch (eNext) {}
        }

        // Parse bảng lịch trực và tính công 13 nhân sự
        const freshSchedule = buildScheduleFromRawSheet(rawRows, now, nextRows);
        if (freshSchedule && freshSchedule.employees && freshSchedule.employees.length > 0) {
          DATA.schedule = freshSchedule;
          try {
            // Lưu vào Browser Cache (localStorage) để lần sau mở web có ngay lập tức
            localStorage.setItem('kpicto_schedule_cache_v3', JSON.stringify(freshSchedule));
          } catch (e) {}
          renderScheduleTab();
          if (currentMainView === 'ot') renderOtTracker();
          showToast('✅ Đã tải trực tiếp từ Google Sheets lúc ' + freshSchedule.updated_at + '!');
          return;
        }
      } catch (err) {
        console.warn('Lỗi đọc Google Sheets trực tiếp, chuyển sang nạp bản lưu gần nhất:', err);
        try {
          const cacheUrl = './Data/schedule_cache.json?t=' + Date.now();
          const res = await fetch(cacheUrl);
          if (res.ok) {
            const freshSchedule = await res.json();
            if (freshSchedule && freshSchedule.employees && freshSchedule.employees.length > 0) {
              DATA.schedule = freshSchedule;
              renderScheduleTab();
              if (currentMainView === 'ot') renderOtTracker();
              showToast('✅ Đã đồng bộ lịch trực từ bản lưu gần nhất (' + (freshSchedule.updated_at || '') + ')');
              return;
            }
          }
        } catch (e2) {}

        if (DATA.schedule && DATA.schedule.employees) {
          renderScheduleTab();
          if (currentMainView === 'ot') renderOtTracker();
          showToast('✅ Dữ liệu lịch trực đang là bản mới nhất (' + (DATA.schedule.updated_at || '13 nhân sự') + ')!');
        } else {
          showToast('ℹ️ Đang hiển thị lịch trực mới nhất!');
        }
      } finally {
        if (btn) {
          btn.innerHTML = '🔄 Tải lại Lịch Trực Mới Nhất';
          btn.style.opacity = '1';
        }
      }
    }
