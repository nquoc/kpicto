/* ============================================================
   KPI & PERFORMANCE TRACKING MODULE
   ============================================================ */
    let currentDay = DATA.current_day || 14;
    let totalDays = DATA.days_in_month || 30;
    let targetPacing = currentDay / totalDays;

    let currentTab = 'kpi';
    let sortColumn = 'pct_kpi_tong';
    let sortAsc = false;
    let filteredKpi = [];

    function calculatePacingDetails(item) {
      const diff = item.pct_kpi_tong - targetPacing;
      const diffPct = (diff * 100).toFixed(2);
      const pctDatTienDo = targetPacing > 0 ? ((item.pct_kpi_tong / targetPacing) * 100).toFixed(1) : '0.0';
      let status = '';
      let badgeClass = '';
      let text = '';
      let isCritical = false;

      if (diff >= 0.03) {
        status = 'AHEAD';
        badgeClass = 'badge-ahead';
        text = `Vượt (+${diffPct}%) • Đạt ${pctDatTienDo}% tiến độ`;
      } else if (diff >= -0.02) {
        status = 'ON_TRACK';
        badgeClass = 'badge-ontrack';
        text = `Đạt chuẩn (${diff >= 0 ? '+' : ''}${diffPct}%) • Đạt ${pctDatTienDo}% tiến độ`;
      } else if (diff >= -0.06) {
        status = 'BEHIND';
        badgeClass = 'badge-behind-slight';
        text = `Chậm (${diffPct}%) • Đạt ${pctDatTienDo}% tiến độ`;
      } else {
        status = 'CRITICAL';
        badgeClass = 'badge-behind-severe';
        text = `Báo động (${diffPct}%) • Đạt ${pctDatTienDo}% tiến độ`;
        isCritical = true;
      }

      return {
        diff,
        diffPct,
        pctDatTienDo,
        status,
        badgeClass,
        icon: '',
        text,
        isCritical
      };
    }

    function onDayChange() {
      const val = parseInt(document.getElementById('input-current-day').value, 10);
      if (!isNaN(val) && val >= 1 && val <= totalDays) {
        currentDay = val;
      } else {
        currentDay = Math.min(14, totalDays);
        document.getElementById('input-current-day').value = currentDay;
      }
      targetPacing = currentDay / totalDays;
      updatePacingDisplay();
      applyFilters();
    }

    function onTotalDaysChange() {
      const val = parseInt(document.getElementById('input-total-days').value, 10);
      if (!isNaN(val) && val >= 28 && val <= 31) {
        totalDays = val;
      } else {
        totalDays = 30;
        document.getElementById('input-total-days').value = 30;
      }
      targetPacing = currentDay / totalDays;
      document.getElementById('pacing-note-text').innerText = `💡 Đang tính theo tháng ${totalDays} ngày (Chuẩn hôm nay ngày ${currentDay}: ${(targetPacing * 100).toFixed(2)}%).`;
      updatePacingDisplay();
      applyFilters();
    }

    function setTotalDays(days) {
      totalDays = days;
      if (document.getElementById('input-total-days')) {
        document.getElementById('input-total-days').value = days;
      }
      targetPacing = currentDay / totalDays;
      document.getElementById('pacing-note-text').innerText = `💡 Đang tính theo tháng ${days} ngày (Chuẩn hôm nay ngày ${currentDay}: ${(targetPacing * 100).toFixed(2)}%).`;
      updatePacingDisplay();
      applyFilters();
    }

    function updatePacingDisplay() {
      const targetPctStr = (targetPacing * 100).toFixed(2) + '%';
      document.getElementById('lbl-target-pacing').innerText = targetPctStr;
      document.getElementById('chart-target-line').innerText = `Chuẩn ngày ${currentDay}: ${targetPctStr}`;

      // Recalculate summary stats based on pacing
      let aheadCount = 0;
      let behindCount = 0;
      DATA.kpi_tong.forEach(item => {
        const pacing = calculatePacingDetails(item);
        item.pacing_diff = pacing.diff;
        item.pacing_info = pacing;
        if (pacing.status === 'AHEAD' || pacing.status === 'ON_TRACK') {
          aheadCount++;
        } else {
          behindCount++;
        }
      });

      document.getElementById('card-total-staff').innerText = DATA.summary.total_staff;
      document.getElementById('card-avg-kpi').innerText = DATA.summary.avg_kpi + '%';
      const avgDiff = (DATA.summary.avg_kpi - targetPacing * 100).toFixed(1);
      document.getElementById('card-avg-status').innerText = `So với chuẩn: ${avgDiff >= 0 ? '+' : ''}${avgDiff}%`;
      document.getElementById('card-count-ahead').innerText = `${aheadCount} / ${DATA.summary.total_staff}`;
      document.getElementById('card-count-behind').innerText = `${behindCount} / ${DATA.summary.total_staff}`;
      const card2Ht = document.getElementById('card-total-ticket-2ht');
      if (card2Ht) card2Ht.innerText = DATA.summary.total_ticket_2ht ?? 0;

      if (typeof renderPodiumAndAwards === 'function') {
        renderPodiumAndAwards();
      }
      if (typeof buildMyNameOptions === 'function') {
        buildMyNameOptions();
      }
    }

    function switchTab(tab) {
      if (tab === 'schedule') {
        switchMainView('schedule');
        return;
      }
      if (currentMainView === 'schedule') {
        switchMainView('kpi');
      }
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById('tab-btn-' + tab);
      if (activeBtn) activeBtn.classList.add('active');

      const paneKpi = document.getElementById('tab-pane-kpi');
      const paneCharts = document.getElementById('tab-pane-charts');
      const panePodium = document.getElementById('tab-pane-podium');

      if (paneKpi) paneKpi.style.display = tab === 'kpi' ? 'block' : 'none';
      if (paneCharts) paneCharts.style.display = tab === 'charts' ? 'block' : 'none';
      if (panePodium) panePodium.style.display = tab === 'podium' ? 'block' : 'none';
    }

    function renderKpiTable() {
      const tbody = document.getElementById('tbody-kpi');
      tbody.innerHTML = '';
      document.getElementById('badge-count-kpi').innerText = filteredKpi.length;

      filteredKpi.forEach((item, idx) => {
        const tr = document.createElement('tr');
        tr.onclick = () => openModal(item);

        const myName = localStorage.getItem('kpicto_my_name') || '';
        if (myName && (item.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(item.name.toLowerCase()))) {
          tr.classList.add('my-row-highlight');
        }

        const pctTicket = item.pct_kpi_ticket;
        const pctCv = item.pct_kpi_cv;
        const pctTong = item.pct_kpi_tong;
        const p = item.pacing_info || calculatePacingDetails(item);

        if (p.isCritical) {
          tr.classList.add('alert-severe');
        }

        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td><strong>${item.ma}</strong></td>
          <td>
            <div style="font-weight:600;">${item.name}</div>
            <div style="font-size:11px;color:var(--text-muted);">${item.team}</div>
          </td>
          <td class="text-center"><span class="badge badge-level">Level ${item.level}</span></td>
          <td class="numeric">${item.kpi_ticket.toLocaleString('vi-VN')}</td>
          <td class="numeric">${item.slg_kh.toLocaleString('vi-VN')}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${pctTicket >= targetPacing ? 'bg-excel' : 'bg-ok'}" style="width:${Math.min(pctTicket * 100, 100)}%;"></div>
              </div>
              <span class="progress-pct-val">${(pctTicket * 100).toFixed(1)}%</span>
            </div>
          </td>
          <td class="numeric">${item.kpi_cv.toLocaleString('vi-VN')}</td>
          <td class="numeric">${item.slg_cv.toLocaleString('vi-VN')}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${pctCv >= targetPacing ? 'bg-excel' : 'bg-ok'}" style="width:${Math.min(pctCv * 100, 100)}%;"></div>
              </div>
              <span class="progress-pct-val">${(pctCv * 100).toFixed(1)}%</span>
            </div>
          </td>
          <td class="text-center">${item.no_ticket_2ht > 0 ? `<span class="badge badge-ticket-2ht">${item.no_ticket_2ht}</span>` : '0'}</td>
          <td>
            <div class="progress-bar-wrapper">
              <div class="progress-track">
                <div class="progress-fill ${pctTong >= targetPacing ? 'bg-excel' : 'bg-low'}" style="width:${Math.min(pctTong * 100, 100)}%;"></div>
              </div>
              <span class="progress-pct-val" style="color:${pctTong >= targetPacing ? '#10b981' : '#f59e0b'};">${(pctTong * 100).toFixed(2)}%</span>
            </div>
          </td>
          <td>
            <span class="badge ${p.badgeClass}">
              ${p.text}
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      });

// Render Mobile Cards View
      renderKpiMobileCards();
    }

    let currentKpiMobileView = 'cards';
    function setKpiMobileView(view) {
      currentKpiMobileView = view;
      const cardsEl = document.getElementById('kpi-mobile-cards');
      const tableEl = document.getElementById('kpi-table-view-wrap');
      const btnCards = document.getElementById('btn-view-cards');
      const btnTable = document.getElementById('btn-view-table');

      if (view === 'cards') {
        if (cardsEl) cardsEl.style.display = 'grid';
        if (tableEl) tableEl.style.display = 'none';
        if (btnCards) btnCards.classList.add('active');
        if (btnTable) btnTable.classList.remove('active');
      } else {
        if (cardsEl) cardsEl.style.display = 'none';
        if (tableEl) tableEl.style.display = 'block';
        if (btnCards) btnCards.classList.remove('active');
        if (btnTable) btnTable.classList.add('active');
      }
    }

    function openModalByMa(ma) {
      let item = (DATA.kpi_tong || []).find(x => String(x.ma) === String(ma));
      if (!item && (String(ma) === '8805' || String(ma) === '8607')) {
        item = (DATA.kpi_tong || []).find(x => String(x.ma) === '8607' || String(x.ma) === '8805');
      }
      if (item) {
        openModal(item);
      }
    }

    function renderKpiMobileCards() {
      const container = document.getElementById('kpi-mobile-cards');
      if (!container) return;

      const sortedByKpi = [...(DATA.kpi_tong || [])].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);

      container.innerHTML = filteredKpi.map((item) => {
        const p = item.pacing_info || calculatePacingDetails(item);
        const rankIdx = sortedByKpi.findIndex(x => x.ma === item.ma);
        const rank = rankIdx >= 0 ? rankIdx + 1 : 1;
        const rankMedal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
        const isLeader = item.name.toLowerCase().includes('minh nhựt') || item.name.toLowerCase().includes('nhựt');

        const nameParts = item.name.trim().split(' ');
        const initials = nameParts.length >= 2 
          ? (nameParts[nameParts.length - 2][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
          : item.name.substring(0, 2).toUpperCase();

        const diffPct = (p.diff * 100).toFixed(1);
        const diffText = p.diff >= 0 ? `+${diffPct}%` : `${diffPct}%`;
        const tagClass = p.isAhead ? 'tag-success' : p.isCritical ? 'tag-danger' : 'tag-warning';
        const tagLabel = p.isAhead ? `🟢 Vượt (${diffText})` : p.isCritical ? `🔴 Chậm (${diffText})` : `🟡 Cận (${diffText})`;

        return `
          <div class="mobile-kpi-card" onclick="openModalByMa('${item.ma}')">
            <div class="mkc-header">
              <div class="mkc-left">
                <span class="mkc-rank">${rankMedal}</span>
                <div class="mkc-avatar">${initials}</div>
                <div class="mkc-name-wrap">
                  <div class="mkc-name">${item.name} ${isLeader ? '👑' : ''}</div>
                  <div class="mkc-sub">MS: ${item.ma} • Level ${item.level}</div>
                </div>
              </div>
              <div class="mkc-right">
                <div class="mkc-kpi-pct ${(item.pct_kpi_tong >= targetPacing) ? 'text-success' : 'text-danger'}">
                  ${(item.pct_kpi_tong * 100).toFixed(1)}%
                </div>
                <div class="mkc-tag ${tagClass}">${tagLabel}</div>
              </div>
            </div>

            <div class="mkc-progress-track">
              <div class="progress-fill ${(item.pct_kpi_tong >= targetPacing) ? 'bg-excel' : 'bg-low'}" style="width:${Math.min(item.pct_kpi_tong * 100, 100)}%;"></div>
              <div class="mkc-marker-target" style="left:${Math.min(targetPacing * 100, 100)}%;" title="Chuẩn ngày: ${(targetPacing * 100).toFixed(1)}%"></div>
            </div>

            <div class="mkc-stats-grid">
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">🎫 Tickets</div>
                <div class="mkc-stat-val">${item.slg_kh.toLocaleString('vi-VN')} <small>/ ${item.kpi_ticket.toLocaleString('vi-VN')}</small></div>
                <div class="mkc-stat-pct">${(item.pct_kpi_ticket * 100).toFixed(0)}% KPI</div>
              </div>
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">💼 Công Việc</div>
                <div class="mkc-stat-val">${item.slg_cv.toLocaleString('vi-VN')} <small>/ ${item.kpi_cv.toLocaleString('vi-VN')}</small></div>
                <div class="mkc-stat-pct">${(item.pct_kpi_cv * 100).toFixed(0)}% KPI</div>
              </div>
              <div class="mkc-stat-item">
                <div class="mkc-stat-lbl">🤝 2 CV Hỗ Trợ</div>
                <div class="mkc-stat-val">${item.no_ticket_2ht}</div>
                <div class="mkc-stat-pct" style="color:var(--text-muted);">${item.no_ticket_2ht > 0 ? 'Có hỗ trợ' : '0'}</div>
              </div>
            </div>

            <div class="mkc-footer">
              <span>Chạm để xem chi tiết thẻ năng lực</span>
              <span style="font-size:13px;color:var(--primary);">➔</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderHsTable() {
      // Đã loại bỏ bảng hiệu suất ca trực theo yêu cầu
    }

    function renderCharts() {
      const containerKpi = document.getElementById('chart-kpi-bars');
      if (containerKpi) {
        containerKpi.innerHTML = '';
        const sortedByKpi = [...DATA.kpi_tong].sort((a, b) => b.pct_kpi_tong - a.pct_kpi_tong);

        sortedByKpi.forEach(item => {
          const row = document.createElement('div');
          row.className = 'bar-row';
          const pct = (item.pct_kpi_tong * 100).toFixed(1);
          const p = item.pacing_info || calculatePacingDetails(item);
          const barColor = p.status === 'AHEAD' ? 'linear-gradient(90deg, #10b981, #34d399)' :
                           p.status === 'ON_TRACK' ? 'linear-gradient(90deg, #0ea5e9, #38bdf8)' :
                           p.status === 'BEHIND' ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' :
                           'linear-gradient(90deg, #ef4444, #f87171)';

          row.innerHTML = `
            <div class="bar-label" title="${item.name}">${item.name}</div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${Math.max(Math.min(pct * 1.3, 100), 12)}%;background:${barColor};">
                <span>${pct}% (Đạt ${p.pctDatTienDo}% tiến độ)</span>
              </div>
            </div>
          `;
          containerKpi.appendChild(row);
        });
      }

      // Xếp hạng Công việc (CV) quy đổi
      const containerShift = document.getElementById('chart-shift-hours');
      if (containerShift) {
        containerShift.innerHTML = '';
        const sortedByCv = [...DATA.kpi_tong].sort((a, b) => b.slg_cv - a.slg_cv);
        const maxCv = Math.max(...sortedByCv.map(x => x.slg_cv), 1);
        sortedByCv.forEach(item => {
          const row = document.createElement('div');
          row.className = 'bar-row';
          const pctWidth = ((item.slg_cv / maxCv) * 100).toFixed(1);
          row.innerHTML = `
            <div class="bar-label" title="${item.name}">${item.name}</div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${Math.max(pctWidth, 12)}%;background:linear-gradient(90deg, #6366f1, #818cf8);">
                <span>${item.slg_cv.toLocaleString('vi-VN')} CV (${(item.pct_kpi_cv * 100).toFixed(0)}%)</span>
              </div>
            </div>
          `;
          containerShift.appendChild(row);
        });
      }
    }

    function applyFilters() {
      const searchEl = document.getElementById('filter-search');
      const levelEl = document.getElementById('filter-level');
      const pacingEl = document.getElementById('filter-pacing');

      const search = searchEl ? searchEl.value.toLowerCase().trim() : '';
      const level = levelEl ? levelEl.value : 'ALL';
      const pacingFilter = pacingEl ? pacingEl.value : 'ALL';

      filteredKpi = DATA.kpi_tong.filter(item => {
        const matchesSearch = !search || item.name.toLowerCase().includes(search) || item.ma.includes(search);
        const matchesLevel = level === 'ALL' || item.level === level;

        const p = item.pacing_info || calculatePacingDetails(item);
        let matchesPacing = true;
        if (pacingFilter === 'AHEAD') matchesPacing = (p.status === 'AHEAD');
        else if (pacingFilter === 'ON_TRACK') matchesPacing = (p.status === 'ON_TRACK');
        else if (pacingFilter === 'BEHIND') matchesPacing = (p.status === 'BEHIND' || p.status === 'CRITICAL');
        else if (pacingFilter === 'CRITICAL') matchesPacing = (p.status === 'CRITICAL');

        return matchesSearch && matchesLevel && matchesPacing;
      });

      renderKpiTable();
      renderCharts();
    }

    function resetFilters() {
      if (document.getElementById('filter-search')) document.getElementById('filter-search').value = '';
      if (document.getElementById('filter-level')) document.getElementById('filter-level').value = 'ALL';
      if (document.getElementById('filter-pacing')) document.getElementById('filter-pacing').value = 'ALL';
      applyFilters();
    }

    function sortTable(type, col) {
      if (sortColumn === col) {
        sortAsc = !sortAsc;
      } else {
        sortColumn = col;
        sortAsc = false;
      }

      filteredKpi.sort((a, b) => {
        let vA = a[col];
        let vB = b[col];
        if (typeof vA === 'string') vA = vA.toLowerCase();
        if (typeof vB === 'string') vB = vB.toLowerCase();
        if (vA < vB) return sortAsc ? -1 : 1;
        if (vA > vB) return sortAsc ? 1 : -1;
        return 0;
      });

      renderKpiTable();
    }

    function buildMyNameOptions() {
      const select = document.getElementById('select-my-name');
      if (!select) return;
      
      const currentVal = select.value;
      select.innerHTML = '<option value="">👤 Tôi là ai? (Chọn tên bạn...)</option>';
      
      const allNamesSet = new Set([...DATA.kpi_tong].map(x => x.name));
      if (DATA.schedule && DATA.schedule.employees) {
        DATA.schedule.employees.forEach(e => allNamesSet.add(e.name));
      }
      const names = Array.from(allNamesSet).sort((a,b) => a.localeCompare(b, 'vi'));
      names.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      });

      const savedName = localStorage.getItem('kpicto_my_name') || '';
      if (savedName && names.includes(savedName)) {
        select.value = savedName;
        onSelectMyName(savedName, false);
      } else if (currentVal && names.includes(currentVal)) {
        select.value = currentVal;
      }
    }

    function onSelectMyName(name, shouldScroll = true) {
      if (name) {
        localStorage.setItem('kpicto_my_name', name);
        const btnCard = document.getElementById('btn-open-my-card');
        if (btnCard) btnCard.style.display = 'inline-flex';
      } else {
        localStorage.removeItem('kpicto_my_name');
        const btnCard = document.getElementById('btn-open-my-card');
        if (btnCard) btnCard.style.display = 'none';
      }

      // Re-apply highlight to tables
      document.querySelectorAll('tr.my-row-highlight').forEach(tr => tr.classList.remove('my-row-highlight'));

      if (name) {
        const nameLower = name.toLowerCase();
        let targetRow = null;
        
        document.querySelectorAll('#tbody-kpi tr').forEach(tr => {
          if (tr.innerText.toLowerCase().includes(nameLower)) {
            tr.classList.add('my-row-highlight');
            if (!targetRow && currentTab === 'kpi') targetRow = tr;
          }
        });

        document.querySelectorAll('#tbody-schedule-summary tr').forEach(tr => {
          if (tr.innerText.toLowerCase().includes(nameLower)) {
            tr.classList.add('my-row-highlight');
            if (!targetRow && currentTab === 'schedule') targetRow = tr;
          }
        });

        document.querySelectorAll('#tbody-matrix-schedule tr').forEach(tr => {
          if (tr.innerText.toLowerCase().includes(nameLower)) {
            tr.classList.add('my-row-highlight');
          }
        });

        if (shouldScroll && targetRow) {
          targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }

    function openMySelectedCard() {
      const myName = localStorage.getItem('kpicto_my_name');
      if (!myName) return;
      const item = DATA.kpi_tong.find(x => x.name.toLowerCase().includes(myName.toLowerCase()) || myName.toLowerCase().includes(x.name.toLowerCase()));
      if (item) {
        openModal(item);
      } else {
        showToast('Chưa tìm thấy dữ liệu cá nhân cho: ' + myName);
      }
    }

    function openModal(item) {
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
      if (rankEl) {
        const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '🏆';
        rankEl.innerText = `${medal} Hạng #${rank} / ${DATA.kpi_tong.length}`;
      }

      document.getElementById('modal-name').innerText = `${item.ma} - ${item.name}`;
      currentModalEmpMa = item.ma;
      const lvlEl = document.getElementById('modal-level');
      if (lvlEl) lvlEl.innerText = 'Level ' + item.level;

      document.getElementById('modal-pacing-status').innerHTML = `<span class="badge ${p.badgeClass}">${p.text}</span>`;

      // Khối 1: Forecast Target Calculator
      const currentPct = item.pct_kpi_tong;
      const forecastPct = targetPacing > 0 ? ((currentPct / targetPacing) * 100).toFixed(1) : (currentPct * 100).toFixed(1);
      const remainingDays = Math.max(1, totalDays - currentDay);
      const remTicket = Math.max(0, item.kpi_ticket - item.slg_kh);
      const dailyTicket = (remTicket / remainingDays).toFixed(1);
      const remCv = Math.max(0, item.kpi_cv - item.slg_cv);
      const dailyCv = (remCv / remainingDays).toFixed(1);

      const fValEl = document.getElementById('modal-forecast-val');
      if (fValEl) {
        const isAhead = parseFloat(forecastPct) >= 100;
        fValEl.innerText = `${forecastPct}% KPI`;
        fValEl.style.color = isAhead ? 'var(--success)' : (parseFloat(forecastPct) >= 85 ? 'var(--warning)' : 'var(--danger)');
      }

      const pTagEl = document.getElementById('modal-pacing-tag');
      if (pTagEl) pTagEl.innerText = `(Tốc độ ngày ${currentDay}/${totalDays} • Chuẩn: ${(targetPacing*100).toFixed(1)}%)`;

      const planEl = document.getElementById('modal-forecast-plan');
      if (planEl) {
        if (currentPct >= 1.0) {
          planEl.innerHTML = `🎉 <strong>Chúc mừng xuất sắc!</strong> Bạn đã hoàn thành vượt mốc 100% KPI tháng sớm! Hãy giữ vững phong độ đỉnh cao này nhé.`;
        } else {
          planEl.innerHTML = `🎯 <strong>Kế hoạch cán đích 100% KPI</strong> trong <strong>${remainingDays} ngày còn lại</strong>:<br>` +
            `• <strong>Ticket KH:</strong> Còn thiếu <strong>${remTicket.toLocaleString('vi-VN')}</strong> KH (trung bình cần <strong>+${dailyTicket} KH/ngày</strong>).<br>` +
            `• <strong>Công việc (CV):</strong> Còn thiếu <strong>${remCv.toLocaleString('vi-VN')}</strong> CV (trung bình cần <strong>+${dailyCv} CV/ngày</strong>).`;
        }
      }

      // Khối 2: Strengths & Balance
      const tValEl = document.getElementById('modal-ticket-val');
      if (tValEl) tValEl.innerText = `${item.slg_kh.toLocaleString('vi-VN')} / ${item.kpi_ticket.toLocaleString('vi-VN')}`;
      const tBadgeEl = document.getElementById('modal-ticket-badge');
      if (tBadgeEl) tBadgeEl.innerText = `${(item.pct_kpi_ticket*100).toFixed(1)}% KPI`;

      const cvValEl = document.getElementById('modal-cv-val');
      if (cvValEl) cvValEl.innerText = `${item.slg_cv.toLocaleString('vi-VN')} / ${item.kpi_cv.toLocaleString('vi-VN')}`;
      const cvBadgeEl = document.getElementById('modal-cv-badge');
      if (cvBadgeEl) cvBadgeEl.innerText = `${(item.pct_kpi_cv*100).toFixed(1)}% KPI`;

      const diffTicketCv = (item.pct_kpi_ticket - item.pct_kpi_cv) * 100;
      const strAssessEl = document.getElementById('modal-strength-assessment');
      const strDescEl = document.getElementById('modal-strength-desc');
      if (strAssessEl && strDescEl) {
        if (diffTicketCv >= 5) {
          strAssessEl.innerText = `⚡ Điểm mạnh: Gánh Ticket vượt trội`;
          strDescEl.innerText = `Tỷ lệ hoàn thành Ticket (${(item.pct_kpi_ticket*100).toFixed(1)}%) cao hơn CV ${diffTicketCv.toFixed(1)}%. Tốc độ hỗ trợ khách hàng rất nhanh nhạy.`;
        } else if (diffTicketCv <= -5) {
          strAssessEl.innerText = `🛠️ Điểm mạnh: Đẩy mạnh Công việc hỗ trợ`;
          strDescEl.innerText = `Tỷ lệ hoàn thành CV (${(item.pct_kpi_cv*100).toFixed(1)}%) cao hơn Ticket ${Math.abs(diffTicketCv).toFixed(1)}%. Đóng góp tích cực vào các công việc kỹ thuật chuyên sâu.`;
        } else {
          strAssessEl.innerText = `⚖️ Phong độ: Toàn diện & Cân bằng`;
          strDescEl.innerText = `Tỷ lệ Ticket và CV phân bổ đồng đều (${(item.pct_kpi_ticket*100).toFixed(1)}% vs ${(item.pct_kpi_cv*100).toFixed(1)}%), hỗ trợ toàn diện các mặt công việc.`;
        }
      }

      const badge2Ht = document.getElementById('modal-ticket-2ht-badge');
      if (badge2Ht) {
        badge2Ht.innerText = `📋 ${item.no_ticket_2ht} Ticket 2 CV`;
        badge2Ht.style.background = 'var(--primary-light)';
        badge2Ht.style.color = 'var(--primary)';
        badge2Ht.title = 'Số lượng ticket có 2 công việc hỗ trợ';
      }

      // Khối 3: Shift Breakdown (nếu có phần tử trong DOM)
      const sBody = document.getElementById('modal-shifts-body');
      if (sBody) sBody.innerHTML = '';
      const stackedBarEl = document.getElementById('modal-shift-stacked');
      if (stackedBarEl) stackedBarEl.innerHTML = '';
      const legendEl = document.getElementById('modal-shift-legend');
      if (legendEl) legendEl.innerHTML = '';
      const highlightEl = document.getElementById('modal-shift-highlight');
      if (highlightEl) highlightEl.innerText = '';

      document.getElementById('emp-modal').style.display = 'flex';
    }

    function closeModal() {
      document.getElementById('emp-modal').style.display = 'none';
    }

    function renderPodiumAndAwards() {
      const podiumEl = document.getElementById('podium-content');
      const awardsEl = document.getElementById('awards-content');
      if (!podiumEl || !awardsEl || !DATA.kpi_tong.length) return;

      const sortedByKpi = [...DATA.kpi_tong].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);
      const top1 = sortedByKpi[0] || null;
      const top2 = sortedByKpi[1] || null;
      const top3 = sortedByKpi[2] || null;

      const getInitials = (name) => {
        const parts = name.trim().split(' ');
        return parts.length >= 2 ? (parts[parts.length - 2][0] + parts[parts.length - 1][0]).toUpperCase() : name.substring(0, 2).toUpperCase();
      };

      let podiumHtml = '';

      if (top2) {
        podiumHtml += `
          <div class="podium-step podium-2" onclick="openModalByName('${top2.name}')">
            <div class="podium-avatar">${getInitials(top2.name)}</div>
            <div class="podium-name" title="${top2.name}">${top2.name}</div>
            <div class="podium-pct">${(top2.pct_kpi_tong * 100).toFixed(1)}%</div>
            <div class="podium-block">2 🥈</div>
          </div>
        `;
      }

      if (top1) {
        podiumHtml += `
          <div class="podium-step podium-1" onclick="openModalByName('${top1.name}')">
            <div class="podium-avatar">
              <span class="podium-crown">👑</span>
              ${getInitials(top1.name)}
            </div>
            <div class="podium-name" title="${top1.name}">${top1.name}</div>
            <div class="podium-pct">${(top1.pct_kpi_tong * 100).toFixed(1)}%</div>
            <div class="podium-block">1 🥇</div>
          </div>
        `;
      }

      if (top3) {
        podiumHtml += `
          <div class="podium-step podium-3" onclick="openModalByName('${top3.name}')">
            <div class="podium-avatar">${getInitials(top3.name)}</div>
            <div class="podium-name" title="${top3.name}">${top3.name}</div>
            <div class="podium-pct">${(top3.pct_kpi_tong * 100).toFixed(1)}%</div>
            <div class="podium-block">3 🥉</div>
          </div>
        `;
      }

      podiumEl.innerHTML = podiumHtml;

      // Special Awards (Được tính toán hoàn toàn từ DATA.kpi_tong)
      const sortedSpeed = [...DATA.kpi_tong].sort((a,b) => {
        const pA = a.pacing_info || calculatePacingDetails(a);
        const pB = b.pacing_info || calculatePacingDetails(b);
        return pB.diff - pA.diff;
      });
      const heroSpeed = sortedSpeed[0];

      const sortedTicket = [...DATA.kpi_tong].sort((a,b) => b.slg_kh - a.slg_kh);
      const heroTicket = sortedTicket[0];

      const sortedCv = [...DATA.kpi_tong].sort((a,b) => b.slg_cv - a.slg_cv);
      const heroCv = sortedCv[0];

      const sorted2Ht = [...DATA.kpi_tong].sort((a,b) => (b.no_ticket_2ht || 0) - (a.no_ticket_2ht || 0));
      const hero2Ht = sorted2Ht[0];

      awardsEl.innerHTML = `
        <div class="award-card" onclick="openModalByName('${heroSpeed ? heroSpeed.name : ''}')">
          <div class="award-icon">⚡</div>
          <div>
            <div class="award-title">Chiến Thần Tốc Độ</div>
            <div class="award-name">${heroSpeed ? heroSpeed.name : '--'}</div>
            <div class="award-stat">${heroSpeed ? (heroSpeed.pacing_info ? heroSpeed.pacing_info.text.split('•')[0] : 'Vượt chuẩn tiến độ') : '--'}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${heroTicket ? heroTicket.name : ''}')">
          <div class="award-icon">🎯</div>
          <div>
            <div class="award-title">Vua Xử Lý Ticket</div>
            <div class="award-name">${heroTicket ? heroTicket.name : '--'}</div>
            <div class="award-stat">${heroTicket ? heroTicket.slg_kh.toLocaleString('vi-VN') + ' KH quy đổi' : '--'}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${heroCv ? heroCv.name : ''}')">
          <div class="award-icon">🛠️</div>
          <div>
            <div class="award-title">Bàn Tay Vàng CV</div>
            <div class="award-name">${heroCv ? heroCv.name : '--'}</div>
            <div class="award-stat">${heroCv ? heroCv.slg_cv.toLocaleString('vi-VN') + ' CV quy đổi' : '--'}</div>
          </div>
        </div>

        <div class="award-card" onclick="openModalByName('${hero2Ht ? hero2Ht.name : ''}')">
          <div class="award-icon">🌟</div>
          <div>
            <div class="award-title">Chúa Tể Buff Bẩn</div>
            <div class="award-name">${hero2Ht ? hero2Ht.name : '--'}</div>
            <div class="award-stat">${hero2Ht ? (hero2Ht.no_ticket_2ht || 0) + ' Ticket có 2 CV HT' : '--'}</div>
          </div>
        </div>
      `;
    }

    function openModalByName(name) {
      if (!name) return;
      const item = DATA.kpi_tong.find(x => x.name.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(x.name.toLowerCase()));
      if (item) openModal(item);
    }

    function captureReportImage() {
      const btn = document.getElementById('btn-snap-zalo');
      if (btn) btn.innerHTML = '⏳ Đang tạo ảnh...';

      // Populate Zalo snapshot card
      document.getElementById('zalo-snap-time').innerText = 'Cập nhật PBI: ' + DATA.updated_at;
      document.getElementById('zalo-snap-pacing').innerText = `Tiến độ: Ngày ${currentDay}/${totalDays} (Chuẩn: ${(targetPacing*100).toFixed(1)}%)`;
      document.getElementById('zalo-snap-staff').innerText = DATA.summary.total_staff;
      document.getElementById('zalo-snap-avg').innerText = DATA.summary.avg_kpi + '%';
      
      const aheadCount = DATA.kpi_tong.filter(x => {
        const p = x.pacing_info || calculatePacingDetails(x);
        return p.status === 'AHEAD' || p.status === 'ON_TRACK';
      }).length;
      document.getElementById('zalo-snap-ahead').innerText = `${aheadCount} / ${DATA.summary.total_staff}`;
      document.getElementById('zalo-snap-top').innerText = DATA.summary.top_performer + ` (${DATA.summary.top_kpi}%)`;

      const tbody = document.getElementById('zalo-snap-tbody');
      tbody.innerHTML = '';
      const sorted = [...DATA.kpi_tong].sort((a,b) => b.pct_kpi_tong - a.pct_kpi_tong);

      sorted.forEach((item, idx) => {
        const p = item.pacing_info || calculatePacingDetails(item);
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #334155';
        const rankMedal = idx === 0 ? '🥇 1' : idx === 1 ? '🥈 2' : idx === 2 ? '🥉 3' : (idx + 1);
        tr.innerHTML = `
          <td style="padding:6px 10px;font-weight:700;">${rankMedal}</td>
          <td style="padding:6px 10px;color:#94a3b8;">${item.ma}</td>
          <td style="padding:6px 10px;font-weight:700;">${item.name}</td>
          <td style="padding:6px 10px;text-align:right;">${item.slg_kh.toLocaleString('vi-VN')}</td>
          <td style="padding:6px 10px;text-align:right;">${item.slg_cv.toLocaleString('vi-VN')}</td>
          <td style="padding:6px 10px;text-align:center;">${item.no_ticket_2ht > 0 ? item.no_ticket_2ht : '0'}</td>
          <td style="padding:6px 10px;text-align:right;font-weight:800;color:#38bdf8;">${(item.pct_kpi_tong*100).toFixed(2)}%</td>
          <td style="padding:6px 10px;text-align:center;">
            <span class="badge ${p.badgeClass}" style="font-size:10px;padding:2px 6px;">${p.text.split('•')[0]}</span>
          </td>
        `;
        tbody.appendChild(tr);
      });

      const card = document.getElementById('zalo-snapshot-card');
      card.style.left = '0px';
      card.style.top = '0px';
      card.style.zIndex = '-9999';

      if (typeof html2canvas === 'undefined') {
        alert('Đang nạp thư viện html2canvas, vui lòng bấm lại sau 2 giây.');
        if (btn) btn.innerHTML = '📸 Xuất ảnh Zalo';
        card.style.left = '-9999px';
        return;
      }

      html2canvas(card, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#0f172a'
      }).then(canvas => {
        card.style.left = '-9999px';
        
        canvas.toBlob(blob => {
          // 1. Download image
          const dateStr = new Date().toISOString().slice(0, 10);
          const a = document.createElement('a');
          a.download = `Bao_Cao_KPI_CTO1_${dateStr}.png`;
          a.href = URL.createObjectURL(blob);
          a.click();

          // 2. Clipboard copy
          if (navigator.clipboard && window.ClipboardItem) {
            navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
              .then(() => {
                showToast('🎉 Đã tải ảnh và COPY vào bộ nhớ tạm! Bạn chỉ cần nhấn Ctrl+V vào Zalo là gửi được ngay!');
              })
              .catch(() => {
                showToast('🎉 Đã tải file ảnh báo cáo xuống máy! Bạn hãy kéo ảnh gửi vào Zalo nhé.');
              });
          } else {
            showToast('🎉 Đã tải file ảnh báo cáo xuống máy! Bạn hãy kéo ảnh gửi vào Zalo nhé.');
          }
        }, 'image/png');
      }).catch(err => {
        console.error(err);
        card.style.left = '-9999px';
        showToast('⚠️ Không thể xuất ảnh: ' + err.message);
      }).finally(() => {
        if (btn) btn.innerHTML = '📸 Xuất ảnh Zalo';
      });
    }

    function exportCurrentTableToCSV() {
      let csvContent = "\uFEFF";
      csvContent += `STT,Ma NV,Ho va Ten,Team,Level,KPI Ticket,Dat KH,% KPI Ticket,KPI CV,Dat CV,% KPI CV,TK 2 CV Ho Tro,% KPI Tong,Tien Do Ngay ${currentDay}\n`;
      filteredKpi.forEach((x, idx) => {
        const p = x.pacing_info || calculatePacingDetails(x);
        csvContent += `"${idx+1}","${x.ma}","${x.name}","${x.team}","${x.level}","${x.kpi_ticket}","${x.slg_kh}","${(x.pct_kpi_ticket*100).toFixed(2)}%","${x.kpi_cv}","${x.slg_cv}","${(x.pct_kpi_cv*100).toFixed(2)}%","${x.no_ticket_2ht}","${(x.pct_kpi_tong*100).toFixed(2)}%","${p.text}"\n`;
      });
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `KPI_Export_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('📥 Đã xuất file CSV thành công!');
    }
