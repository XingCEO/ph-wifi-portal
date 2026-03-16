'use strict';

document.addEventListener('alpine:init', () => {
  Alpine.data('adminApp', () => ({
    // ── Tab state ──────────────────────────────────────────────────────────
    currentTab: 'dashboard',
    tabTitles: {
      dashboard: 'Dashboard', hotspots: '熱點管理', revenue: '收入分析', live: '即時監控',
      users: '用戶記錄', security: '資安中心', advertisers: '廣告主管理',
      devices: '設備管理', sessions: '連線管理', settings: '系統設定',
    },
    clockTime: '',

    // ── Dashboard ──────────────────────────────────────────────────────────
    dashStats: null,
    healthData: null,
    trendChart: null,

    // ── Hotspots ───────────────────────────────────────────────────────────
    hotspots: [],
    hotspotSearch: '',
    hotspotEditId: null,
    hotspotForm: { name: '', location: '', ap_mac: '', site_name: '', latitude: '', longitude: '' },
    showHotspotModal: false,
    showHsDetail: false,
    hsDetail: null,

    // ── Revenue ────────────────────────────────────────────────────────────
    revenueMonth: '',
    revData: null,
    revDailyData: null,
    revenueDateStart: '',
    revenueDateEnd: '',
    revenueChart: null,
    revDailyChart: null,

    // ── Live ───────────────────────────────────────────────────────────────
    liveData: null,
    liveCountdown: 15,
    _liveTimer: null,
    _liveCountdownTimer: null,

    // ── Users ──────────────────────────────────────────────────────────────
    users: [],
    usersTotal: 0,
    usersPage: 0,
    userSearch: '',
    userHotspotFilter: '',

    // ── Security ───────────────────────────────────────────────────────────
    secStats: null,
    auditLog: [],
    blockedCount: 0,

    // ── Advertisers ────────────────────────────────────────────────────────
    advertisers: [],
    advSearch: '',
    advForm: { name: '', contact: '', banner_url: '', click_url: '', monthly_fee_php: '', status: 'true', start_date: '', end_date: '', hotspot_ids: [] },
    advEditId: null,
    showAdvModal: false,

    // ── Devices ────────────────────────────────────────────────────────────
    blockedDevices: [],
    blockForm: { mac: '', reason: '', expires_at: '' },
    showBlockModal: false,
    deviceHistory: null,
    deviceLookupMac: '',

    // ── Sessions ───────────────────────────────────────────────────────────
    sessions: null,
    sessCountdown: 30,
    _sessTimer: null,
    _sessCountdownTimer: null,

    // ── Settings ───────────────────────────────────────────────────────────
    settingsData: null,
    settingsForm: {
      ad_duration_seconds: 30,
      session_duration_seconds: 3600,
      anti_spam_window_seconds: 3600,
    },
    omadaTestResult: '',

    // ── Confirm dialog ─────────────────────────────────────────────────────
    showConfirm: false,
    confirmMsg: '',
    confirmFn: null,

    // ── UI ──────────────────────────────────────────────────────────────────
    sidebarOpen: false,
    lastUpdate: '',

    // ════════════════════════════════════════════════════════════════════════
    // INIT
    // ════════════════════════════════════════════════════════════════════════
    init() {
      this.loadDashboard();
      this.updateClock();
      setInterval(() => this.updateClock(), 1000);
    },

    updateClock() {
      this.clockTime = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    },

    // ════════════════════════════════════════════════════════════════════════
    // TAB SWITCHING
    // ════════════════════════════════════════════════════════════════════════
    switchTab(tab) {
      // stop any running timers from previous tab
      this.stopLiveTimer();
      this.stopSessTimer();

      this.currentTab = tab;
      this.sidebarOpen = false;

      switch (tab) {
        case 'dashboard':   this.loadDashboard(); break;
        case 'hotspots':    this.loadHotspots(); break;
        case 'revenue':     this.loadRevenue(); break;
        case 'live':        this.loadLive(); this.startLiveTimer(); break;
        case 'users':       this.loadUsers(); break;
        case 'security':    this.loadSecurity(); break;
        case 'advertisers': this.loadAdvertisers(); break;
        case 'devices':     this.loadDevices(); break;
        case 'sessions':    this.loadSessions(); this.startSessTimer(); break;
        case 'settings':    this.loadSettings(); break;
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // DASHBOARD
    // ════════════════════════════════════════════════════════════════════════
    async loadDashboard() {
      try {
        const [statsRes, healthRes] = await Promise.all([
          fetch('/admin/api/stats'),
          fetch('/health'),
        ]);
        if (statsRes.ok) {
          this.dashStats = await statsRes.json();
          this.lastUpdate = this.fmtDate(new Date().toISOString());
          this.$nextTick(() => this.renderTrendChart());
        }
        if (healthRes.ok) {
          this.healthData = await healthRes.json();
        }
      } catch (e) {
        this.toast('Failed to load dashboard: ' + e.message, 'error');
      }
    },

    renderTrendChart() {
      const canvas = document.getElementById('chart-trend');
      if (!canvas) return;

      const trend = this.dashStats?.hotspots || [];
      if (!trend.length) return;

      if (this.trendChart) {
        this.trendChart.destroy();
        this.trendChart = null;
      }

      this.trendChart = new Chart(canvas, {
        type: 'bar',
        data: {
          labels: trend.map(t => t.hotspot_name || ''),
          datasets: [{
            label: 'Visits Today',
            data: trend.map(t => t.visits_today || 0),
            backgroundColor: 'rgba(0, 230, 118, 0.6)',
            borderColor: '#00e676',
            borderWidth: 1,
            borderRadius: 4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              ticks: { color: '#a1a1aa' },
              grid: { color: 'rgba(255,255,255,0.06)' },
            },
            y: {
              beginAtZero: true,
              ticks: { color: '#a1a1aa' },
              grid: { color: 'rgba(255,255,255,0.06)' },
            },
          },
        },
      });
    },

    // ════════════════════════════════════════════════════════════════════════
    // HOTSPOTS
    // ════════════════════════════════════════════════════════════════════════
    async loadHotspots() {
      try {
        const res = await fetch('/admin/api/hotspots');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.hotspots = await res.json();
      } catch (e) {
        this.toast('Failed to load hotspots: ' + e.message, 'error');
      }
    },

    get filteredHotspots() {
      if (!this.hotspotSearch) return this.hotspots;
      const q = this.hotspotSearch.toLowerCase();
      return this.hotspots.filter(h =>
        (h.name || '').toLowerCase().includes(q) ||
        (h.location || '').toLowerCase().includes(q)
      );
    },

    openHotspotModal(id) {
      if (id) {
        const h = this.hotspots.find(x => x.id === id);
        if (h) {
          this.hotspotEditId = id;
          this.hotspotForm = {
            name: h.name || '',
            location: h.location || '',
            ap_mac: h.ap_mac || '',
            site_name: h.site_name || '',
            latitude: h.latitude || '',
            longitude: h.longitude || '',
          };
        }
      } else {
        this.hotspotEditId = null;
        this.hotspotForm = { name: '', location: '', ap_mac: '', site_name: '', latitude: '', longitude: '' };
      }
      this.showHotspotModal = true;
    },

    async submitHotspot() {
      try {
        const url = this.hotspotEditId
          ? `/admin/api/hotspots/${this.hotspotEditId}`
          : '/admin/api/hotspots';
        const method = this.hotspotEditId ? 'PATCH' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.hotspotForm),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.showHotspotModal = false;
        this.toast(this.hotspotEditId ? 'Hotspot updated' : 'Hotspot created', 'success');
        await this.loadHotspots();
      } catch (e) {
        this.toast('Failed to save hotspot: ' + e.message, 'error');
      }
    },

    async toggleHotspot(id, currentActive) {
      try {
        const res = await fetch(`/admin/api/hotspots/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_active: !currentActive }),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.toast('Hotspot status updated', 'success');
        await this.loadHotspots();
      } catch (e) {
        this.toast('Failed to toggle hotspot: ' + e.message, 'error');
      }
    },

    async deleteHotspot(id) {
      this.showConfirmDialog('Are you sure you want to delete this hotspot?', async () => {
        try {
          const res = await fetch(`/admin/api/hotspots/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          this.toast('Hotspot deleted', 'success');
          await this.loadHotspots();
        } catch (e) {
          this.toast('Failed to delete hotspot: ' + e.message, 'error');
        }
      });
    },

    async openHsDetail(id) {
      try {
        const res = await fetch(`/admin/api/hotspots/${id}/detail`);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.hsDetail = await res.json();
        this.showHsDetail = true;
      } catch (e) {
        this.toast('Failed to load hotspot detail: ' + e.message, 'error');
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // REVENUE
    // ════════════════════════════════════════════════════════════════════════
    async loadRevenue() {
      try {
        const params = new URLSearchParams();
        if (this.revenueMonth) params.set('month', this.revenueMonth);
        const res = await fetch('/admin/api/revenue?' + params.toString());
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.revData = await res.json();
        this.$nextTick(() => this.renderRevenueChart());
      } catch (e) {
        this.toast('Failed to load revenue: ' + e.message, 'error');
      }
    },

    async loadRevenueDaily() {
      try {
        const params = new URLSearchParams();
        if (this.revenueDateStart) params.set('start', this.revenueDateStart);
        if (this.revenueDateEnd) params.set('end', this.revenueDateEnd);
        const res = await fetch('/admin/api/revenue/daily?' + params.toString());
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.revDailyData = await res.json();
        this.$nextTick(() => this.renderRevDailyChart());
      } catch (e) {
        this.toast('Failed to load daily revenue: ' + e.message, 'error');
      }
    },

    renderRevenueChart() {
      const canvas = document.getElementById('chart-revenue');
      if (!canvas || !this.revData) return;

      if (this.revenueChart) {
        this.revenueChart.destroy();
        this.revenueChart = null;
      }

      const data = this.revData;
      const labels = [];
      const values = [];
      const colors = [];
      const colorPalette = [
        '#00e676', '#2979ff', '#ff9100', '#e040fb', '#ffea00', '#00e5ff',
      ];

      if (data.breakdown_by_hotspot && data.breakdown_by_hotspot.length) {
        data.breakdown_by_hotspot.forEach((h, i) => {
          labels.push(h.hotspot_name || 'Hotspot ' + (i + 1));
          values.push(parseFloat(h.revenue_usd) || 0);
          colors.push(colorPalette[i % colorPalette.length]);
        });
      } else {
        labels.push('Ad Revenue', 'Direct Ads');
        values.push(parseFloat(data.adcash_revenue_usd) || 0, parseFloat(data.direct_revenue_php) || 0);
        colors.push('#00e676', '#2979ff');
      }

      this.revenueChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data: values,
            backgroundColor: colors,
            borderColor: 'rgba(0,0,0,0.3)',
            borderWidth: 1,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: '#a1a1aa' },
            },
          },
        },
      });
    },

    renderRevDailyChart() {
      const canvas = document.getElementById('chart-revenue-daily');
      if (!canvas || !this.revDailyData) return;

      if (this.revDailyChart) {
        this.revDailyChart.destroy();
        this.revDailyChart = null;
      }

      const daily = Array.isArray(this.revDailyData) ? this.revDailyData : (this.revDailyData.days || []);

      this.revDailyChart = new Chart(canvas, {
        type: 'line',
        data: {
          labels: daily.map(d => d.date || d.day || ''),
          datasets: [{
            label: 'Daily Revenue',
            data: daily.map(d => d.revenue || d.amount || 0),
            borderColor: '#00e676',
            backgroundColor: 'rgba(0, 230, 118, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointBackgroundColor: '#00e676',
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              ticks: { color: '#a1a1aa' },
              grid: { color: 'rgba(255,255,255,0.06)' },
            },
            y: {
              beginAtZero: true,
              ticks: { color: '#a1a1aa' },
              grid: { color: 'rgba(255,255,255,0.06)' },
            },
          },
        },
      });
    },

    // ════════════════════════════════════════════════════════════════════════
    // LIVE MONITOR
    // ════════════════════════════════════════════════════════════════════════
    async loadLive() {
      try {
        const res = await fetch('/admin/api/live');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.liveData = await res.json();
        this.liveCountdown = 15;
        this.lastUpdate = this.fmtDate(new Date().toISOString());
      } catch (e) {
        this.toast('Failed to load live data: ' + e.message, 'error');
      }
    },

    startLiveTimer() {
      this.stopLiveTimer();
      this._liveTimer = setInterval(() => {
        this.loadLive();
      }, 15000);
      this._liveCountdownTimer = setInterval(() => {
        if (this.liveCountdown > 0) this.liveCountdown--;
      }, 1000);
    },

    stopLiveTimer() {
      if (this._liveTimer) {
        clearInterval(this._liveTimer);
        this._liveTimer = null;
      }
      if (this._liveCountdownTimer) {
        clearInterval(this._liveCountdownTimer);
        this._liveCountdownTimer = null;
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // USERS (Visits)
    // ════════════════════════════════════════════════════════════════════════
    async loadUsers() {
      try {
        const params = new URLSearchParams();
        params.set('limit', '50');
        params.set('offset', String(this.usersPage * 50));
        if (this.userHotspotFilter) params.set('hotspot_id', this.userHotspotFilter);

        const res = await fetch('/admin/api/visits?' + params.toString());
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        this.users = data.items || data.visits || data || [];
        this.usersTotal = data.total || this.users.length;
      } catch (e) {
        this.toast('Failed to load users: ' + e.message, 'error');
      }
    },

    setPage(n) {
      this.usersPage = n;
      this.loadUsers();
    },

    get usersTotalPages() {
      return Math.max(1, Math.ceil(this.usersTotal / 50));
    },

    // ════════════════════════════════════════════════════════════════════════
    // SECURITY
    // ════════════════════════════════════════════════════════════════════════
    async loadSecurity() {
      try {
        const [statsRes, auditRes, blockedRes, healthRes] = await Promise.all([
          fetch('/admin/api/stats'),
          fetch('/admin/api/audit-log?limit=15'),
          fetch('/admin/api/devices/blocked'),
          fetch('/health'),
        ]);

        if (statsRes.ok) this.secStats = await statsRes.json();
        if (auditRes.ok) {
          const auditData = await auditRes.json();
          this.auditLog = Array.isArray(auditData) ? auditData : (auditData.items || []);
        }
        if (blockedRes.ok) {
          const blockedData = await blockedRes.json();
          const arr = Array.isArray(blockedData) ? blockedData : (blockedData.items || []);
          this.blockedCount = arr.length;
        }
        if (healthRes.ok) this.healthData = await healthRes.json();
      } catch (e) {
        this.toast('Failed to load security data: ' + e.message, 'error');
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // ADVERTISERS
    // ════════════════════════════════════════════════════════════════════════
    async loadAdvertisers() {
      try {
        const res = await fetch('/admin/api/advertisers');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        this.advertisers = Array.isArray(data) ? data : (data.items || []);
      } catch (e) {
        this.toast('Failed to load advertisers: ' + e.message, 'error');
      }
    },

    get filteredAdvertisers() {
      if (!this.advSearch) return this.advertisers;
      const q = this.advSearch.toLowerCase();
      return this.advertisers.filter(a =>
        (a.name || '').toLowerCase().includes(q) ||
        (a.contact || '').toLowerCase().includes(q)
      );
    },

    openAdvModal(id) {
      if (id) {
        const a = this.advertisers.find(x => x.id === id);
        if (a) {
          this.advEditId = id;
          this.advForm = {
            name: a.name || '',
            contact: a.contact || '',
            banner_url: a.banner_url || '',
            click_url: a.click_url || '',
            monthly_fee_php: a.monthly_fee_php || '',
            status: String(a.is_active),
            start_date: a.starts_at ? a.starts_at.slice(0, 10) : '',
            end_date: a.ends_at ? a.ends_at.slice(0, 10) : '',
            hotspot_ids: a.hotspot_ids || [],
          };
        }
      } else {
        this.advEditId = null;
        this.advForm = { name: '', contact: '', banner_url: '', click_url: '', monthly_fee_php: '', status: 'true', start_date: '', end_date: '', hotspot_ids: [] };
      }
      this.showAdvModal = true;
    },

    async submitAdvertiser() {
      try {
        const url = this.advEditId
          ? `/admin/api/advertisers/${this.advEditId}`
          : '/admin/api/advertisers';
        const method = this.advEditId ? 'PATCH' : 'POST';
        const payload = {
          name: this.advForm.name,
          contact: this.advForm.contact || null,
          banner_url: this.advForm.banner_url,
          click_url: this.advForm.click_url,
          monthly_fee_php: parseFloat(this.advForm.monthly_fee_php) || 0,
          is_active: this.advForm.status === 'true',
          starts_at: this.advForm.start_date ? new Date(this.advForm.start_date).toISOString() : null,
          ends_at: this.advForm.end_date ? new Date(this.advForm.end_date).toISOString() : null,
          hotspot_ids: this.advForm.hotspot_ids,
        };
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.showAdvModal = false;
        this.toast(this.advEditId ? 'Advertiser updated' : 'Advertiser created', 'success');
        await this.loadAdvertisers();
      } catch (e) {
        this.toast('Failed to save advertiser: ' + e.message, 'error');
      }
    },

    async deleteAdvertiser(id) {
      this.showConfirmDialog('Are you sure you want to delete this advertiser?', async () => {
        try {
          const res = await fetch(`/admin/api/advertisers/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          this.toast('Advertiser deleted', 'success');
          await this.loadAdvertisers();
        } catch (e) {
          this.toast('Failed to delete advertiser: ' + e.message, 'error');
        }
      });
    },

    // ════════════════════════════════════════════════════════════════════════
    // DEVICES
    // ════════════════════════════════════════════════════════════════════════
    async loadDevices() {
      try {
        const res = await fetch('/admin/api/devices/blocked');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        this.blockedDevices = Array.isArray(data) ? data : (data.items || []);
      } catch (e) {
        this.toast('Failed to load blocked devices: ' + e.message, 'error');
      }
    },

    openBlockModal() {
      this.blockForm = { mac: '', reason: '', expires_at: '' };
      this.showBlockModal = true;
    },

    closeBlockModal() {
      this.showBlockModal = false;
    },

    async submitBlock() {
      try {
        const payload = {
          client_mac: this.blockForm.mac,
          reason: this.blockForm.reason || null,
          expires_at: this.blockForm.expires_at ? new Date(this.blockForm.expires_at).toISOString() : null,
        };
        const res = await fetch('/admin/api/devices/block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.showBlockModal = false;
        this.toast('Device blocked', 'success');
        await this.loadDevices();
      } catch (e) {
        this.toast('Failed to block device: ' + e.message, 'error');
      }
    },

    async unblockDevice(id) {
      this.showConfirmDialog('Are you sure you want to unblock this device?', async () => {
        try {
          const res = await fetch(`/admin/api/devices/block/${id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          this.toast('Device unblocked', 'success');
          await this.loadDevices();
        } catch (e) {
          this.toast('Failed to unblock device: ' + e.message, 'error');
        }
      });
    },

    async lookupDevice() {
      if (!this.deviceLookupMac) {
        this.toast('Please enter a MAC address', 'error');
        return;
      }
      try {
        const mac = encodeURIComponent(this.deviceLookupMac);
        const res = await fetch(`/admin/api/devices/${mac}/history`);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.deviceHistory = await res.json();
      } catch (e) {
        this.toast('Failed to lookup device: ' + e.message, 'error');
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // SESSIONS
    // ════════════════════════════════════════════════════════════════════════
    async loadSessions() {
      try {
        const res = await fetch('/admin/api/sessions/active');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.sessions = await res.json();
        this.sessCountdown = 30;
        this.lastUpdate = this.fmtDate(new Date().toISOString());
      } catch (e) {
        this.toast('Failed to load sessions: ' + e.message, 'error');
      }
    },

    async revokeSession(id) {
      this.showConfirmDialog('Are you sure you want to revoke this session?', async () => {
        try {
          const res = await fetch(`/admin/api/sessions/${id}/revoke`, { method: 'POST' });
          if (!res.ok) throw new Error('HTTP ' + res.status);
          this.toast('Session revoked', 'success');
          await this.loadSessions();
        } catch (e) {
          this.toast('Failed to revoke session: ' + e.message, 'error');
        }
      });
    },

    startSessTimer() {
      this.stopSessTimer();
      this._sessTimer = setInterval(() => {
        this.loadSessions();
      }, 30000);
      this._sessCountdownTimer = setInterval(() => {
        if (this.sessCountdown > 0) this.sessCountdown--;
      }, 1000);
    },

    stopSessTimer() {
      if (this._sessTimer) {
        clearInterval(this._sessTimer);
        this._sessTimer = null;
      }
      if (this._sessCountdownTimer) {
        clearInterval(this._sessCountdownTimer);
        this._sessCountdownTimer = null;
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // SETTINGS
    // ════════════════════════════════════════════════════════════════════════
    async loadSettings() {
      try {
        const res = await fetch('/admin/api/settings');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.settingsData = await res.json();
        this.settingsForm = {
          ad_duration_seconds: this.settingsData.ad_duration_seconds ?? 30,
          session_duration_seconds: this.settingsData.session_duration_seconds ?? 3600,
          anti_spam_window_seconds: this.settingsData.anti_spam_window_seconds ?? 3600,
        };
        this.omadaTestResult = '';
      } catch (e) {
        this.toast('Failed to load settings: ' + e.message, 'error');
      }
    },

    async saveSettings() {
      try {
        const payload = {
          ad_duration_seconds: parseInt(this.settingsForm.ad_duration_seconds) || null,
          session_duration_seconds: parseInt(this.settingsForm.session_duration_seconds) || null,
          anti_spam_window_seconds: parseInt(this.settingsForm.anti_spam_window_seconds) || null,
        };

        const res = await fetch('/admin/api/settings', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.toast('Settings saved', 'success');
        await this.loadSettings();
      } catch (e) {
        this.toast('Failed to save settings: ' + e.message, 'error');
      }
    },

    async testOmada() {
      this.omadaTestResult = 'Testing...';
      try {
        const res = await fetch('/admin/api/settings/test-omada', { method: 'POST' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        this.omadaTestResult = data.status === 'ok'
          ? 'Connection successful!'
          : 'Connection failed: ' + (data.message || 'Unknown error');
      } catch (e) {
        this.omadaTestResult = 'Connection failed: ' + e.message;
      }
    },

    // ════════════════════════════════════════════════════════════════════════
    // EXPORT HELPERS
    // ════════════════════════════════════════════════════════════════════════
    exportVisits() {
      window.location.href = '/admin/api/export/visits';
    },

    exportRevenue() {
      window.location.href = '/admin/api/export/revenue';
    },

    exportDevices() {
      window.location.href = '/admin/api/export/devices';
    },

    // ════════════════════════════════════════════════════════════════════════
    // CONFIRM DIALOG
    // ════════════════════════════════════════════════════════════════════════
    showConfirmDialog(msg, fn) {
      this.confirmMsg = msg;
      this.confirmFn = fn;
      this.showConfirm = true;
    },

    async confirmAction() {
      this.showConfirm = false;
      if (this.confirmFn) {
        try {
          await this.confirmFn();
        } catch (e) {
          this.toast('Action failed: ' + e.message, 'error');
        }
        this.confirmFn = null;
      }
    },

    cancelConfirm() {
      this.showConfirm = false;
      this.confirmFn = null;
    },

    // ════════════════════════════════════════════════════════════════════════
    // TOAST NOTIFICATION
    // ════════════════════════════════════════════════════════════════════════
    toast(msg, type) {
      type = type || 'info';
      const container = document.getElementById('toast-container')
        || this._createToastContainer();

      const el = document.createElement('div');
      el.className = 'toast toast-' + this.esc(type);
      el.textContent = msg;
      container.appendChild(el);

      // Trigger enter animation
      requestAnimationFrame(() => el.classList.add('toast-show'));

      setTimeout(() => {
        el.classList.remove('toast-show');
        el.classList.add('toast-hide');
        setTimeout(() => el.remove(), 300);
      }, 3500);
    },

    _createToastContainer() {
      const c = document.createElement('div');
      c.id = 'toast-container';
      c.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:10000;display:flex;flex-direction:column;gap:0.5rem;pointer-events:none;';
      document.body.appendChild(c);
      return c;
    },

    // ════════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ════════════════════════════════════════════════════════════════════════
    esc(s) {
      if (s == null) return '';
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    fmt(n) {
      if (n == null) return '--';
      return Number(n).toLocaleString('zh-TW');
    },

    fmtDate(s) {
      if (!s) return '--';
      try {
        const d = new Date(s);
        return d.toLocaleString('zh-TW', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });
      } catch {
        return s;
      }
    },

    truncate(s, n) {
      if (!s) return '';
      n = n || 30;
      return s.length > n ? s.slice(0, n) + '...' : s;
    },
  }));
});
