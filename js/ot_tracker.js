/* ============================================================
       OVERTIME TRACKER MODULE (TRA CỨU & COPY GIỜ OT)
       Chu kỳ 26 tháng trước đến 25 tháng này từ Google Sheets
       ============================================================ */
    let currentOtEmployeeId = '8131'; // Mặc định Lê Thị Trúc Linh
    let currentModalEmpMa = '';
    let otSearchDebounceTimer = null;
    let otModifiedCells = {}; // Lưu trữ chỉnh sửa thủ công của người dùng

    function normalizeText(value) {
      return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[đĐ]/g, 'd')
        .toLowerCase()
        .trim();
    }

    function isNoOT(v) {
      const s = String(v || '').trim().toUpperCase();
      return !s || ['X', '-', 'OFF', 'OFF/2', 'P'].includes(s) || s.startsWith('CH');
    }

    function getCycleDatesForOT() {
      if (DATA.schedule && DATA.schedule.dates && DATA.schedule.dates.length > 0) {
        const cA = DATA.schedule.dates.filter(d => d.in_cycle_a);
        if (cA.length > 0) return cA;
      }
      // Fallback nếu chưa có dates
      const now = new Date();
      const y = now.getFullYear();
      const m = now.getMonth() + 1;
      const isAfter26 = now.getDate() >= 26;
      const startD = isAfter26 ? new Date(y, m - 1, 26) : new Date(y, m - 2, 26);
      const endD = isAfter26 ? new Date(y, m, 25) : new Date(y, m - 1, 25);
      const dates = [];
      const c = new Date(startD.getTime());
      const pad = n => n < 10 ? '0' + n : String(n);
      const thuVi = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
      while (c <= endD) {
        dates.push({
          date_str: `${c.getFullYear()}-${pad(c.getMonth() + 1)}-${pad(c.getDate())}`,
          day_num: c.getDate(),
          month: c.getMonth() + 1,
          year: c.getFullYear(),
          thu: thuVi[c.getDay()],
          is_weekend: (c.getDay() === 0 || c.getDay() === 6),
          is_today: (c.toDateString() === now.toDateString()),
          in_cycle_a: true
        });
        c.setDate(c.getDate() + 1);
      }
      return dates;
    }

    // ============================================================
    // BỘ CHỌN KHOẢNG NGÀY SAO CHÉP (DATE RANGE COPY)
    // ============================================================
    let otCopyFromIndex = 0;
    let otCopyToIndex = -1; // -1: Mặc định chọn đến hết chu kỳ (dates.length - 1)

    function initOtDateRange(dates) {
      const fromSel = document.getElementById('ot-range-from');
      const toSel = document.getElementById('ot-range-to');
      if (!fromSel || !toSel || !dates || dates.length === 0) return;

      const pad = n => n < 10 ? '0' + n : String(n);
      const optionsHtml = dates.map((d, idx) => {
        return `<option value="${idx}">${pad(d.day_num)}/${pad(d.month)} (${d.thu})${d.is_today ? ' • Hôm nay' : ''}</option>`;
      }).join('');

      fromSel.innerHTML = optionsHtml;
      toSel.innerHTML = optionsHtml;

      if (otCopyToIndex < 0 || otCopyToIndex >= dates.length) {
        otCopyToIndex = dates.length - 1;
      }
      if (otCopyFromIndex < 0 || otCopyFromIndex >= dates.length) {
        otCopyFromIndex = 0;
      }
      if (otCopyFromIndex > otCopyToIndex) {
        otCopyFromIndex = 0;
      }

      fromSel.value = String(otCopyFromIndex);
      toSel.value = String(otCopyToIndex);

      updateOtDateRangeUI(dates);
    }

    function onOtDateRangeChange() {
      const fromSel = document.getElementById('ot-range-from');
      const toSel = document.getElementById('ot-range-to');
      if (!fromSel || !toSel) return;

      let fromIdx = parseInt(fromSel.value, 10);
      let toIdx = parseInt(toSel.value, 10);

      if (isNaN(fromIdx)) fromIdx = 0;
      if (isNaN(toIdx)) toIdx = 0;

      if (fromIdx > toIdx) {
        toIdx = fromIdx;
        toSel.value = String(toIdx);
      }

      otCopyFromIndex = fromIdx;
      otCopyToIndex = toIdx;

      const dates = getCycleDatesForOT();
      updateOtDateRangeUI(dates);
    }

    function setOtCopyRangePreset(preset) {
      const dates = getCycleDatesForOT();
      if (!dates || dates.length === 0) return;

      if (preset === 'full') {
        otCopyFromIndex = 0;
        otCopyToIndex = dates.length - 1;
      } else if (preset === 'today') {
        const todayIdx = dates.findIndex(d => d.is_today);
        otCopyFromIndex = 0;
        otCopyToIndex = (todayIdx >= 0) ? todayIdx : (dates.length - 1);
      }

      const fromSel = document.getElementById('ot-range-from');
      const toSel = document.getElementById('ot-range-to');
      if (fromSel) fromSel.value = String(otCopyFromIndex);
      if (toSel) toSel.value = String(otCopyToIndex);

      updateOtDateRangeUI(dates);
      const pad = n => n < 10 ? '0' + n : String(n);
      const fromD = dates[otCopyFromIndex];
      const toD = dates[otCopyToIndex];
      if (typeof showToast === 'function' && fromD && toD) {
        showToast(`📅 Đã chọn khoảng ngày copy: ${pad(fromD.day_num)}/${pad(fromD.month)} ➔ ${pad(toD.day_num)}/${pad(toD.month)} (${otCopyToIndex - otCopyFromIndex + 1} ngày).`);
      }
    }

    function updateOtDateRangeUI(dates) {
      if (!dates || dates.length === 0) return;
      const maxIdx = dates.length - 1;
      const fromIdx = Math.max(0, Math.min(otCopyFromIndex, maxIdx));
      const toIdx = Math.max(fromIdx, Math.min(otCopyToIndex < 0 ? maxIdx : otCopyToIndex, maxIdx));
      const count = toIdx - fromIdx + 1;

      const pad = n => n < 10 ? '0' + n : String(n);
      const fromD = dates[fromIdx];
      const toD = dates[toIdx];

      const badge = document.getElementById('ot-range-summary-badge');
      if (badge && fromD && toD) {
        badge.innerHTML = `Đang chọn: <strong>${count} ngày</strong> (${pad(fromD.day_num)}/${pad(fromD.month)} ➔ ${pad(toD.day_num)}/${pad(toD.month)})`;
      }

      const table = document.getElementById('ot-compare-table');
      if (table) {
        const allRows = table.querySelectorAll('thead tr, tbody tr');
        allRows.forEach(row => {
          const cells = row.children;
          for (let i = 0; i < dates.length; i++) {
            const cell = cells[i + 1];
            if (cell) {
              const inRange = (i >= fromIdx && i <= toIdx);
              cell.classList.toggle('in-copy-range', inRange);
              cell.classList.toggle('out-of-copy-range', !inRange);
            }
          }
        });
      }
    }

    function calculateOTForEmp(emp, dates) {
      if (!emp || !emp.shifts) {
        return { name: emp ? emp.name : '', id: emp ? emp.id : '', totalHours: 0, totalS: 0, totalTR: 0, totalT: 0, daily: [] };
      }

      let totalHours = 0, totalS = 0, totalTR = 0, totalT = 0;
      const daily = [];

      dates.forEach(dObj => {
        const dStr = dObj.date_str;
        const shifts = emp.shifts[dStr] || [];
        const getShiftVal = (label) => {
          const it = shifts.find(s => s.ca === label || (label === 'HC-S' && s.ca === 'HCS') || (label === 'HC-C' && s.ca === 'HCC'));
          return it ? String(it.val || '').trim().toUpperCase() : '';
        };

        const sVal = getShiftVal('S');
        const hcsVal = getShiftVal('HC-S');
        const trVal = getShiftVal('TR');
        const hccVal = getShiftVal('HC-C');
        const tVal = getShiftVal('T');

        const four = [sVal, hcsVal, trVal, hccVal];
        const allFourOff = four.every(v => v === 'OFF');
        const isHalfDayOff = ['OFF/2', 'P/2'].includes(hccVal);
        const isCH = (hcsVal === '' && hccVal !== '' && !allFourOff && !isHalfDayOff) || tVal.startsWith('CH');

        const five = [sVal, hcsVal, trVal, hccVal, tVal];
        const isFullDayLeave = five.some(v => v === 'P');

        let sHours = 0, trHours = 0, tHours = 0;
        const dayItems = [];

        if (!isFullDayLeave) {
          if (!isNoOT(sVal)) {
            sHours = 1;
            dayItems.push({ column: 'S', code: sVal, hours: 1 });
          }
          if (!isNoOT(trVal)) {
            trHours = 1;
            dayItems.push({ column: 'TR', code: trVal, hours: 1 });
          }
          if (!isCH && !isNoOT(tVal)) {
            const tShiftObj = shifts.find(s => s.ca === 'T');
            const colorType = tShiftObj ? (tShiftObj.colorType || '') : '';

            // 1. "có CH ko tính OT nhé"
            if (tVal.startsWith('CH')) {
              tHours = 0;
            }
            // 2. Ca đêm N = 4 tiếng chuẩn 100%
            else if (tVal === 'N') {
              tHours = 4;
            }
            // 3. Ca tối T = 3 tiếng chuẩn 100%
            else if (tVal === 'T') {
              tHours = 3;
            }
            // 4. Màu vàng: TK, Miss, FC màu vàng tính 3 tiếng
            else if (colorType === 'YELLOW') {
              tHours = 3;
            }
            // 5. Màu đỏ: TK, Miss, FC, FB... màu đỏ tính 4 tiếng
            else if (colorType === 'RED') {
              tHours = 4;
            }
            // 6. Mặc định khi không có màu (hoặc màu trắng)
            else if (tVal.startsWith('FC') || tVal.startsWith('FB') || tVal === 'TK') {
              tHours = 4;
            }
            else if (tVal === 'MISS') {
              tHours = 3;
            }

            if (tHours > 0) {
              dayItems.push({ column: 'T', code: tVal, hours: tHours });
            }
          }
        }

        // Áp dụng chỉnh sửa thủ công của người dùng (nếu có)
        const modKeyPrefix = `${emp.id}_${dStr}_`;
        if (otModifiedCells[modKeyPrefix + 'T'] !== undefined) tHours = otModifiedCells[modKeyPrefix + 'T'];
        if (otModifiedCells[modKeyPrefix + 'TR'] !== undefined) trHours = otModifiedCells[modKeyPrefix + 'TR'];
        if (otModifiedCells[modKeyPrefix + 'S'] !== undefined) sHours = otModifiedCells[modKeyPrefix + 'S'];

        const dayHours = sHours + trHours + tHours;
        totalS += sHours;
        totalTR += trHours;
        totalT += tHours;
        totalHours += dayHours;

        daily.push({
          dateStr: dStr,
          day: dObj.day_num,
          month: dObj.month,
          year: dObj.year,
          thu: dObj.thu,
          is_weekend: dObj.is_weekend,
          is_today: dObj.is_today,
          shifts: dayItems,
          hours: dayHours,
          sHours,
          trHours,
          tHours
        });
      });

      return {
        name: emp.name,
        id: emp.id,
        totalHours,
        totalS,
        totalTR,
        totalT,
        daily
      };
    }

    function renderOtTracker() {
      const emps = (DATA.schedule && DATA.schedule.employees) || [];
      if (!emps || emps.length === 0) return;

      // Tìm nhân viên hiện tại
      let emp = emps.find(e => e.id === currentOtEmployeeId);
      if (!emp) {
        emp = emps[0];
        currentOtEmployeeId = emp.id;
      }

      // Render Chips nhân viên
      const chipsEl = document.getElementById('ot-quick-chips');
      if (chipsEl) {
        chipsEl.innerHTML = emps.map(e => `
          <button type="button" class="ot-chip ${e.id === currentOtEmployeeId ? 'active' : ''}" onclick="selectOtEmployee('${e.id}')">
            ${e.name.split(' ').slice(-2).join(' ')} (${e.id})
          </button>
        `).join('');
      }

      // Render & đồng bộ Select box nhân viên
      const selEl = document.getElementById('ot-select-employee');
      if (selEl) {
        if (selEl.options.length === 0 || selEl.getAttribute('data-loaded') !== 'true') {
          selEl.innerHTML = emps.map(e => `
            <option value="${e.id}" ${e.id === currentOtEmployeeId ? 'selected' : ''}>
              ${e.is_leader ? '👑 ' : ''}${e.id} - ${e.name} ${e.is_leader ? '(Leader)' : ''}
            </option>
          `).join('');
          selEl.setAttribute('data-loaded', 'true');
        } else {
          selEl.value = currentOtEmployeeId;
        }
      }

      // Input tìm kiếm hiện tên
      const inp = document.getElementById('ot-target-name');
      if (inp) {
        inp.value = `${emp.id} - ${emp.name}`;
      }

      const dates = getCycleDatesForOT();
      const otResult = calculateOTForEmp(emp, dates);

      // Cập nhật Header & Stats
      const nameEl = document.getElementById('ot-employee-name');
      if (nameEl) nameEl.innerText = `${emp.id} - ${emp.name} ${emp.is_leader ? '👑' : ''}`;

      const periodEl = document.getElementById('ot-cycle-period');
      if (periodEl && dates.length > 0) {
        const firstD = dates[0];
        const lastD = dates[dates.length - 1];
        const pad = n => n < 10 ? '0' + n : String(n);
        periodEl.innerText = `Chu kỳ chấm công: ${pad(firstD.day_num)}/${pad(firstD.month)}/${firstD.year} – ${pad(lastD.day_num)}/${pad(lastD.month)}/${lastD.year} (${dates.length} ngày)`;
      }

      document.getElementById('ot-total-hours').innerText = otResult.totalHours + ' giờ';
      document.getElementById('ot-total-s').innerText = otResult.totalS + ' giờ';
      document.getElementById('ot-total-tr').innerText = otResult.totalTR + ' giờ';
      document.getElementById('ot-total-t').innerText = otResult.totalT + ' giờ';

      // Khởi tạo & đồng bộ bộ chọn khoảng ngày copy
      initOtDateRange(dates);

      // Render Bảng Ma trận Hàng ngang Đối chiếu Lịch trực vs Giờ OT (tích hợp Chỉnh sửa & 1-Click Copy)
      renderOtCompareTable(emp, otResult, dates);

      // Render bảng chi tiết theo ngày (cho compatibility nếu element tồn tại)
      const tbodyDaily = document.getElementById('ot-daily-rows');
      const emptyDailyEl = document.getElementById('ot-empty-result');
      if (tbodyDaily) {
        tbodyDaily.innerHTML = '';
        const activeDays = otResult.daily.filter(d => d.hours > 0);
        if (emptyDailyEl) emptyDailyEl.style.display = (activeDays.length === 0) ? 'block' : 'none';

        activeDays.forEach(d => {
          const tr = document.createElement('tr');
          const pad = n => n < 10 ? '0' + n : String(n);
          const dFmt = `${pad(d.day)}/${pad(d.month)}/${d.year}`;
          
          const shiftBadges = [];
          if (d.sHours > 0) shiftBadges.push(`<span class="badge" style="background:rgba(245,158,11,0.15);color:#f59e0b;font-weight:700;">Ca Sáng (S): ${d.sHours}h</span>`);
          if (d.trHours > 0) shiftBadges.push(`<span class="badge" style="background:rgba(56,189,248,0.15);color:#38bdf8;font-weight:700;">Ca Trưa (TR): ${d.trHours}h</span>`);
          if (d.tHours > 0) shiftBadges.push(`<span class="badge" style="background:rgba(192,132,252,0.15);color:#c084fc;font-weight:700;">Ca Tối (T): ${d.tHours}h</span>`);

          tr.innerHTML = `
            <td><strong>${dFmt}</strong></td>
            <td><span class="badge" style="background:${d.is_weekend ? 'rgba(239,68,68,0.15);color:#ef4444' : 'rgba(255,255,255,0.06)'}">${d.thu}</span></td>
            <td><div style="display:flex;gap:6px;flex-wrap:wrap;">${shiftBadges.join('')}</div></td>
            <td class="numeric" style="text-align:right;"><strong style="color:var(--success);font-size:14px;">${d.hours}h</strong></td>
          `;
          tbodyDaily.appendChild(tr);
        });
      }

      // Render Ma Trận Lịch Trực Cả Tháng Toàn Team (Gắn từ tab Lịch trực qua)
      if (typeof renderScheduleMatrixTable === 'function') {
        renderScheduleMatrixTable();
      }
      renderOtTeamSummaryTable(emps, dates);
    }

    let showOtCompareSubRows = true;

    function toggleOtCompareDetail() {
      showOtCompareSubRows = !showOtCompareSubRows;
      const subRows = document.querySelectorAll('.row-sub-shift');
      subRows.forEach(r => {
        r.style.display = showOtCompareSubRows ? '' : 'none';
      });
      const lbl = document.getElementById('lbl-toggle-ot-cmp-detail');
      if (lbl) {
        lbl.innerText = showOtCompareSubRows ? 'Thu Gọn (2 Dòng)' : 'Xem Chi Tiết Cả 3 Ca';
      }
    }

    function jumpToOtTodayColumn() {
      const todayCell = document.querySelector('#ot-compare-table .col-today, #ot-compare-table .th-today');
      if (todayCell) {
        todayCell.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      } else {
        if (typeof showToast === 'function') {
          showToast('Hôm nay không nằm trong chu kỳ này hoặc không có dữ liệu.');
        }
      }
    }

    function renderOtCompareTable(emp, otResult, dates) {
      const targetEmp = emp;
      const table = document.getElementById('ot-compare-table');
      if (!table) return;
      table.innerHTML = '';

      const emptyDailyEl = document.getElementById('ot-empty-result');
      if (emptyDailyEl) {
        emptyDailyEl.style.display = (otResult.totalHours === 0) ? 'block' : 'none';
      }

      const maxIdx = dates.length - 1;
      const fromIdx = Math.max(0, Math.min(otCopyFromIndex, maxIdx));
      const toIdx = Math.max(fromIdx, Math.min(otCopyToIndex < 0 ? maxIdx : otCopyToIndex, maxIdx));

      // 1. THEAD
      const thead = document.createElement('thead');
      const trHead = document.createElement('tr');

      const thLabel = document.createElement('th');
      thLabel.className = 'cmp-label-cell';
      thLabel.innerHTML = `
        <div style="font-size:11.5px;font-weight:800;color:var(--text-main);letter-spacing:0.5px;">NGÀY / CHU KỲ</div>
        <div style="font-size:10px;color:var(--text-muted);font-weight:500;margin-top:2px;">(26 ➔ 25)</div>
      `;
      trHead.appendChild(thLabel);

      dates.forEach((d, i) => {
        const th = document.createElement('th');
        if (d.is_weekend) th.classList.add('th-weekend');
        if (d.is_today) th.classList.add('th-today');
        const inRange = (i >= fromIdx && i <= toIdx);
        th.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');
        th.innerHTML = `<span class="cmp-day-num">${d.day_num}</span><span class="cmp-day-thu">${d.thu}</span>`;
        th.title = `${d.thu} - ${d.date_str}`;
        trHead.appendChild(th);
      });

      const thTotal = document.createElement('th');
      thTotal.className = 'cmp-total-cell';
      thTotal.innerHTML = `
        <div style="font-size:11.5px;font-weight:800;color:var(--text-main);">TỔNG CỘNG</div>
        <div style="font-size:10px;color:var(--text-muted);font-weight:500;margin-top:2px;">Chu kỳ</div>
      `;
      trHead.appendChild(thTotal);
      thead.appendChild(trHead);
      table.appendChild(thead);

      // 2. TBODY
      const tbody = document.createElement('tbody');

      // --- HÀNG 1: 📅 LỊCH TRỰC GỐC (Ở TRÊN) ---
      const trSched = document.createElement('tr');
      trSched.className = 'row-sched';

      const tdSchedLabel = document.createElement('td');
      tdSchedLabel.className = 'cmp-label-cell';
      tdSchedLabel.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:15px;">📅</span>
          <span style="font-weight:700;color:var(--text-main);">Lịch Trực Gốc</span>
        </div>
        <div style="font-size:10.5px;color:var(--text-muted);font-weight:normal;margin-top:2px;">(Ca làm việc trên lịch)</div>
      `;
      trSched.appendChild(tdSchedLabel);

      let workCount = 0, offCount = 0, pCount = 0;

      dates.forEach((d, i) => {
        const td = document.createElement('td');
        if (d.is_today) td.classList.add('col-today');
        if (d.is_weekend) td.classList.add('col-weekend');
        const inRange = (i >= fromIdx && i <= toIdx);
        td.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');

        const rawShifts = (targetEmp && targetEmp.shifts && targetEmp.shifts[d.date_str]) || [];
        const INVALID_CA_KEYWORDS = ['tổng', 'tong', 'sl ', 'sl\n', 'overtime', 'ot\n', 'ot ', 'chiều', 'chưa tính', 'đã tính'];
        const shifts = rawShifts.filter(s => {
          const ca = (s.ca || '').toLowerCase().trim();
          return !INVALID_CA_KEYWORDS.some(kw => ca.includes(kw));
        });
        const vals = shifts.map(s => (s.val || '').toUpperCase().trim());
        if (vals.some(v => v.startsWith('P'))) pCount++;
        else if (vals.some(v => v.startsWith('OFF'))) offCount++;
        else if (vals.length > 0) workCount++;

        if (!shifts.length) {
          td.innerHTML = '<span class="ot-cmp-dash">-</span>';
        } else {
          const badgesHtml = shifts.map(s => {
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
          td.innerHTML = `<div class="ot-cmp-badges">${badgesHtml}</div>`;
        }
        trSched.appendChild(td);
      });

      const tdSchedTotal = document.createElement('td');
      tdSchedTotal.className = 'cmp-total-cell';
      tdSchedTotal.innerHTML = `
        <div style="font-size:11px;line-height:1.4;">
          <span style="color:var(--text-main);font-weight:700;">${workCount} làm</span><br>
          <span style="color:#f87171;">${offCount} OFF</span> • <span style="color:#c084fc;">${pCount} P</span>
        </div>
      `;
      trSched.appendChild(tdSchedTotal);

      // --- HÀNG 2: 🌙 OT CA TỐI (T) ---
      const trT = document.createElement('tr');
      trT.className = 'row-sub-shift row-ot-t';
      if (!showOtCompareSubRows) trT.style.display = 'none';

      const tdTLabel = document.createElement('td');
      tdTLabel.className = 'cmp-label-cell';
      tdTLabel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
          <div style="padding-left:6px;">
            <div style="font-weight:700;color:#c084fc;">🌙 Ca Tối (T)</div>
            <div style="font-size:10px;color:var(--text-muted);">Gõ số giờ (3h, 4h)</div>
          </div>
          <button type="button" class="ot-row-copy-btn" onclick="copyOtRow('T', this)" title="Copy hàng Ca Tối theo khoảng ngày đã chọn để dán vào Google Sheets">
            🗐 Copy
          </button>
        </div>
      `;
      trT.appendChild(tdTLabel);

      otResult.daily.forEach((d, i) => {
        const td = document.createElement('td');
        td.className = 'ot-editable-cell';
        td.setAttribute('contenteditable', 'true');
        td.setAttribute('data-emp-id', emp.id);
        td.setAttribute('data-date-str', d.dateStr);
        td.setAttribute('data-shift-type', 'T');
        if (d.is_today) td.classList.add('col-today');
        if (d.is_weekend) td.classList.add('col-weekend');
        const inRange = (i >= fromIdx && i <= toIdx);
        td.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');

        if (d.tHours > 0) {
          td.innerHTML = `<span class="ot-cmp-chip-t">${d.tHours}</span>`;
          td.classList.add('has-val');
        } else {
          td.innerHTML = '<span class="ot-cmp-dash">-</span>';
        }

        td.addEventListener('focus', function() {
          if (this.innerText.trim() === '-') this.innerText = '';
        });
        td.addEventListener('blur', function() {
          if (!this.innerText.trim()) this.innerHTML = '<span class="ot-cmp-dash">-</span>';
        });
        td.addEventListener('input', function() {
          handleOtCompareCellEdit(this);
        });

        trT.appendChild(td);
      });

      const tdTTotal = document.createElement('td');
      tdTTotal.className = 'cmp-total-cell';
      tdTTotal.innerHTML = `<strong class="ot-cmp-chip-t" style="font-size:13px;">${otResult.totalT}h</strong>`;
      trT.appendChild(tdTTotal);

      // --- HÀNG 3: ☀️ OT CA TRƯA (TR) ---
      const trTR = document.createElement('tr');
      trTR.className = 'row-sub-shift row-ot-tr';
      if (!showOtCompareSubRows) trTR.style.display = 'none';

      const tdTRLabel = document.createElement('td');
      tdTRLabel.className = 'cmp-label-cell';
      tdTRLabel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
          <div style="padding-left:6px;">
            <div style="font-weight:700;color:#38bdf8;">☀️ Ca Trưa (TR)</div>
            <div style="font-size:10px;color:var(--text-muted);">Gõ số giờ (1h)</div>
          </div>
          <button type="button" class="ot-row-copy-btn" onclick="copyOtRow('TR', this)" title="Copy hàng Ca Trưa theo khoảng ngày đã chọn để dán vào Google Sheets">
            🗐 Copy
          </button>
        </div>
      `;
      trTR.appendChild(tdTRLabel);

      otResult.daily.forEach((d, i) => {
        const td = document.createElement('td');
        td.className = 'ot-editable-cell';
        td.setAttribute('contenteditable', 'true');
        td.setAttribute('data-emp-id', emp.id);
        td.setAttribute('data-date-str', d.dateStr);
        td.setAttribute('data-shift-type', 'TR');
        if (d.is_today) td.classList.add('col-today');
        if (d.is_weekend) td.classList.add('col-weekend');
        const inRange = (i >= fromIdx && i <= toIdx);
        td.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');

        if (d.trHours > 0) {
          td.innerHTML = `<span class="ot-cmp-chip-tr">${d.trHours}</span>`;
          td.classList.add('has-val');
        } else {
          td.innerHTML = '<span class="ot-cmp-dash">-</span>';
        }

        td.addEventListener('focus', function() {
          if (this.innerText.trim() === '-') this.innerText = '';
        });
        td.addEventListener('blur', function() {
          if (!this.innerText.trim()) this.innerHTML = '<span class="ot-cmp-dash">-</span>';
        });
        td.addEventListener('input', function() {
          handleOtCompareCellEdit(this);
        });

        trTR.appendChild(td);
      });

      const tdTRTotal = document.createElement('td');
      tdTRTotal.className = 'cmp-total-cell';
      tdTRTotal.innerHTML = `<strong class="ot-cmp-chip-tr" style="font-size:13px;">${otResult.totalTR}h</strong>`;
      trTR.appendChild(tdTRTotal);

      // --- HÀNG 4: 🌅 OT CA SÁNG (S) ---
      const trS = document.createElement('tr');
      trS.className = 'row-sub-shift row-ot-s';
      if (!showOtCompareSubRows) trS.style.display = 'none';

      const tdSLabel = document.createElement('td');
      tdSLabel.className = 'cmp-label-cell';
      tdSLabel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
          <div style="padding-left:6px;">
            <div style="font-weight:700;color:#f59e0b;">🌅 Ca Sáng (S)</div>
            <div style="font-size:10px;color:var(--text-muted);">Gõ số giờ (1h)</div>
          </div>
          <button type="button" class="ot-row-copy-btn" onclick="copyOtRow('S', this)" title="Copy hàng Ca Sáng theo khoảng ngày đã chọn để dán vào Google Sheets">
            🗐 Copy
          </button>
        </div>
      `;
      trS.appendChild(tdSLabel);

      otResult.daily.forEach((d, i) => {
        const td = document.createElement('td');
        td.className = 'ot-editable-cell';
        td.setAttribute('contenteditable', 'true');
        td.setAttribute('data-emp-id', emp.id);
        td.setAttribute('data-date-str', d.dateStr);
        td.setAttribute('data-shift-type', 'S');
        if (d.is_today) td.classList.add('col-today');
        if (d.is_weekend) td.classList.add('col-weekend');
        const inRange = (i >= fromIdx && i <= toIdx);
        td.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');

        if (d.sHours > 0) {
          td.innerHTML = `<span class="ot-cmp-chip-s">${d.sHours}</span>`;
          td.classList.add('has-val');
        } else {
          td.innerHTML = '<span class="ot-cmp-dash">-</span>';
        }

        td.addEventListener('focus', function() {
          if (this.innerText.trim() === '-') this.innerText = '';
        });
        td.addEventListener('blur', function() {
          if (!this.innerText.trim()) this.innerHTML = '<span class="ot-cmp-dash">-</span>';
        });
        td.addEventListener('input', function() {
          handleOtCompareCellEdit(this);
        });

        trS.appendChild(td);
      });

      const tdSTotal = document.createElement('td');
      tdSTotal.className = 'cmp-total-cell';
      tdSTotal.innerHTML = `<strong class="ot-cmp-chip-s" style="font-size:13px;">${otResult.totalS}h</strong>`;
      trS.appendChild(tdSTotal);

      // --- HÀNG 5: ⚡ TỔNG GIỜ OT (Ở DƯỚI CÙNG 3 CA, KHÔNG CÓ NÚT COPY) ---
      const trOt = document.createElement('tr');
      trOt.className = 'row-ot-total';

      const tdOtLabel = document.createElement('td');
      tdOtLabel.className = 'cmp-label-cell';
      tdOtLabel.innerHTML = `
        <div style="font-weight:800;color:var(--success);display:flex;align-items:center;gap:5px;">
          <span>⚡</span>
          <span>Tổng Giờ OT</span>
        </div>
        <div style="font-size:10px;color:var(--text-muted);">(Tổng cộng cả 3 ca)</div>
      `;
      trOt.appendChild(tdOtLabel);

      otResult.daily.forEach((d, i) => {
        const td = document.createElement('td');
        if (d.is_today) td.classList.add('col-today');
        if (d.is_weekend) td.classList.add('col-weekend');
        const inRange = (i >= fromIdx && i <= toIdx);
        td.classList.add(inRange ? 'in-copy-range' : 'out-of-copy-range');

        if (d.hours > 0) {
          td.classList.add('has-ot');
          td.innerHTML = `<div class="ot-cmp-total-badge">${d.hours}h</div>`;
          td.title = `${d.thu} ${d.day}/${d.month}: ${d.hours}h OT (S:${d.sHours}h, TR:${d.trHours}h, T:${d.tHours}h)`;
        } else {
          td.innerHTML = '<span class="ot-cmp-dash">-</span>';
        }
        trOt.appendChild(td);
      });

      const tdOtTotal = document.createElement('td');
      tdOtTotal.className = 'cmp-total-cell';
      tdOtTotal.innerHTML = `<strong style="font-size:16px;color:var(--primary);font-weight:800;">${otResult.totalHours} giờ</strong>`;
      trOt.appendChild(tdOtTotal);

      // Sắp xếp thứ tự: Lịch Gốc -> Ca Tối -> Ca Trưa -> Ca Sáng -> Tổng Giờ OT (Ở Dưới Cùng)
      tbody.appendChild(trSched);
      tbody.appendChild(trT);
      tbody.appendChild(trTR);
      tbody.appendChild(trS);
      tbody.appendChild(trOt);

      table.appendChild(tbody);
      updateOtDateRangeUI(dates);
    }

    function handleOtCompareCellEdit(cell) {
      const empId = cell.getAttribute('data-emp-id');
      const dateStr = cell.getAttribute('data-date-str');
      const shiftType = cell.getAttribute('data-shift-type');
      const textVal = cell.innerText.trim();
      const numVal = parseFloat(textVal) || 0;

      const modKey = `${empId}_${dateStr}_${shiftType}`;
      otModifiedCells[modKey] = numVal;

      if (numVal > 0) {
        cell.classList.add('has-val');
      } else {
        cell.classList.remove('has-val');
      }

      // Recalculate
      const dates = getCycleDatesForOT();
      const emps = (DATA.schedule && DATA.schedule.employees) || [];
      const emp = emps.find(e => e.id === currentOtEmployeeId);
      if (!emp) return;

      const res = calculateOTForEmp(emp, dates);

      // 1. Cập nhật các thẻ tóm tắt trên cùng
      document.getElementById('ot-total-hours').innerText = res.totalHours + ' giờ';
      document.getElementById('ot-total-s').innerText = res.totalS + ' giờ';
      document.getElementById('ot-total-tr').innerText = res.totalTR + ' giờ';
      document.getElementById('ot-total-t').innerText = res.totalT + ' giờ';

      // 2. Cập nhật ô ngày ở hàng Tổng OT (tr.row-ot-total)
      const trOt = document.querySelector('#ot-compare-table tr.row-ot-total');
      if (trOt) {
        const dObj = res.daily.find(d => d.dateStr === dateStr);
        const dayIndex = dates.findIndex(d => d.date_str === dateStr);
        if (dayIndex >= 0 && dObj) {
          const tdTotalDay = trOt.querySelectorAll('td')[dayIndex + 1];
          if (tdTotalDay) {
            if (dObj.hours > 0) {
              tdTotalDay.classList.add('has-ot');
              tdTotalDay.innerHTML = `<div class="ot-cmp-total-badge">${dObj.hours}h</div>`;
              tdTotalDay.title = `${dObj.thu} ${dObj.day}/${dObj.month}: ${dObj.hours}h OT (S:${dObj.sHours}h, TR:${dObj.trHours}h, T:${dObj.tHours}h)`;
            } else {
              tdTotalDay.classList.remove('has-ot');
              tdTotalDay.innerHTML = '<span class="ot-cmp-dash">-</span>';
              tdTotalDay.title = '';
            }
          }
        }
        // Cập nhật ô Tổng cộng cuối dòng
        const tdTotalEnd = trOt.querySelector('.cmp-total-cell');
        if (tdTotalEnd) {
          tdTotalEnd.innerHTML = `<strong style="font-size:16px;color:var(--primary);font-weight:800;">${res.totalHours} giờ</strong>`;
        }
      }

      // 3. Cập nhật ô Tổng cộng cuối dòng của chính ca này
      const shiftTr = cell.closest('tr');
      if (shiftTr) {
        const shiftTotalCell = shiftTr.querySelector('.cmp-total-cell');
        if (shiftTotalCell) {
          let shiftTotal = (shiftType === 'T') ? res.totalT : (shiftType === 'TR' ? res.totalTR : res.totalS);
          const chipCls = `ot-cmp-chip-${shiftType.toLowerCase()}`;
          shiftTotalCell.innerHTML = `<strong class="${chipCls}" style="font-size:13px;">${shiftTotal}h</strong>`;
        }
      }

      // 4. Cập nhật bảng tổng hợp cả team
      renderOtTeamSummaryTable(emps, dates);
    }

    function resetOtModifications() {
      otModifiedCells = {};
      renderOtTracker();
      if (typeof showToast === 'function') {
        showToast('↺ Đã đặt lại giờ OT về mặc định tính toán từ Lịch trực.');
      }
    }

    function renderShiftTable(tableId, otResult, shiftType) {
      // Legacy compatibility no-op
    }

    function handleOtCellEdit(cell) {
      handleOtCompareCellEdit(cell);
    }

    function renderOtTeamSummaryTable(emps, dates) {
      const tbody = document.getElementById('ot-team-summary-tbody');
      if (!tbody) return;
      tbody.innerHTML = '';

      emps.forEach((e, idx) => {
        const res = calculateOTForEmp(e, dates);
        const tr = document.createElement('tr');
        if (e.id === currentOtEmployeeId) {
          tr.style.background = 'var(--primary-light)';
        }

        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td><span class="badge" style="background:rgba(255,255,255,0.06);font-family:var(--mono-font);">${e.id}</span></td>
          <td><strong>${e.name}</strong> ${e.is_leader ? '<span class="badge" style="background:#fef3c7;color:#b45309;font-size:10px;">👑 Leader</span>' : ''}</td>
          <td class="numeric" style="text-align:right;"><span style="color:#f59e0b;font-weight:700;">${res.totalS}h</span></td>
          <td class="numeric" style="text-align:right;"><span style="color:#38bdf8;font-weight:700;">${res.totalTR}h</span></td>
          <td class="numeric" style="text-align:right;"><span style="color:#c084fc;font-weight:700;">${res.totalT}h</span></td>
          <td class="numeric" style="text-align:right;"><strong style="font-size:14px;color:var(--primary);">${res.totalHours}h</strong></td>
          <td class="text-center" style="text-align:center;">
            <button class="btn btn-sm" onclick="selectOtEmployee('${e.id}', true)" style="padding:4px 10px;font-size:11.5px;background:var(--primary);color:#fff;border:none;">
              📋 Xem & Copy
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    function selectOtEmployee(empId, scrollToTop = false) {
      currentOtEmployeeId = empId;
      hideOtSuggestions();
      renderOtTracker();
      if (scrollToTop) {
        const target = document.getElementById('tab-pane-ot');
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    function openOtForEmployee(empId) {
      switchMainView('ot');
      selectOtEmployee(empId, true);
    }

    function openOtForCurrentModal() {
      closeModal();
      if (currentModalEmpMa) {
        openOtForEmployee(currentModalEmpMa);
      }
    }

    // Sao chép 1 hàng ca trực dạng Tab-Separated Values (TSV) theo khoảng ngày đã chọn
    async function copyOtRow(shiftType, btn) {
      const table = document.getElementById('ot-compare-table');
      if (!table) return;

      let rowSelector = '';
      let rowName = '';
      if (shiftType === 'T') {
        rowSelector = 'tr.row-ot-t';
        rowName = 'Ca Tối (T)';
      } else if (shiftType === 'TR') {
        rowSelector = 'tr.row-ot-tr';
        rowName = 'Ca Trưa (TR)';
      } else if (shiftType === 'S') {
        rowSelector = 'tr.row-ot-s';
        rowName = 'Ca Sáng (S)';
      } else if (shiftType === 'TOTAL') {
        rowSelector = 'tr.row-ot-total';
        rowName = 'Tổng Giờ OT';
      }

      const tr = table.querySelector(rowSelector);
      if (!tr) {
        showToast('Không tìm thấy dòng dữ liệu cần sao chép.');
        return;
      }

      const allTds = Array.from(tr.querySelectorAll('td'));
      if (allTds.length < 3) return;
      const dateTds = allTds.slice(1, -1);

      const dates = getCycleDatesForOT();
      const maxIdx = dateTds.length - 1;
      const fromIdx = Math.max(0, Math.min(otCopyFromIndex, maxIdx));
      const toIdx = Math.max(fromIdx, Math.min(otCopyToIndex < 0 ? maxIdx : otCopyToIndex, maxIdx));
      const selectedTds = dateTds.slice(fromIdx, toIdx + 1);

      const values = selectedTds.map(td => {
        const raw = td.innerText.trim();
        if (raw === '-' || raw === '0' || raw === '0h' || !raw) return '';
        const match = raw.match(/\d+(\.\d+)?/);
        return match ? match[0] : raw;
      });

      const tsvText = values.join('\t');

      try {
        await copyTextToClipboard(tsvText);
        showCopySuccess(btn);
        const pad = n => n < 10 ? '0' + n : String(n);
        const fromStr = dates[fromIdx] ? `${pad(dates[fromIdx].day_num)}/${pad(dates[fromIdx].month)}` : '';
        const toStr = dates[toIdx] ? `${pad(dates[toIdx].day_num)}/${pad(dates[toIdx].month)}` : '';
        showToast(`✅ Đã copy ${values.length} ô ngày (${fromStr} ➔ ${toStr}) của ${rowName}! Nhấn Ctrl+V để dán vào Sheets.`);
      } catch (err) {
        showToast('❌ Không thể sao chép tự động. Vui lòng kiểm tra quyền clipboard.');
      }
    }

    // Sao chép cả 3 ca cùng một lúc theo khoảng ngày đã chọn (3 dòng TSV chuẩn Google Sheets)
    async function copyAllOtShifts(btn) {
      const table = document.getElementById('ot-compare-table');
      if (!table) return;

      const dates = getCycleDatesForOT();
      const rowTypes = ['t', 'tr', 's'];
      const lines = [];
      let copiedCount = 0;

      rowTypes.forEach(st => {
        const tr = table.querySelector(`tr.row-ot-${st}`);
        if (tr) {
          const allTds = Array.from(tr.querySelectorAll('td'));
          const dateTds = allTds.slice(1, -1);
          const maxIdx = dateTds.length - 1;
          const fromIdx = Math.max(0, Math.min(otCopyFromIndex, maxIdx));
          const toIdx = Math.max(fromIdx, Math.min(otCopyToIndex < 0 ? maxIdx : otCopyToIndex, maxIdx));
          const selectedTds = dateTds.slice(fromIdx, toIdx + 1);
          copiedCount = selectedTds.length;

          const rowVals = selectedTds.map(td => {
            const raw = td.innerText.trim();
            if (raw === '-' || raw === '0' || raw === '0h' || !raw) return '';
            const match = raw.match(/\d+(\.\d+)?/);
            return match ? match[0] : raw;
          });
          lines.push(rowVals.join('\t'));
        }
      });

      if (lines.length === 0) {
        showToast('Chưa có dữ liệu để sao chép.');
        return;
      }

      const tsvText = lines.join('\n');
      try {
        await copyTextToClipboard(tsvText);
        showCopySuccess(btn);
        const pad = n => n < 10 ? '0' + n : String(n);
        const fromIdx = Math.max(0, Math.min(otCopyFromIndex, dates.length - 1));
        const toIdx = Math.max(fromIdx, Math.min(otCopyToIndex < 0 ? dates.length - 1 : otCopyToIndex, dates.length - 1));
        const fromStr = dates[fromIdx] ? `${pad(dates[fromIdx].day_num)}/${pad(dates[fromIdx].month)}` : '';
        const toStr = dates[toIdx] ? `${pad(dates[toIdx].day_num)}/${pad(dates[toIdx].month)}` : '';
        showToast(`✅ Đã copy cả 3 ca cho ${copiedCount} ngày (${fromStr} ➔ ${toStr})! Sẵn sàng dán 3 dòng vào Google Sheets.`);
      } catch (err) {
        showToast('❌ Không thể sao chép tự động.');
      }
    }

    async function copyOtTable(tableId, btn) {
      if (typeof tableId === 'string') {
        if (tableId.includes('-t')) return copyOtRow('T', btn);
        if (tableId.includes('-tr')) return copyOtRow('TR', btn);
        if (tableId.includes('-s')) return copyOtRow('S', btn);
      }
      return copyOtRow('TOTAL', btn);
    }

    async function copyTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text);
          return;
        } catch (e) {}
      }

      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);
      const success = document.execCommand('copy');
      textarea.remove();
      if (!success) throw new Error('Copy command failed');
    }

    function showCopySuccess(btn) {
      if (!btn.dataset.originalText) {
        btn.dataset.originalText = btn.innerHTML;
      }
      btn.innerHTML = '✓ Đã copy thành công!';
      btn.classList.add('copied');

      if (btn._copyTimeout) clearTimeout(btn._copyTimeout);
      btn._copyTimeout = setTimeout(() => {
        btn.innerHTML = btn.dataset.originalText;
        btn.classList.remove('copied');
        btn._copyTimeout = null;
      }, 2000);
    }

    // Gợi ý tìm kiếm nhân viên OT
    function hideOtSuggestions() {
      const box = document.getElementById('ot-employee-suggestions');
      const inp = document.getElementById('ot-target-name');
      if (box) box.style.display = 'none';
      if (inp) inp.setAttribute('aria-expanded', 'false');
    }

    function showOtSuggestions() {
      const box = document.getElementById('ot-employee-suggestions');
      const inp = document.getElementById('ot-target-name');
      if (box) box.style.display = 'block';
      if (inp) inp.setAttribute('aria-expanded', 'true');
    }

    function setupOtSearch() {
      const inp = document.getElementById('ot-target-name');
      const box = document.getElementById('ot-employee-suggestions');
      if (!inp || !box) return;

      const triggerSearch = (forceShowAll = false) => {
        const rawVal = inp.value.trim();
        const query = normalizeText(rawVal);
        const emps = (DATA.schedule && DATA.schedule.employees) || [];

        // Kiểm tra nếu query trùng với tên nhân viên đang chọn -> Hiện tất cả 13 người
        const currEmp = emps.find(e => e.id === currentOtEmployeeId);
        const isCurrentVal = currEmp && (
          query === normalizeText(`${currEmp.id} - ${currEmp.name}`) ||
          query === normalizeText(currEmp.name) ||
          query === normalizeText(currEmp.id)
        );

        let matches = emps;
        if (query && !forceShowAll && !isCurrentVal) {
          matches = emps.filter(e => {
            return normalizeText(e.id).includes(query) || normalizeText(e.name).includes(query);
          });
        }

        box.innerHTML = '';
        if (matches.length === 0) {
          box.innerHTML = '<div style="padding:10px 14px;color:var(--text-muted);font-size:13px;">Không tìm thấy nhân viên phù hợp</div>';
          showOtSuggestions();
          return;
        }

        matches.forEach(e => {
          const item = document.createElement('button');
          item.type = 'button';
          item.className = 'ot-suggestion-item';
          if (e.id === currentOtEmployeeId) {
            item.style.background = 'rgba(99, 102, 241, 0.12)';
            item.style.fontWeight = '700';
          }
          item.innerHTML = `
            <span><strong style="color:var(--text-main);">${e.is_leader ? '👑 ' : ''}${e.name}</strong></span>
            <span class="ot-suggestion-code">${e.id}</span>
          `;
          item.addEventListener('click', () => {
            selectOtEmployee(e.id);
          });
          box.appendChild(item);
        });
        showOtSuggestions();
      };

      inp.addEventListener('input', () => {
        if (otSearchDebounceTimer) clearTimeout(otSearchDebounceTimer);
        otSearchDebounceTimer = setTimeout(() => triggerSearch(false), 120);
      });

      inp.addEventListener('focus', () => {
        inp.select();
        triggerSearch(true);
      });

      inp.addEventListener('click', () => {
        triggerSearch(true);
      });

      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideOtSuggestions();
        if (e.key === 'Enter') {
          e.preventDefault();
          const first = box.querySelector('.ot-suggestion-item');
          if (first) first.click();
        }
      });

      document.addEventListener('click', (e) => {
        if (!e.target.closest('.ot-search-wrapper')) {
          hideOtSuggestions();
        }
      });
    }
