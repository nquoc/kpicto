/* ============================================================
   MAIN APPLICATION CONTROLLER & NAVIGATION
   ============================================================ */
    function showToast(msg) {
      const old = document.querySelector('.toast-msg');
      if (old) old.remove();
      const toast = document.createElement('div');
      toast.className = 'toast-msg';
      toast.innerHTML = `<span>${msg}</span>`;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.style.transition = 'opacity 0.5s ease';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
      }, 5000);
    }

    // ==========================================

    function switchMainView(view) {
      if (view === 'schedule') view = 'ot';
      currentMainView = view;
      document.body.classList.toggle('view-is-ot', view === 'ot');
      document.body.classList.toggle('view-is-kpi', view === 'kpi');

      const kpiMain = document.getElementById('section-kpi-main');
      const otPane = document.getElementById('tab-pane-ot');
      const tabKpi = document.getElementById('nav-tab-kpi');
      const tabOt = document.getElementById('nav-tab-ot');
      const hdrBtn = document.getElementById('hdr-btn-toggle-sched');

      if (kpiMain) kpiMain.style.display = (view === 'kpi') ? 'block' : 'none';
      if (otPane) otPane.style.display = (view === 'ot') ? 'block' : 'none';

      if (tabKpi) tabKpi.classList.toggle('active', view === 'kpi');
      if (tabOt) tabOt.classList.toggle('active', view === 'ot');

      if (hdrBtn) {
        if (view === 'kpi') {
          hdrBtn.innerHTML = '⏰ Lịch Trực & Giờ OT';
        } else {
          hdrBtn.innerHTML = '📊 Quay lại Báo Cáo KPI';
        }
      }

      if (view === 'ot') {
        renderOtTracker();
      }

      try {
        if (window.location.hash.replace('#', '') !== view) {
          if (window.history && window.history.replaceState) {
            window.history.replaceState(null, '', '#' + view);
          }
        }
      } catch (e) {}
    }

    function toggleMainView() {
      if (currentMainView === 'kpi') switchMainView('ot');
      else switchMainView('kpi');
    }


    // TV Kiosk Mode
    let tvInterval = null;
    let tvProgressInterval = null;
    let tvSlideIndex = 0;
    const TV_SLIDES = ['kpi', 'podium'];
    const TV_SLIDE_DURATION = 15000;

    function toggleTvMode() {
      const isTv = document.body.classList.toggle('tv-kiosk-mode');
      if (isTv) {
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
        startTvLoop();
        showToast('📺 Đã bật Chế độ TV! Đang xoay vòng hiển thị mỗi 15 giây. Nhấn ESC để thoát.');
      } else {
        stopTvLoop();
        if (document.exitFullscreen && document.fullscreenElement) {
          document.exitFullscreen().catch(() => {});
        }
        showToast('Đã thoát Chế độ TV.');
      }
    }

    function startTvLoop() {
      stopTvLoop();
      tvSlideIndex = 0;
      switchTab(TV_SLIDES[tvSlideIndex]);
      animateTvProgress();

      tvInterval = setInterval(() => {
        tvSlideIndex = (tvSlideIndex + 1) % TV_SLIDES.length;
        switchTab(TV_SLIDES[tvSlideIndex]);
        animateTvProgress();
      }, TV_SLIDE_DURATION);
    }

    function stopTvLoop() {
      if (tvInterval) clearInterval(tvInterval);
      if (tvProgressInterval) clearInterval(tvProgressInterval);
      tvInterval = null;
      tvProgressInterval = null;
      const bar = document.getElementById('tv-progress-bar');
      if (bar) bar.style.width = '0%';
    }

    function animateTvProgress() {
      const bar = document.getElementById('tv-progress-bar');
      if (!bar) return;
      if (tvProgressInterval) clearInterval(tvProgressInterval);
      let start = Date.now();
      tvProgressInterval = setInterval(() => {
        let elapsed = Date.now() - start;
        let pct = Math.min((elapsed / TV_SLIDE_DURATION) * 100, 100);
        bar.style.width = pct + '%';
        if (elapsed >= TV_SLIDE_DURATION) {
          clearInterval(tvProgressInterval);
        }
      }, 100);
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.body.classList.contains('tv-kiosk-mode')) {
        toggleTvMode();
      }
    });

    document.addEventListener('fullscreenchange', () => {
      if (!document.fullscreenElement && document.body.classList.contains('tv-kiosk-mode')) {
        toggleTvMode();
      }
    });

    function toggleTheme() {
      document.body.classList.toggle('light-theme');
      const isLight = document.body.classList.contains('light-theme');
      document.getElementById('theme-icon').innerText = isLight ? '☀️' : '🌙';
    }

    function init() {
      document.getElementById('lbl-updated-at').innerText = DATA.updated_at;
      document.getElementById('input-current-day').value = currentDay;
      if (document.getElementById('input-total-days')) {
        document.getElementById('input-total-days').value = totalDays;
      }
      updatePacingDisplay();
      buildMyNameOptions();
      renderPodiumAndAwards();
      if (typeof initSchedule === 'function') {
        initSchedule();
      }
      if (typeof setupOtSearch === 'function') {
        setupOtSearch();
      }
      applyFilters();

      // Kích hoạt đọc trực tiếp Realtime từ Google Sheets
      fetchRealtimeSheetsData(false);
      setInterval(() => fetchRealtimeSheetsData(false), 30000);

      // Mặc định hoặc khởi động theo view (từ window.DEFAULT_MAIN_VIEW hoặc hash URL)
      let hash = window.location.hash ? window.location.hash.replace('#', '').toLowerCase() : '';
      if (hash === 'schedule') hash = 'ot';
      let initialView = window.DEFAULT_MAIN_VIEW || (['kpi', 'ot'].includes(hash) ? hash : 'kpi');
      if (initialView === 'schedule') initialView = 'ot';
      if (initialView && initialView !== 'kpi') {
        switchMainView(initialView);
      }
    }

    window.onload = function() {
      init();
    };

    window.addEventListener('hashchange', () => {
      let hash = window.location.hash ? window.location.hash.replace('#', '').toLowerCase() : '';
      if (hash === 'schedule') hash = 'ot';
      if (['kpi', 'ot'].includes(hash) && hash !== currentMainView) {
        switchMainView(hash);
      }
    });
