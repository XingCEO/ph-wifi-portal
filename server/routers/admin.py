from __future__ import annotations

import base64
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdView, DirectAdvertiser, Hotspot, Visit, get_db
from models.schemas import (
    DirectAdvertiserCreate,
    DirectAdvertiserResponse,
    HotspotCreate,
    HotspotResponse,
    RevenueResponse,
    StatsResponse,
    HotspotStats,
)
from services.omada import OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


def verify_basic_auth(request: Request) -> None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    if not (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>PH WiFi — Admin Console</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --primary:#6366f1;--primary-light:#e0e7ff;--primary-dark:#4f46e5;
  --success:#10b981;--warning:#f59e0b;--danger:#ef4444;--info:#3b82f6;
  --gray-50:#f9fafb;--gray-100:#f3f4f6;--gray-200:#e5e7eb;--gray-300:#d1d5db;
  --gray-400:#9ca3af;--gray-500:#6b7280;--gray-600:#4b5563;--gray-700:#374151;
  --gray-800:#1f2937;--gray-900:#111827;
  --sidebar-w:240px;--header-h:60px;
  --radius:12px;--radius-sm:8px;
  --shadow:0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.06);
  --shadow-md:0 4px 6px rgba(0,0,0,.07),0 2px 4px rgba(0,0,0,.06);
  --shadow-lg:0 10px 15px rgba(0,0,0,.08),0 4px 6px rgba(0,0,0,.05);
}
html,body{height:100%;font-family:'Inter',system-ui,-apple-system,sans-serif;font-size:14px;color:var(--gray-800);background:var(--gray-50)}

/* ── Layout ── */
#app{display:flex;height:100vh;overflow:hidden}
#sidebar{width:var(--sidebar-w);min-width:var(--sidebar-w);background:#fff;border-right:1px solid var(--gray-200);display:flex;flex-direction:column;z-index:100;transition:transform .3s}
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#topbar{height:var(--header-h);background:#fff;border-bottom:1px solid var(--gray-200);display:flex;align-items:center;padding:0 24px;gap:12px;flex-shrink:0}
#content{flex:1;overflow-y:auto;padding:24px}

/* ── Sidebar ── */
.sidebar-logo{padding:18px 20px 16px;border-bottom:1px solid var(--gray-100)}
.sidebar-logo h1{font-size:17px;font-weight:700;color:var(--primary);letter-spacing:-.3px}
.sidebar-logo p{font-size:11px;color:var(--gray-400);margin-top:2px}
.sidebar-nav{flex:1;padding:12px 10px;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:var(--radius-sm);cursor:pointer;color:var(--gray-600);font-weight:500;font-size:13.5px;transition:all .15s;margin-bottom:2px;border:none;background:none;width:100%;text-align:left}
.nav-item:hover{background:var(--gray-100);color:var(--gray-900)}
.nav-item.active{background:var(--primary-light);color:var(--primary);font-weight:600}
.nav-item .icon{font-size:16px;width:20px;text-align:center;flex-shrink:0}
.sidebar-footer{padding:16px;border-top:1px solid var(--gray-100);font-size:12px;color:var(--gray-400)}

/* ── Topbar ── */
#menu-toggle{display:none;background:none;border:none;font-size:20px;cursor:pointer;color:var(--gray-600)}
.topbar-title{font-weight:600;font-size:16px;color:var(--gray-900);flex:1}
.topbar-badge{background:var(--primary-light);color:var(--primary);padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600}
#last-update{font-size:12px;color:var(--gray-400)}

/* ── Cards ── */
.card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);border:1px solid var(--gray-200);padding:20px}
.card-title{font-size:13px;font-weight:600;color:var(--gray-500);text-transform:uppercase;letter-spacing:.5px;margin-bottom:16px}

/* ── KPI Grid ── */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:20px}
.kpi-card{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);border:1px solid var(--gray-200);padding:20px;display:flex;flex-direction:column;gap:6px}
.kpi-label{font-size:12px;font-weight:500;color:var(--gray-500);text-transform:uppercase;letter-spacing:.4px}
.kpi-value{font-size:28px;font-weight:700;color:var(--gray-900);line-height:1.2}
.kpi-sub{font-size:12px;color:var(--gray-400)}
.kpi-icon{font-size:24px;margin-bottom:4px}
.kpi-card.success .kpi-value{color:var(--success)}
.kpi-card.warning .kpi-value{color:var(--warning)}
.kpi-card.danger .kpi-value{color:var(--danger)}
.kpi-card.primary .kpi-value{color:var(--primary)}

/* ── Section Grid ── */
.section-grid{display:grid;gap:16px}
.section-grid.cols-2{grid-template-columns:1fr 1fr}
.section-grid.cols-3{grid-template-columns:2fr 1fr}

/* ── Tables ── */
.table-wrap{overflow-x:auto;border-radius:var(--radius-sm)}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{padding:10px 14px;text-align:left;font-size:11px;font-weight:600;color:var(--gray-500);text-transform:uppercase;letter-spacing:.4px;background:var(--gray-50);border-bottom:1px solid var(--gray-200)}
tbody tr{border-bottom:1px solid var(--gray-100);transition:background .1s}
tbody tr:nth-child(even){background:var(--gray-50)}
tbody tr:hover{background:var(--primary-light)}
tbody td{padding:10px 14px;color:var(--gray-700)}

/* ── Badge ── */
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;line-height:1.4}
.badge.success{background:#d1fae5;color:#065f46}
.badge.warning{background:#fef3c7;color:#92400e}
.badge.danger{background:#fee2e2;color:#991b1b}
.badge.info{background:#dbeafe;color:#1e40af}
.badge.gray{background:var(--gray-100);color:var(--gray-600)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.dot.success{background:var(--success)}
.dot.danger{background:var(--danger)}
.dot.warning{background:var(--warning)}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;cursor:pointer;border:1px solid transparent;transition:all .15s;line-height:1}
.btn-primary{background:var(--primary);color:#fff;border-color:var(--primary)}
.btn-primary:hover{background:var(--primary-dark)}
.btn-outline{background:#fff;color:var(--gray-700);border-color:var(--gray-300)}
.btn-outline:hover{background:var(--gray-50)}
.btn-danger{background:var(--danger);color:#fff;border-color:var(--danger)}
.btn-sm{padding:5px 10px;font-size:12px}

/* ── Forms ── */
.form-group{margin-bottom:16px}
.form-label{display:block;font-size:13px;font-weight:500;color:var(--gray-700);margin-bottom:6px}
.form-control{width:100%;padding:9px 12px;border:1px solid var(--gray-300);border-radius:var(--radius-sm);font-size:13px;color:var(--gray-800);background:#fff;outline:none;transition:border-color .15s}
.form-control:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(99,102,241,.1)}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form-select{appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236b7280' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px}

/* ── Search ── */
.search-wrap{position:relative;max-width:300px}
.search-wrap input{padding-left:36px}
.search-icon{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--gray-400);font-size:14px;pointer-events:none}

/* ── Tabs Content ── */
.tab-pane{display:none;animation:fadeIn .2s ease}
.tab-pane.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}

/* ── Chart containers ── */
.chart-container{position:relative;height:260px}
.chart-sm{height:200px}

/* ── Live monitor ── */
.live-count{font-size:72px;font-weight:800;color:var(--primary);line-height:1;text-align:center;padding:20px 0}
.live-label{text-align:center;font-size:15px;color:var(--gray-500);margin-bottom:24px}
.pulse{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--success);animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.5)}50%{box-shadow:0 0 0 8px rgba(16,185,129,0)}}

/* ── Health Grid ── */
.health-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.health-item{background:var(--gray-50);border:1px solid var(--gray-200);border-radius:var(--radius-sm);padding:14px;text-align:center}
.health-item .h-label{font-size:11px;color:var(--gray-500);font-weight:500;text-transform:uppercase;letter-spacing:.4px}
.health-item .h-value{font-size:18px;font-weight:700;margin-top:4px}
.health-item.ok .h-value{color:var(--success)}
.health-item.warn .h-value{color:var(--warning)}
.health-item.err .h-value{color:var(--danger)}

/* ── Security ── */
.sec-section{margin-bottom:20px}
.sec-section h3{font-size:13px;font-weight:600;color:var(--gray-700);margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--gray-200)}
.ip-stat-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--gray-100)}
.ip-stat-item:last-child{border-bottom:none}

/* ── Modal ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1000;align-items:center;justify-content:center}
.modal-overlay.show{display:flex}
.modal{background:#fff;border-radius:var(--radius);box-shadow:var(--shadow-lg);width:520px;max-width:95vw;max-height:90vh;overflow-y:auto}
.modal-header{padding:20px 24px 16px;border-bottom:1px solid var(--gray-200);display:flex;justify-content:space-between;align-items:center}
.modal-header h2{font-size:16px;font-weight:600}
.modal-close{background:none;border:none;font-size:20px;cursor:pointer;color:var(--gray-400);line-height:1}
.modal-body{padding:24px}
.modal-footer{padding:16px 24px;border-top:1px solid var(--gray-200);display:flex;justify-content:flex-end;gap:10px}

/* ── Toast ── */
#toast-container{position:fixed;bottom:20px;right:20px;z-index:2000;display:flex;flex-direction:column;gap:8px}
.toast{padding:12px 18px;border-radius:var(--radius-sm);color:#fff;font-size:13px;font-weight:500;box-shadow:var(--shadow-md);animation:slideIn .3s ease;max-width:300px}
.toast.success{background:var(--success)}
.toast.error{background:var(--danger)}
.toast.info{background:var(--primary)}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* ── Spinner ── */
.spinner{display:inline-block;width:20px;height:20px;border:2px solid var(--gray-200);border-top-color:var(--primary);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-state{display:flex;align-items:center;gap:10px;color:var(--gray-500);padding:20px}
.empty-state{text-align:center;padding:40px;color:var(--gray-400)}
.empty-state .empty-icon{font-size:40px;margin-bottom:8px}

/* ── Responsive ── */
@media(max-width:768px){
  #sidebar{position:fixed;top:0;left:0;height:100vh;transform:translateX(-100%)}
  #sidebar.open{transform:translateX(0);box-shadow:var(--shadow-lg)}
  #menu-toggle{display:block}
  .section-grid.cols-2,.section-grid.cols-3{grid-template-columns:1fr}
  .form-row{grid-template-columns:1fr}
  .kpi-grid{grid-template-columns:1fr 1fr}
  #content{padding:16px}
}
@media(max-width:480px){
  .kpi-grid{grid-template-columns:1fr}
  .live-count{font-size:54px}
}
</style>
</head>
<body>
<div id="app">

<!-- ══ Sidebar ══ -->
<aside id="sidebar">
  <div class="sidebar-logo">
    <h1>&#128246; PH WiFi</h1>
    <p>Admin Console v2.0</p>
  </div>
  <nav class="sidebar-nav">
    <button class="nav-item active" onclick="switchTab('dashboard',this)" data-tab="dashboard">
      <span class="icon">&#128202;</span>Dashboard
    </button>
    <button class="nav-item" onclick="switchTab('hotspots',this)" data-tab="hotspots">
      <span class="icon">&#128225;</span>熱點管理
    </button>
    <button class="nav-item" onclick="switchTab('revenue',this)" data-tab="revenue">
      <span class="icon">&#128176;</span>收入分析
    </button>
    <button class="nav-item" onclick="switchTab('live',this)" data-tab="live">
      <span class="icon">&#128308;</span>即時監控
    </button>
    <button class="nav-item" onclick="switchTab('users',this)" data-tab="users">
      <span class="icon">&#128101;</span>用戶記錄
    </button>
    <button class="nav-item" onclick="switchTab('security',this)" data-tab="security">
      <span class="icon">&#128274;</span>資安中心
    </button>
  </nav>
  <div class="sidebar-footer">
    <div>PH WiFi System</div>
    <div id="sf-time"></div>
  </div>
</aside>

<!-- ══ Main ══ -->
<div id="main">
  <header id="topbar">
    <button id="menu-toggle" onclick="toggleSidebar()">&#9776;</button>
    <div class="topbar-title" id="topbar-title">Dashboard</div>
    <span id="live-indicator" style="display:none"><span class="pulse"></span></span>
    <span class="topbar-badge" id="topbar-badge">LIVE</span>
    <span id="last-update"></span>
  </header>

  <main id="content">

    <!-- ── Tab: Dashboard ── -->
    <div id="tab-dashboard" class="tab-pane active">
      <div class="kpi-grid" id="dash-kpis">
        <div class="loading-state"><span class="spinner"></span> 載入中...</div>
      </div>
      <div class="section-grid cols-3" style="margin-bottom:20px">
        <div class="card">
          <div class="card-title">7 天訪問趨勢</div>
          <div class="chart-container"><canvas id="chart-trend"></canvas></div>
        </div>
        <div class="card">
          <div class="card-title">&#128139; 系統健康</div>
          <div id="health-grid" class="health-grid">
            <div class="loading-state"><span class="spinner"></span></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">&#128205; 熱點狀態概覽</div>
        <div class="table-wrap">
          <table id="dash-hotspot-table">
            <thead><tr><th>名稱</th><th>地點</th><th>今日用戶</th><th>在線</th><th>狀態</th></tr></thead>
            <tbody id="dash-hotspot-body">
              <tr><td colspan="5"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Tab: Hotspots ── -->
    <div id="tab-hotspots" class="tab-pane">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:gap">
        <div class="search-wrap">
          <span class="search-icon">&#128269;</span>
          <input class="form-control" id="hs-search" placeholder="搜尋熱點名稱或地點..." oninput="filterHotspots()" style="padding-left:36px">
        </div>
        <button class="btn btn-primary" onclick="openAddModal()">+ 新增熱點</button>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th><th>名稱</th><th>地點</th><th>AP MAC</th><th>Site</th><th>座標</th><th>今日訪問</th><th>狀態</th><th>操作</th>
              </tr>
            </thead>
            <tbody id="hs-table-body">
              <tr><td colspan="9"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Tab: Revenue ── -->
    <div id="tab-revenue" class="tab-pane">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;flex-wrap:wrap">
        <label class="form-label" style="margin:0">月份：</label>
        <input type="month" class="form-control" id="rev-month" style="width:160px" onchange="loadRevenue()">
        <button class="btn btn-primary" onclick="loadRevenue()">查詢</button>
      </div>
      <div class="kpi-grid" id="rev-kpis">
        <div class="loading-state"><span class="spinner"></span> 選擇月份後載入...</div>
      </div>
      <div class="section-grid cols-2" style="margin-top:16px">
        <div class="card">
          <div class="card-title">各熱點收入分解</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>熱點</th><th>地點</th><th>廣告展示</th><th>收入 (PHP)</th><th>佔比</th></tr></thead>
              <tbody id="rev-table-body">
                <tr><td colspan="5" class="empty-state">請選擇月份</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-title">收入分佈</div>
          <div class="chart-container chart-sm"><canvas id="chart-revenue"></canvas></div>
        </div>
      </div>
    </div>

    <!-- ── Tab: Live ── -->
    <div id="tab-live" class="tab-pane">
      <div class="card" style="margin-bottom:16px;text-align:center">
        <div class="live-count" id="live-total">—</div>
        <div class="live-label">
          <span class="pulse"></span>&nbsp;
          目前在線人數 &nbsp;|&nbsp;
          <span id="live-refresh-countdown">15</span>s 後自動刷新
        </div>
        <button class="btn btn-outline" onclick="loadLive()">立即刷新</button>
      </div>
      <div class="card">
        <div class="card-title">各熱點即時狀態</div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>熱點</th><th>地點</th><th>在線人數</th><th>今日訪問</th><th>最後活動</th><th>狀態</th></tr></thead>
            <tbody id="live-table-body">
              <tr><td colspan="6"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Tab: Users ── -->
    <div id="tab-users" class="tab-pane">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px">
        <div class="search-wrap">
          <span class="search-icon">&#128269;</span>
          <input class="form-control" id="usr-search" placeholder="搜尋 MAC / IP / 熱點..." oninput="filterUsers()" style="padding-left:36px">
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="form-control form-select" id="usr-hotspot-filter" onchange="filterUsers()" style="width:160px">
            <option value="">所有熱點</option>
          </select>
          <button class="btn btn-outline" onclick="loadUsers()">重新載入</button>
        </div>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>MAC 地址</th><th>熱點</th><th>IP 地址</th><th>訪問時間</th><th>User Agent</th></tr>
            </thead>
            <tbody id="usr-table-body">
              <tr><td colspan="6"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
        <div id="usr-pagination" style="display:flex;justify-content:flex-end;padding:12px 0;gap:8px"></div>
      </div>
    </div>

    <!-- ── Tab: Security ── -->
    <div id="tab-security" class="tab-pane">
      <div class="section-grid cols-2">
        <div>
          <div class="card sec-section" style="margin-bottom:16px">
            <div class="sec-section">
              <h3>&#128202; 今日請求統計</h3>
              <div id="sec-stats">
                <div class="loading-state"><span class="spinner"></span></div>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="sec-section">
              <h3>&#128683; 異常 MAC 地址（短時間多次請求）</h3>
              <div id="sec-anomaly">
                <div class="empty-state"><div class="empty-icon">&#10003;</div>暫無異常</div>
              </div>
            </div>
          </div>
        </div>
        <div>
          <div class="card" style="margin-bottom:16px">
            <div class="sec-section">
              <h3>&#127758; IP 存取統計</h3>
              <div id="sec-ip-stats">
                <div class="loading-state"><span class="spinner"></span></div>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="sec-section">
              <h3>&#128221; Admin 登入記錄</h3>
              <div id="sec-login-log">載入中...</div>
            </div>
            <div class="sec-section" style="margin-top:16px">
              <h3>&#128295; 系統資訊</h3>
              <div id="sec-sysinfo">
                <div class="loading-state"><span class="spinner"></span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </main>
</div>
</div><!-- #app -->

<!-- ══ Add Hotspot Modal ══ -->
<div class="modal-overlay" id="add-modal">
  <div class="modal">
    <div class="modal-header">
      <h2>&#128205; 新增熱點</h2>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">熱點名稱 *</label>
          <input class="form-control" id="f-name" placeholder="e.g. Mall Entrance">
        </div>
        <div class="form-group">
          <label class="form-label">地點 *</label>
          <input class="form-control" id="f-location" placeholder="e.g. SM City Cebu">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">AP MAC 地址</label>
          <input class="form-control" id="f-mac" placeholder="AA:BB:CC:DD:EE:FF">
        </div>
        <div class="form-group">
          <label class="form-label">Omada Site</label>
          <input class="form-control" id="f-site" placeholder="default">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">緯度 (Latitude)</label>
          <input class="form-control" id="f-lat" placeholder="10.3157" type="number" step="any">
        </div>
        <div class="form-group">
          <label class="form-label">經度 (Longitude)</label>
          <input class="form-control" id="f-lng" placeholder="123.8854" type="number" step="any">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">備註</label>
        <input class="form-control" id="f-note" placeholder="選填備註">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" onclick="submitAddHotspot()">確認新增</button>
    </div>
  </div>
</div>

<div id="toast-container"></div>

<script>
const AUTH = 'Basic eGluZ2Nlbzp4aW5nd2lmaTIwMjY=';
const headers = { 'Authorization': AUTH, 'Content-Type': 'application/json' };
const headersGet = { 'Authorization': AUTH };

let trendChart = null;
let revenueChart = null;
let liveTimer = null;
let liveCountdown = 15;
let allHotspots = [];
let allUsers = [];
let usersPage = 0;
const PAGE_SIZE = 50;

// ── Helpers ──
function toast(msg, type='info') {
  const d = document.createElement('div');
  d.className = 'toast ' + type;
  d.textContent = msg;
  document.getElementById('toast-container').appendChild(d);
  setTimeout(() => d.remove(), 3500);
}

function fmt(n) { return n == null ? '—' : Number(n).toLocaleString(); }
function fmtDate(s) {
  if (!s) return '—';
  try { return new Date(s).toLocaleString('zh-TW', {hour12:false}); } catch(e) { return s; }
}
function truncate(s, n=40) { return s && s.length > n ? s.slice(0, n) + '...' : (s || '—'); }

function setLastUpdate() {
  document.getElementById('last-update').textContent = '更新：' + new Date().toLocaleTimeString('zh-TW', {hour12:false});
}

function sidebarTime() {
  document.getElementById('sf-time').textContent = new Date().toLocaleTimeString('zh-TW', {hour12:false});
}
setInterval(sidebarTime, 1000);

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}
document.addEventListener('click', e => {
  const sb = document.getElementById('sidebar');
  if (window.innerWidth <= 768 && !sb.contains(e.target) && !document.getElementById('menu-toggle').contains(e.target)) {
    sb.classList.remove('open');
  }
});

// ── Tab switching ──
const tabTitles = { dashboard:'Dashboard', hotspots:'熱點管理', revenue:'收入分析', live:'即時監控', users:'用戶記錄', security:'資安中心' };
function switchTab(tab, el) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.getElementById('topbar-title').textContent = tabTitles[tab] || tab;
  const li = document.getElementById('live-indicator');
  if (tab === 'live') { li.style.display=''; startLiveTimer(); }
  else { li.style.display='none'; stopLiveTimer(); }
  if (tab === 'dashboard') loadDashboard();
  if (tab === 'hotspots') loadHotspots();
  if (tab === 'revenue') { setDefaultMonth(); loadRevenue(); }
  if (tab === 'live') loadLive();
  if (tab === 'users') loadUsers();
  if (tab === 'security') loadSecurity();
}

// ── Dashboard ──
async function loadDashboard() {
  await Promise.all([loadStats(), loadHealth()]);
  setLastUpdate();
}

async function loadStats() {
  try {
    const r = await fetch('/admin/api/stats', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    renderDashKPIs(d);
    renderDashHotspots(d.hotspots || []);
    renderTrendChart(d.daily_trend || []);
  } catch(e) {
    document.getElementById('dash-kpis').innerHTML = '<div class="empty-state"><div class="empty-icon">&#9888;</div>載入失敗：' + e.message + '</div>';
  }
}

function renderDashKPIs(d) {
  const kpis = [
    { label:'今日訪客', value: fmt(d.today_visitors), icon:'&#128100;', cls:'primary', sub:'當日訪問' },
    { label:'總連線數', value: fmt(d.total_connections), icon:'&#128225;', cls:'success', sub:'累計紀錄' },
    { label:'活躍熱點', value: fmt(d.active_hotspots) + ' / ' + fmt(d.total_hotspots), icon:'&#128205;', cls:'warning', sub:'熱點狀態' },
    { label:'本月收入', value: 'PHP ' + fmt(d.monthly_revenue), icon:'&#128176;', cls:'primary', sub:'廣告收入' },
  ];
  document.getElementById('dash-kpis').innerHTML = kpis.map(k =>
    '<div class="kpi-card ' + k.cls + '">' +
    '<div class="kpi-icon">' + k.icon + '</div>' +
    '<div class="kpi-label">' + k.label + '</div>' +
    '<div class="kpi-value">' + k.value + '</div>' +
    '<div class="kpi-sub">' + k.sub + '</div></div>'
  ).join('');
}

function renderDashHotspots(hs) {
  const tbody = document.getElementById('dash-hotspot-body');
  if (!hs.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state">無資料</div></td></tr>'; return; }
  tbody.innerHTML = hs.map(h =>
    '<tr><td><strong>' + (h.name || h.id || '—') + '</strong></td>' +
    '<td>' + (h.location || '—') + '</td>' +
    '<td>' + fmt(h.today_visits) + '</td>' +
    '<td>' + fmt(h.online_users) + '</td>' +
    '<td><span class="badge ' + (h.is_active ? 'success' : 'danger') + '"><span class="dot ' + (h.is_active ? 'success' : 'danger') + '"></span>' + (h.is_active ? '正常' : '離線') + '</span></td></tr>'
  ).join('');
}

function renderTrendChart(data) {
  const ctx = document.getElementById('chart-trend');
  if (!ctx) return;
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  const labels = data.map(d => d.date || d.day || '').slice(-7);
  const values = data.map(d => d.count || d.visits || 0).slice(-7);
  trendChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label:'每日訪客', data: values, backgroundColor:'rgba(99,102,241,.7)', borderColor:'#6366f1', borderWidth:1, borderRadius:6 }]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:false } },
      scales:{ y:{ beginAtZero:true, ticks:{ maxTicksLimit:5 }, grid:{ color:'rgba(0,0,0,.05)' } }, x:{ grid:{ display:false } } }
    }
  });
}

async function loadHealth() {
  try {
    const r = await fetch('/health', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    renderHealth(d);
  } catch(e) {
    document.getElementById('health-grid').innerHTML = '<div class="empty-state">&#9888; 無法取得健康狀態</div>';
  }
}

function renderHealth(d) {
  const items = [
    { label:'DB', value: d.db || d.database || 'unknown' },
    { label:'Redis', value: d.redis || 'unknown' },
    { label:'版本', value: d.version || '—' },
    { label:'狀態', value: d.status || d.overall || 'ok' },
  ];
  const grid = document.getElementById('health-grid');
  grid.innerHTML = items.map(i => {
    const v = String(i.value).toLowerCase();
    const cls = v === 'ok' || v === 'healthy' || v === 'connected' ? 'ok' : v === 'warn' || v === 'degraded' ? 'warn' : 'ok';
    return '<div class="health-item ' + cls + '"><div class="h-label">' + i.label + '</div><div class="h-value">' + i.value + '</div></div>';
  }).join('');
}

// ── Hotspots ──
async function loadHotspots() {
  try {
    const r = await fetch('/admin/api/hotspots', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    allHotspots = d.hotspots || d || [];
    renderHotspotTable(allHotspots);
    populateHotspotFilter(allHotspots);
  } catch(e) {
    document.getElementById('hs-table-body').innerHTML = '<tr><td colspan="9"><div class="empty-state">&#9888; 載入失敗：' + e.message + '</div></td></tr>';
  }
}

function renderHotspotTable(hs) {
  const tbody = document.getElementById('hs-table-body');
  if (!hs.length) { tbody.innerHTML = '<tr><td colspan="9"><div class="empty-state"><div class="empty-icon">&#128205;</div>無熱點資料</div></td></tr>'; return; }
  tbody.innerHTML = hs.map(h =>
    '<tr>' +
    '<td>' + (h.id || '—') + '</td>' +
    '<td><strong>' + (h.name || '—') + '</strong></td>' +
    '<td>' + (h.location || '—') + '</td>' +
    '<td><code style="font-size:11px;background:var(--gray-100);padding:2px 6px;border-radius:4px">' + (h.ap_mac || '—') + '</code></td>' +
    '<td>' + (h.site_id || h.site || '—') + '</td>' +
    '<td style="font-size:11px;color:var(--gray-500)">' + (h.latitude ? h.latitude.toFixed(4) + ', ' + (h.longitude || 0).toFixed(4) : '—') + '</td>' +
    '<td>' + fmt(h.today_visits || 0) + '</td>' +
    '<td><span class="badge ' + (h.is_active !== false ? 'success' : 'danger') + '">' + (h.is_active !== false ? '啟用' : '停用') + '</span></td>' +
    '<td><button class="btn btn-outline btn-sm" onclick="toggleHotspot(' + h.id + ',' + (h.is_active !== false) + ')">' + (h.is_active !== false ? '停用' : '啟用') + '</button></td>' +
    '</tr>'
  ).join('');
}

function filterHotspots() {
  const q = document.getElementById('hs-search').value.toLowerCase();
  const filtered = allHotspots.filter(h => (h.name || '').toLowerCase().includes(q) || (h.location || '').toLowerCase().includes(q));
  renderHotspotTable(filtered);
}

async function toggleHotspot(id, currentActive) {
  try {
    const r = await fetch('/admin/api/hotspots/' + id, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ is_active: !currentActive })
    });
    if (!r.ok) throw new Error(r.status);
    toast((currentActive ? '已停用' : '已啟用') + ' 熱點 #' + id, 'success');
    loadHotspots();
  } catch(e) {
    toast('操作失敗：' + e.message, 'error');
  }
}

function openAddModal() { document.getElementById('add-modal').classList.add('show'); }
function closeModal() { document.getElementById('add-modal').classList.remove('show'); }

async function submitAddHotspot() {
  const name = document.getElementById('f-name').value.trim();
  const location = document.getElementById('f-location').value.trim();
  if (!name || !location) { toast('請填寫名稱與地點', 'error'); return; }
  const payload = {
    name, location,
    ap_mac: document.getElementById('f-mac').value.trim() || null,
    site_id: document.getElementById('f-site').value.trim() || null,
    latitude: parseFloat(document.getElementById('f-lat').value) || null,
    longitude: parseFloat(document.getElementById('f-lng').value) || null,
    notes: document.getElementById('f-note').value.trim() || null,
    is_active: true
  };
  try {
    const r = await fetch('/admin/api/hotspots', { method:'POST', headers, body:JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || r.status); }
    toast('熱點新增成功！', 'success');
    closeModal();
    loadHotspots();
    ['f-name','f-location','f-mac','f-site','f-lat','f-lng','f-note'].forEach(id => { document.getElementById(id).value = ''; });
  } catch(e) {
    toast('新增失敗：' + e.message, 'error');
  }
}

function populateHotspotFilter(hs) {
  const sel = document.getElementById('usr-hotspot-filter');
  const cur = sel.value;
  sel.innerHTML = '<option value="">所有熱點</option>' + hs.map(h => '<option value="' + h.id + '">' + (h.name || h.id) + '</option>').join('');
  sel.value = cur;
}

// ── Revenue ──
function setDefaultMonth() {
  const el = document.getElementById('rev-month');
  if (!el.value) {
    const now = new Date();
    el.value = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
  }
}

async function loadRevenue() {
  const month = document.getElementById('rev-month').value;
  if (!month) { toast('請選擇月份', 'error'); return; }
  try {
    const r = await fetch('/admin/api/revenue?month=' + month, { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    renderRevenueKPIs(d, month);
    renderRevenueTable(d.breakdown || d.hotspots || []);
    renderRevenueChart(d.breakdown || d.hotspots || []);
  } catch(e) {
    document.getElementById('rev-kpis').innerHTML = '<div class="empty-state">&#9888; 載入失敗：' + e.message + '</div>';
  }
}

function renderRevenueKPIs(d, month) {
  const kpis = [
    { label:'月份', value: month, icon:'&#128197;', cls:'' },
    { label:'總收入', value: 'PHP ' + fmt(d.total_revenue), icon:'&#128176;', cls:'success' },
    { label:'廣告展示', value: fmt(d.total_ad_views), icon:'&#128247;', cls:'primary' },
    { label:'總訪客', value: fmt(d.total_visitors), icon:'&#128100;', cls:'warning' },
  ];
  document.getElementById('rev-kpis').innerHTML = kpis.map(k =>
    '<div class="kpi-card ' + k.cls + '"><div class="kpi-icon">' + k.icon + '</div><div class="kpi-label">' + k.label + '</div><div class="kpi-value">' + k.value + '</div></div>'
  ).join('');
}

function renderRevenueTable(breakdown) {
  const tbody = document.getElementById('rev-table-body');
  if (!breakdown.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state">無資料</div></td></tr>'; return; }
  const total = breakdown.reduce((s, r) => s + (r.revenue || 0), 0);
  tbody.innerHTML = breakdown.map(r => {
    const pct = total > 0 ? ((r.revenue || 0) / total * 100).toFixed(1) : 0;
    return '<tr><td><strong>' + (r.hotspot_name || r.name || '—') + '</strong></td>' +
      '<td>' + (r.location || '—') + '</td>' +
      '<td>' + fmt(r.ad_views || r.views || 0) + '</td>' +
      '<td><strong>PHP ' + fmt(r.revenue || 0) + '</strong></td>' +
      '<td><div style="display:flex;align-items:center;gap:8px"><div style="background:var(--primary-light);border-radius:4px;height:8px;width:80px;overflow:hidden"><div style="background:var(--primary);height:100%;width:' + pct + '%"></div></div>' + pct + '%</div></td></tr>';
  }).join('');
}

function renderRevenueChart(breakdown) {
  const ctx = document.getElementById('chart-revenue');
  if (!ctx) return;
  if (revenueChart) { revenueChart.destroy(); revenueChart = null; }
  if (!breakdown.length) return;
  const labels = breakdown.map(r => r.hotspot_name || r.name || '?');
  const data = breakdown.map(r => r.revenue || 0);
  const colors = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899','#14b8a6'];
  revenueChart = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors.slice(0, data.length), borderWidth:2, borderColor:'#fff' }] },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ position:'bottom', labels:{ boxWidth:12, font:{ size:11 } } } }
    }
  });
}

// ── Live ──
function startLiveTimer() {
  stopLiveTimer();
  liveCountdown = 15;
  liveTimer = setInterval(() => {
    liveCountdown--;
    const el = document.getElementById('live-refresh-countdown');
    if (el) el.textContent = liveCountdown;
    if (liveCountdown <= 0) {
      liveCountdown = 15;
      loadLive();
    }
  }, 1000);
}

function stopLiveTimer() {
  if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
}

async function loadLive() {
  liveCountdown = 15;
  try {
    const r = await fetch('/admin/api/live', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const total = d.total_online || d.total || 0;
    document.getElementById('live-total').textContent = fmt(total);
    renderLiveTable(d.hotspots || []);
    setLastUpdate();
  } catch(e) {
    document.getElementById('live-total').textContent = '—';
    document.getElementById('live-table-body').innerHTML = '<tr><td colspan="6"><div class="empty-state">&#9888; 載入失敗：' + e.message + '</div></td></tr>';
  }
}

function renderLiveTable(hs) {
  const tbody = document.getElementById('live-table-body');
  if (!hs.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">無熱點在線</div></td></tr>'; return; }
  tbody.innerHTML = hs.map(h =>
    '<tr>' +
    '<td><strong>' + (h.name || '—') + '</strong></td>' +
    '<td>' + (h.location || '—') + '</td>' +
    '<td style="font-size:18px;font-weight:700;color:var(--primary)">' + fmt(h.online || h.online_users || 0) + '</td>' +
    '<td>' + fmt(h.today_visits || 0) + '</td>' +
    '<td>' + fmtDate(h.last_activity || h.last_seen) + '</td>' +
    '<td><span class="badge ' + (h.is_active !== false ? 'success' : 'danger') + '"><span class="dot ' + (h.is_active !== false ? 'success' : 'danger') + '"></span>' + (h.is_active !== false ? '在線' : '離線') + '</span></td>' +
    '</tr>'
  ).join('');
}

// ── Users ──
async function loadUsers() {
  usersPage = 0;
  try {
    const r = await fetch('/admin/api/stats', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    allUsers = d.recent_visits || d.visits || [];
    if (allHotspots.length === 0 && d.hotspots) {
      allHotspots = d.hotspots;
      populateHotspotFilter(allHotspots);
    }
    renderUsersTable();
  } catch(e) {
    try {
      const r2 = await fetch('/admin/api/hotspots', { headers: headersGet });
      const d2 = await r2.json();
      allHotspots = d2.hotspots || d2 || [];
      populateHotspotFilter(allHotspots);
    } catch(_) {}
    document.getElementById('usr-table-body').innerHTML = '<tr><td colspan="6"><div class="empty-state">&#9888; 載入失敗：' + e.message + '</div></td></tr>';
  }
}

function filterUsers() {
  usersPage = 0;
  renderUsersTable();
}

function renderUsersTable() {
  const q = document.getElementById('usr-search').value.toLowerCase();
  const hsFilter = document.getElementById('usr-hotspot-filter').value;
  let filtered = allUsers.filter(u => {
    const matchQ = !q || (u.mac || '').toLowerCase().includes(q) || (u.ip || '').toLowerCase().includes(q) || (u.hotspot_name || '').toLowerCase().includes(q);
    const matchHs = !hsFilter || String(u.hotspot_id) === hsFilter;
    return matchQ && matchHs;
  });
  const total = filtered.length;
  const paged = filtered.slice(usersPage * PAGE_SIZE, (usersPage + 1) * PAGE_SIZE);
  const tbody = document.getElementById('usr-table-body');
  if (!paged.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><div class="empty-icon">&#128100;</div>無訪問記錄</div></td></tr>'; }
  else {
    tbody.innerHTML = paged.map((u, i) =>
      '<tr>' +
      '<td>' + (usersPage * PAGE_SIZE + i + 1) + '</td>' +
      '<td><code style="font-size:12px;background:var(--gray-100);padding:2px 6px;border-radius:4px">' + (u.mac || u.mac_address || '—') + '</code></td>' +
      '<td>' + (u.hotspot_name || u.hotspot || '—') + '</td>' +
      '<td><code style="font-size:12px">' + (u.ip || u.ip_address || '—') + '</code></td>' +
      '<td>' + fmtDate(u.created_at || u.timestamp || u.visited_at) + '</td>' +
      '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + (u.user_agent || '') + '">' + truncate(u.user_agent, 35) + '</td>' +
      '</tr>'
    ).join('');
  }
  const pg = document.getElementById('usr-pagination');
  const totalPages = Math.ceil(total / PAGE_SIZE);
  let pgHtml = '<span style="color:var(--gray-500);font-size:12px;align-self:center">共 ' + total + ' 筆</span>';
  if (totalPages > 1) {
    pgHtml += '<button class="btn btn-outline btn-sm" onclick="setPage(' + (usersPage - 1) + ')" ' + (usersPage === 0 ? 'disabled' : '') + '>上一頁</button>';
    pgHtml += '<span style="font-size:13px;color:var(--gray-600)">' + (usersPage + 1) + ' / ' + totalPages + '</span>';
    pgHtml += '<button class="btn btn-outline btn-sm" onclick="setPage(' + (usersPage + 1) + ')" ' + (usersPage >= totalPages - 1 ? 'disabled' : '') + '>下一頁</button>';
  }
  pg.innerHTML = pgHtml;
}

function setPage(p) { usersPage = p; renderUsersTable(); }

// ── Security ──
async function loadSecurity() {
  recordAdminLogin();
  renderLoginLog();
  await Promise.all([loadSecurityStats(), loadSysInfo()]);
}

function recordAdminLogin() {
  const now = new Date().toISOString();
  let logs = JSON.parse(localStorage.getItem('admin_logins') || '[]');
  logs.unshift({ time: now, ua: navigator.userAgent.slice(0, 80) });
  if (logs.length > 20) logs = logs.slice(0, 20);
  localStorage.setItem('admin_logins', JSON.stringify(logs));
}

function renderLoginLog() {
  const logs = JSON.parse(localStorage.getItem('admin_logins') || '[]');
  const div = document.getElementById('sec-login-log');
  if (!logs.length) { div.innerHTML = '<div class="empty-state">無記錄</div>'; return; }
  div.innerHTML = logs.slice(0, 10).map((l, i) =>
    '<div class="ip-stat-item">' +
    '<div><strong>' + fmtDate(l.time) + '</strong>' + (i === 0 ? ' <span class="badge success">本次</span>' : '') +
    '<div style="font-size:11px;color:var(--gray-400);margin-top:2px">' + truncate(l.ua, 50) + '</div></div>' +
    '</div>'
  ).join('');
}

async function loadSecurityStats() {
  try {
    const r = await fetch('/admin/api/stats', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const today = d.today_visitors || 0;
    const total = d.total_connections || 0;
    const hs = d.hotspots || [];
    document.getElementById('sec-stats').innerHTML =
      '<div class="ip-stat-item"><span>今日訪客</span><span class="badge info">' + fmt(today) + '</span></div>' +
      '<div class="ip-stat-item"><span>累計連線</span><span class="badge gray">' + fmt(total) + '</span></div>' +
      '<div class="ip-stat-item"><span>活躍熱點</span><span class="badge success">' + fmt(d.active_hotspots || hs.filter(h => h.is_active).length) + '</span></div>' +
      '<div class="ip-stat-item"><span>離線熱點</span><span class="badge ' + (d.inactive_hotspots > 0 ? 'danger' : 'gray') + '">' + fmt(d.inactive_hotspots || hs.filter(h => !h.is_active).length) + '</span></div>';
    const visits = d.recent_visits || [];
    const macCount = {};
    visits.forEach(v => { const m = v.mac || v.mac_address; if (m) macCount[m] = (macCount[m] || 0) + 1; });
    const anomaly = Object.entries(macCount).filter(([,c]) => c >= 5).sort((a,b) => b[1]-a[1]);
    const ipCount = {};
    visits.forEach(v => { const ip = v.ip || v.ip_address; if (ip) ipCount[ip] = (ipCount[ip] || 0) + 1; });
    const topIPs = Object.entries(ipCount).sort((a,b) => b[1]-a[1]).slice(0, 8);
    if (anomaly.length) {
      document.getElementById('sec-anomaly').innerHTML = anomaly.map(([mac, c]) =>
        '<div class="ip-stat-item"><code style="font-size:12px">' + mac + '</code><span class="badge danger">' + c + ' 次</span></div>'
      ).join('');
    }
    if (topIPs.length) {
      document.getElementById('sec-ip-stats').innerHTML = topIPs.map(([ip, c]) =>
        '<div class="ip-stat-item"><code style="font-size:12px">' + ip + '</code><span class="badge info">' + c + ' 次</span></div>'
      ).join('');
    } else {
      document.getElementById('sec-ip-stats').innerHTML = '<div class="empty-state">無 IP 統計資料</div>';
    }
  } catch(e) {
    document.getElementById('sec-stats').innerHTML = '<div class="empty-state">&#9888; ' + e.message + '</div>';
  }
}

async function loadSysInfo() {
  try {
    const r = await fetch('/health', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    document.getElementById('sec-sysinfo').innerHTML =
      Object.entries(d).map(([k, v]) =>
        '<div class="ip-stat-item"><span style="font-weight:500">' + k + '</span>' +
        '<span class="badge ' + (String(v).toLowerCase() === 'ok' || String(v).toLowerCase() === 'healthy' ? 'success' : 'gray') + '">' + v + '</span></div>'
      ).join('') +
      '<div class="ip-stat-item"><span>當前時間</span><span style="font-size:12px;color:var(--gray-500)">' + new Date().toLocaleString('zh-TW') + '</span></div>';
  } catch(e) {
    document.getElementById('sec-sysinfo').innerHTML = '<div class="empty-state">無法取得系統資訊</div>';
  }
}

// ── Init ──
(function init() {
  loadDashboard();
  setDefaultMonth();
})();
</script>
</body>
</html>
"""


import base64
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import AccessGrant, AdView, DirectAdvertiser, Hotspot, Visit, get_db
from models.schemas import (
    DirectAdvertiserCreate,
    DirectAdvertiserResponse,
    HotspotCreate,
    HotspotResponse,
    RevenueResponse,
    StatsResponse,
    HotspotStats,
)
from services.omada import OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


def verify_basic_auth(request: Request) -> None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    if not (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>WiFi Portal Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f0f13;color:#e0e0e8;min-height:100vh}
a{color:inherit;text-decoration:none}
.sidebar{position:fixed;left:0;top:0;width:220px;height:100vh;background:#1a1a24;border-right:1px solid #2a2a38;padding:20px 0;z-index:10}
.logo{padding:0 20px 20px;font-size:16px;font-weight:700;color:#fff;border-bottom:1px solid #2a2a38;margin-bottom:12px}
.logo span{color:#00e676}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 20px;cursor:pointer;font-size:13px;color:#888;transition:all .15s;border-left:3px solid transparent}
.nav-item:hover{color:#fff;background:rgba(255,255,255,.04)}
.nav-item.active{color:#00e676;background:rgba(0,230,118,.06);border-left-color:#00e676}
.main{margin-left:220px;padding:24px;min-height:100vh}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.page-title{font-size:20px;font-weight:700}
.badge-live{background:rgba(0,230,118,.15);color:#00e676;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid rgba(0,230,118,.3)}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:24px}
.card{background:#1a1a24;border:1px solid #2a2a38;border-radius:12px;padding:20px}
.card-sm{background:#1a1a24;border:1px solid #2a2a38;border-radius:12px;padding:16px}
.stat-label{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.stat-val{font-size:28px;font-weight:700;color:#fff;letter-spacing:-.02em}
.stat-sub{font-size:12px;color:#555;margin-top:4px}
.stat-up{color:#00e676;font-size:11px}
.section-title{font-size:14px;font-weight:600;color:#ccc;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center}
table{width:100%;border-collapse:collapse}
th{font-size:11px;color:#555;padding:8px 12px;border-bottom:1px solid #2a2a38;text-align:left;text-transform:uppercase;letter-spacing:.06em}
td{padding:12px;border-bottom:1px solid #1e1e2a;font-size:13px;color:#bbb}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02);color:#ddd}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.pill.on{background:rgba(0,230,118,.12);color:#00e676}
.pill.off{background:rgba(255,80,80,.1);color:#ff5555}
.pill.warn{background:rgba(255,180,0,.1);color:#ffb400}
.btn{padding:7px 16px;border-radius:8px;border:none;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}
.btn-green{background:#00e676;color:#000}
.btn-green:hover{background:#00c853}
.btn-ghost{background:transparent;color:#666;border:1px solid #2a2a38}
.btn-ghost:hover{color:#ccc;border-color:#444}
.btn-red{background:rgba(255,80,80,.15);color:#ff5555;border:1px solid rgba(255,80,80,.2)}
input,select{background:#13131a;border:1px solid #2a2a38;color:#e0e0e8;padding:8px 12px;border-radius:8px;font-size:13px;outline:none;width:100%}
input:focus,select:focus{border-color:#00e676}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
.form-label{font-size:11px;color:#555;margin-bottom:4px;display:block}
.divider{height:1px;background:#2a2a38;margin:20px 0}
.tab{display:none}.tab.active{display:block}
.pulse{width:8px;height:8px;border-radius:50%;background:#00e676;display:inline-block;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,230,118,.4)}50%{opacity:.7;box-shadow:0 0 0 6px rgba(0,230,118,0)}}
.revenue-bar{height:6px;background:#2a2a38;border-radius:3px;overflow:hidden;margin-top:6px}
.revenue-fill{height:100%;background:linear-gradient(90deg,#00e676,#00b0ff);border-radius:3px;transition:width .5s ease}
.empty{text-align:center;padding:40px;color:#444;font-size:13px}
.config-key{font-family:monospace;font-size:12px;color:#888;background:#13131a;padding:4px 8px;border-radius:4px;margin-top:4px;display:block;word-break:break-all}
</style>
</head>
<body>
<div class="sidebar">
  <div class="logo">WiFi<span>Portal</span></div>
  <div class="nav-item active" onclick="showTab('overview')">📊 總覽</div>
  <div class="nav-item" onclick="showTab('hotspots')">📡 熱點管理</div>
  <div class="nav-item" onclick="showTab('revenue')">💰 收入分析</div>
  <div class="nav-item" onclick="showTab('live')">🔴 即時監控</div>
  <div class="nav-item" onclick="showTab('config')">⚙️ 系統設定</div>
</div>

<div class="main">
<div class="topbar">
  <div>
    <div class="page-title" id="pageTitle">總覽 Dashboard</div>
    <div style="font-size:12px;color:#444;margin-top:2px" id="pageDesc">最後更新：<span id="lastUpdate">-</span></div>
  </div>
  <span class="badge-live"><span class="pulse"></span> &nbsp;LIVE</span>
</div>

<!-- 總覽 -->
<div class="tab active" id="tab-overview">
  <div class="grid4">
    <div class="card"><div class="stat-label">今日連線</div><div class="stat-val" id="ov-visits">-</div><div class="stat-sub">累計 <span id="ov-total-visits">-</span></div></div>
    <div class="card"><div class="stat-label">今日廣告</div><div class="stat-val" id="ov-ads">-</div><div class="stat-sub">累計 <span id="ov-total-ads">-</span></div></div>
    <div class="card"><div class="stat-label">即時用戶</div><div class="stat-val" id="ov-live" style="color:#00e676">-</div><div class="stat-sub">正在上網中</div></div>
    <div class="card"><div class="stat-label">本月收入</div><div class="stat-val" id="ov-rev">-</div><div class="stat-sub">USD 估算</div></div>
  </div>
  <div class="grid2">
    <div class="card">
      <div class="section-title">熱點狀態</div>
      <table><thead><tr><th>熱點</th><th>即時用戶</th><th>今日</th><th>狀態</th></tr></thead>
      <tbody id="ov-hotspot-table"><tr><td colspan="4" class="empty">載入中...</td></tr></tbody></table>
    </div>
    <div class="card">
      <div class="section-title">系統健康</div>
      <div style="display:flex;flex-direction:column;gap:12px" id="ov-health">
        <div style="color:#444;text-align:center;padding:20px">載入中...</div>
      </div>
    </div>
  </div>
</div>

<!-- 熱點管理 -->
<div class="tab" id="tab-hotspots">
  <div class="card" style="margin-bottom:16px">
    <div class="section-title">新增熱點 <button class="btn btn-ghost" onclick="toggleAddForm()">+ 新增</button></div>
    <div id="addForm" style="display:none">
      <div class="form-row"><div><label class="form-label">熱點名稱 *</label><input id="hN" placeholder="台北咖啡廳"/></div><div><label class="form-label">地點描述 *</label><input id="hL" placeholder="台北市大安區"/></div></div>
      <div class="form-row"><div><label class="form-label">AP MAC 地址 *</label><input id="hM" placeholder="aa:bb:cc:dd:ee:ff"/></div><div><label class="form-label">Omada Site 名稱 *</label><input id="hS" placeholder="site-default"/></div></div>
      <div class="form-row"><div><label class="form-label">緯度（選填）</label><input id="hLat" placeholder="25.0330"/></div><div><label class="form-label">經度（選填）</label><input id="hLng" placeholder="121.5654"/></div></div>
      <button class="btn btn-green" onclick="addHotspot()">確認新增</button>
      <button class="btn btn-ghost" onclick="toggleAddForm()" style="margin-left:8px">取消</button>
    </div>
  </div>
  <div class="card">
    <div class="section-title">所有熱點</div>
    <table><thead><tr><th>名稱</th><th>地點</th><th>AP MAC</th><th>Site</th><th>今日連線</th><th>今日廣告</th><th>狀態</th></tr></thead>
    <tbody id="hotspot-table"><tr><td colspan="7" class="empty">載入中...</td></tr></tbody></table>
  </div>
</div>

<!-- 收入分析 -->
<div class="tab" id="tab-revenue">
  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;align-items:center;gap:12px">
      <label class="form-label" style="white-space:nowrap;margin:0">選擇月份：</label>
      <input type="month" id="revMonth" style="width:160px" onchange="loadRevenue()"/>
    </div>
  </div>
  <div class="grid4" style="margin-bottom:16px">
    <div class="card"><div class="stat-label">Adcash 收入</div><div class="stat-val" id="rev-adcash">-</div><div class="stat-sub">USD</div></div>
    <div class="card"><div class="stat-label">直接廣告商</div><div class="stat-val" id="rev-direct">-</div><div class="stat-sub">PHP</div></div>
    <div class="card"><div class="stat-label">廣告瀏覽</div><div class="stat-val" id="rev-views">-</div><div class="stat-sub">次</div></div>
    <div class="card"><div class="stat-label">每千次收入</div><div class="stat-val" id="rev-cpm">-</div><div class="stat-sub">USD CPM</div></div>
  </div>
  <div class="card">
    <div class="section-title">各熱點收入分解</div>
    <table><thead><tr><th>熱點</th><th>廣告瀏覽</th><th>收入 USD</th><th>佔比</th></tr></thead>
    <tbody id="rev-table"><tr><td colspan="4" class="empty">選擇月份後載入</td></tr></tbody></table>
  </div>
</div>

<!-- 即時監控 -->
<div class="tab" id="tab-live">
  <div class="grid4" style="margin-bottom:16px">
    <div class="card"><div class="stat-label">即時用戶</div><div class="stat-val" id="live-total" style="color:#00e676">-</div><div class="stat-sub">正在上網</div></div>
    <div class="card"><div class="stat-label">OC200 連接</div><div class="stat-val" id="live-omada" style="font-size:20px">-</div><div class="stat-sub">設備數</div></div>
  </div>
  <div class="card">
    <div class="section-title">各熱點即時狀況 <button class="btn btn-ghost" onclick="loadLive()" style="font-size:11px">🔄 刷新</button></div>
    <table><thead><tr><th>熱點名稱</th><th>即時用戶</th><th>狀態</th></tr></thead>
    <tbody id="live-table"><tr><td colspan="3" class="empty">載入中...</td></tr></tbody></table>
  </div>
</div>

<!-- 系統設定 -->
<div class="tab" id="tab-config">
  <div class="grid2">
    <div class="card">
      <div class="section-title">Portal 設定</div>
      <div style="display:flex;flex-direction:column;gap:12px">
        <div><div class="form-label">Portal URL（填入 OC200）</div><code class="config-key" id="cfg-url">https://ph-wifi-portal.zeabur.app/portal</code></div>
        <div><div class="form-label">廣告觀看時間（秒）</div><code class="config-key">30 秒</code></div>
        <div><div class="form-label">上網時長</div><code class="config-key">3600 秒（1 小時）</code></div>
      </div>
    </div>
    <div class="card">
      <div class="section-title">OC200 設定指南</div>
      <div style="font-size:12px;color:#888;line-height:1.8">
        <p>1. 登入 Omada 控制台</p>
        <p>2. 設定 → 認證 → Portal</p>
        <p>3. 認證類型選「External Web Portal」</p>
        <p>4. Portal URL 填入上方網址</p>
        <p>5. 儲存並套用到目標 SSID</p>
      </div>
    </div>
    <div class="card">
      <div class="section-title">系統資訊</div>
      <table><tbody id="sys-info">
        <tr><td>版本</td><td style="color:#00e676">v1.0.0</td></tr>
        <tr><td>環境</td><td id="si-env">-</td></tr>
        <tr><td>資料庫</td><td id="si-db">-</td></tr>
        <tr><td>Redis</td><td id="si-redis">-</td></tr>
        <tr><td>OC200</td><td id="si-omada">-</td></tr>
      </tbody></table>
    </div>
  </div>
</div>

</div><!-- /main -->

<script>
const PAGES={overview:'總覽 Dashboard',hotspots:'熱點管理',revenue:'收入分析',live:'即時監控',config:'系統設定'};
function showTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  event.currentTarget.classList.add('active');
  document.getElementById('pageTitle').textContent=PAGES[name];
  if(name==='overview')loadOverview();
  if(name==='hotspots')loadHotspots();
  if(name==='revenue'){const d=new Date();document.getElementById('revMonth').value=d.getFullYear()+'-'+(String(d.getMonth()+1).padStart(2,'0'));loadRevenue();}
  if(name==='live')loadLive();
  if(name==='config')loadConfig();
}
function toggleAddForm(){const f=document.getElementById('addForm');f.style.display=f.style.display==='none'?'block':'none';}

async function loadOverview(){
  try{
    const [s,l]=await Promise.all([fetch('/admin/api/stats').then(r=>r.json()),fetch('/admin/api/live').then(r=>r.json())]);
    document.getElementById('ov-visits').textContent=s.today_visits??0;
    document.getElementById('ov-total-visits').textContent=(s.total_visits??0).toLocaleString();
    document.getElementById('ov-ads').textContent=s.today_ad_views??0;
    document.getElementById('ov-total-ads').textContent=(s.total_ad_views??0).toLocaleString();
    document.getElementById('ov-live').textContent=l.total_active_users??0;
    document.getElementById('ov-rev').textContent='$'+(parseFloat(s.total_revenue_usd??0)).toFixed(2);
    document.getElementById('lastUpdate').textContent=new Date().toLocaleTimeString();
    // hotspot table
    const hs=s.hotspots??[];
    const liveMap={};(l.hotspots??[]).forEach(h=>{liveMap[h.hotspot_id]=h.active_users;});
    document.getElementById('ov-hotspot-table').innerHTML=hs.length?hs.map(h=>`<tr><td><b>${h.name}</b></td><td style="color:#00e676">${liveMap[h.id]??0}</td><td>${h.today_visits??0}</td><td><span class="pill ${h.is_active?'on':'off'}">${h.is_active?'● 運行':'● 停用'}</span></td></tr>`).join(''):`<tr><td colspan="4" class="empty">尚無熱點</td></tr>`;
    // health
    const items=[['資料庫',s.database_status],['Redis',s.redis_status],['OC200',s.omada_status??(s.omada_configured?'連接中':'未設定')]];
    document.getElementById('ov-health').innerHTML=items.map(([k,v])=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #2a2a38"><span style="color:#888;font-size:13px">${k}</span><span class="pill ${v==='ok'?'on':v==='未設定'?'warn':'off'}">${v==='ok'?'● 正常':v==='未設定'?'● 未設定':'● 異常'}</span></div>`).join('');
  }catch(e){console.error(e);}
}

async function loadHotspots(){
  const hs=await fetch('/admin/api/hotspots').then(r=>r.json()).catch(()=>[]);
  document.getElementById('hotspot-table').innerHTML=hs.length?hs.map(h=>`<tr><td><b>${h.name}</b></td><td>${h.location}</td><td style="font-family:monospace;font-size:11px;color:#888">${h.ap_mac}</td><td style="font-size:11px;color:#888">${h.site_name}</td><td>${h.today_visits??0}</td><td>${h.today_ad_views??0}</td><td><span class="pill ${h.is_active?'on':'off'}">${h.is_active?'● 運行中':'● 停用'}</span></td></tr>`).join(''):`<tr><td colspan="7" class="empty">尚無熱點，點「新增」開始</td></tr>`;
}

async function addHotspot(){
  const d={name:document.getElementById('hN').value,location:document.getElementById('hL').value,ap_mac:document.getElementById('hM').value,site_name:document.getElementById('hS').value};
  const lat=document.getElementById('hLat').value,lng=document.getElementById('hLng').value;
  if(lat)d.latitude=parseFloat(lat);if(lng)d.longitude=parseFloat(lng);
  if(!d.name||!d.ap_mac||!d.site_name){alert('名稱、AP MAC、Site 為必填');return;}
  const r=await fetch('/admin/api/hotspots',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  if(r.ok){toggleAddForm();loadHotspots();}else{const e=await r.json();alert('失敗: '+(e.detail||'unknown'));}
}

async function loadRevenue(){
  const m=document.getElementById('revMonth').value;if(!m)return;
  const d=await fetch('/admin/api/revenue?month='+m).then(r=>r.json()).catch(()=>null);
  if(!d)return;
  document.getElementById('rev-adcash').textContent='$'+parseFloat(d.adcash_revenue_usd??0).toFixed(2);
  document.getElementById('rev-direct').textContent='₱'+parseFloat(d.direct_revenue_php??0).toFixed(0);
  document.getElementById('rev-views').textContent=(d.total_ad_views??0).toLocaleString();
  const cpm=d.total_ad_views>0?(parseFloat(d.adcash_revenue_usd??0)/d.total_ad_views*1000).toFixed(3):'0';
  document.getElementById('rev-cpm').textContent='$'+cpm;
  const total=parseFloat(d.adcash_revenue_usd??0)||0.001;
  document.getElementById('rev-table').innerHTML=(d.breakdown_by_hotspot??[]).map(b=>{
    const pct=total>0?(parseFloat(b.revenue_usd)/total*100).toFixed(1):0;
    return `<tr><td><b>${b.hotspot_name}</b></td><td>${b.ad_views}</td><td>$${parseFloat(b.revenue_usd).toFixed(2)}</td><td><div style="min-width:80px">${pct}%<div class="revenue-bar"><div class="revenue-fill" style="width:${pct}%"></div></div></div></td></tr>`;
  }).join('')||`<tr><td colspan="4" class="empty">本月尚無收入資料</td></tr>`;
}

async function loadLive(){
  const d=await fetch('/admin/api/live').then(r=>r.json()).catch(()=>null);
  if(!d)return;
  document.getElementById('live-total').textContent=d.total_active_users??0;
  document.getElementById('live-omada').textContent=d.omada_clients??'N/A';
  document.getElementById('live-table').innerHTML=(d.hotspots??[]).map(h=>`<tr><td><b>${h.hotspot_name}</b></td><td style="color:#00e676;font-size:18px;font-weight:700">${h.active_users}</td><td><span class="pill ${h.active_users>0?'on':'warn'}">${h.active_users>0?'● 有用戶':'● 空閒'}</span></td></tr>`).join('')||`<tr><td colspan="3" class="empty">無資料</td></tr>`;
}

async function loadConfig(){
  const d=await fetch('/admin/api/stats').then(r=>r.json()).catch(()=>null);
  if(!d)return;
  document.getElementById('cfg-url').textContent=window.location.origin+'/portal';
  document.getElementById('si-env').textContent=d.environment||'production';
  document.getElementById('si-db').innerHTML=`<span class="${d.database_status==='ok'?'pill on':'pill off'}">${d.database_status==='ok'?'● 正常':'● 異常'}</span>`;
  document.getElementById('si-redis').innerHTML=`<span class="${d.redis_status==='ok'?'pill on':'pill off'}">${d.redis_status==='ok'?'● 正常':'● 異常'}</span>`;
  document.getElementById('si-omada').innerHTML=`<span class="pill warn">● 待設定</span>`;
}

loadOverview();
setInterval(()=>{
  const active=document.querySelector('.nav-item.active');
  if(active&&active.textContent.includes('總覽'))loadOverview();
  if(active&&active.textContent.includes('即時'))loadLive();
},15000);
</script>
</body></html>"""

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    verify_basic_auth(request)
    return HTMLResponse(content=DASHBOARD_HTML, status_code=200)


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StatsResponse:
    verify_basic_auth(request)
    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    visits_result = await db.execute(select(func.count(Visit.id)).where(Visit.visited_at >= today_start))
    total_visits: int = visits_result.scalar_one() or 0

    adviews_result = await db.execute(select(func.count(AdView.id)).where(AdView.viewed_at >= today_start))
    total_ad_views: int = adviews_result.scalar_one() or 0

    revenue_result = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.viewed_at >= today_start))
    total_revenue_usd: Decimal = revenue_result.scalar_one() or Decimal("0.0000")

    grants_result = await db.execute(select(func.count(AccessGrant.id)).where(AccessGrant.granted_at >= today_start))
    total_access_grants: int = grants_result.scalar_one() or 0

    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))
    hotspots = hotspots_result.scalars().all()

    redis_svc = RedisService(redis)
    hotspot_stats: list[HotspotStats] = []
    active_users_total = 0

    for hotspot in hotspots:
        hv = await db.execute(select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot.id, Visit.visited_at >= today_start))
        hav = await db.execute(select(func.count(AdView.id)).where(AdView.hotspot_id == hotspot.id, AdView.viewed_at >= today_start))
        hr = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.hotspot_id == hotspot.id, AdView.viewed_at >= today_start))
        active = await redis_svc.get_active_users_count(hotspot.id)
        active_users_total += active
        hotspot_stats.append(HotspotStats(
            hotspot_id=hotspot.id,
            hotspot_name=hotspot.name,
            visits_today=hv.scalar_one() or 0,
            ad_views_today=hav.scalar_one() or 0,
            revenue_today_usd=hr.scalar_one() or Decimal("0.0000"),
            active_users=active,
        ))

    return StatsResponse(
        date=today_start.strftime("%Y-%m-%d"),
        total_visits=total_visits,
        total_ad_views=total_ad_views,
        total_revenue_usd=total_revenue_usd,
        total_access_grants=total_access_grants,
        active_users_total=active_users_total,
        hotspots=hotspot_stats,
    )


@router.get("/api/hotspots", response_model=list[HotspotResponse])
async def list_hotspots(request: Request, db: AsyncSession = Depends(get_db)) -> list[HotspotResponse]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot))
    return [HotspotResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/api/hotspots", response_model=HotspotResponse, status_code=201)
async def create_hotspot(request: Request, body: HotspotCreate, db: AsyncSession = Depends(get_db)) -> HotspotResponse:
    verify_basic_auth(request)
    existing = await db.execute(select(Hotspot).where((Hotspot.name == body.name) | (Hotspot.ap_mac == body.ap_mac)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotspot with this name or AP MAC already exists")
    now = datetime.now(tz=timezone.utc)
    hotspot = Hotspot(name=body.name, location=body.location, ap_mac=body.ap_mac, site_name=body.site_name,
                      latitude=body.latitude, longitude=body.longitude, is_active=body.is_active, created_at=now, updated_at=now)
    db.add(hotspot)
    await db.flush()
    await db.refresh(hotspot)
    await db.commit()
    logger.info("hotspot_created", hotspot_id=hotspot.id)
    return HotspotResponse.model_validate(hotspot)


@router.get("/api/revenue", response_model=RevenueResponse)
async def get_revenue(
    request: Request,
    month: str = Query(default="", description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
) -> RevenueResponse:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    period = month if month else now.strftime("%Y-%m")
    try:
        year_s, month_s = period.split("-")
        period_start = datetime(int(year_s), int(month_s), 1, tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    if period_start.month == 12:
        period_end = datetime(period_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        period_end = datetime(period_start.year, period_start.month + 1, 1, tzinfo=timezone.utc)

    adcash_r = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end, AdView.ad_network == "adcash"))
    direct_r = await db.execute(select(func.sum(DirectAdvertiser.monthly_fee_php)).where(DirectAdvertiser.is_active == True, DirectAdvertiser.starts_at < period_end))
    total_v = await db.execute(select(func.count(AdView.id)).where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end))

    hotspots_result = await db.execute(select(Hotspot))
    breakdown: list[dict[str, Any]] = []
    for h in hotspots_result.scalars().all():
        hr = await db.execute(select(func.sum(AdView.estimated_revenue_usd)).where(AdView.hotspot_id == h.id, AdView.viewed_at >= period_start, AdView.viewed_at < period_end))
        hv = await db.execute(select(func.count(AdView.id)).where(AdView.hotspot_id == h.id, AdView.viewed_at >= period_start, AdView.viewed_at < period_end))
        breakdown.append({"hotspot_id": h.id, "hotspot_name": h.name, "revenue_usd": str(hr.scalar_one() or Decimal("0.0000")), "ad_views": hv.scalar_one() or 0})

    return RevenueResponse(
        period=period,
        adcash_revenue_usd=adcash_r.scalar_one() or Decimal("0.0000"),
        direct_revenue_php=direct_r.scalar_one() or Decimal("0.00"),
        total_ad_views=total_v.scalar_one() or 0,
        breakdown_by_hotspot=breakdown,
    )


@router.get("/api/live")
async def get_live_users(request: Request, redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    verify_basic_auth(request)
    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))
    hotspots = hotspots_result.scalars().all()
    redis_svc = RedisService(redis)
    live_data: list[dict[str, Any]] = []
    total = 0
    for hotspot in hotspots:
        count = await redis_svc.get_active_users_count(hotspot.id)
        total += count
        live_data.append({"hotspot_id": hotspot.id, "hotspot_name": hotspot.name, "active_users": count})
    omada_data: list[dict[str, Any]] = []
    try:
        omada = get_omada_client()
        for hotspot in hotspots:
            clients = await omada.get_online_clients(hotspot.site_name)
            omada_data.extend(clients)
    except (OmadaError, RuntimeError):
        pass
    return {"total_active_users": total, "hotspots": live_data, "omada_clients": len(omada_data), "message": f"{total} active user(s) across {len(hotspots)} hotspot(s)"}


@router.get("/api/visits")
async def list_visits(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    hotspot_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    verify_basic_auth(request)
    q = select(Visit, Hotspot.name.label("hotspot_name")).join(
        Hotspot, Visit.hotspot_id == Hotspot.id, isouter=True
    ).order_by(Visit.visited_at.desc()).limit(limit).offset(offset)
    if hotspot_id:
        q = q.where(Visit.hotspot_id == hotspot_id)
    result = await db.execute(q)
    rows = result.all()
    total_q = select(func.count(Visit.id))
    if hotspot_id:
        total_q = total_q.where(Visit.hotspot_id == hotspot_id)
    total = (await db.execute(total_q)).scalar_one()
    return {
        "total": total,
        "items": [
            {
                "id": row.Visit.id,
                "client_mac": row.Visit.client_mac,
                "hotspot_name": row.hotspot_name or "Unknown",
                "ip_address": row.Visit.ip_address,
                "user_agent": row.Visit.user_agent,
                "visited_at": row.Visit.visited_at.isoformat() if row.Visit.visited_at else None,
            }
            for row in rows
        ],
    }


@router.get("/api/security")
async def security_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    verify_basic_auth(request)
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=1)
    # 近 1 小時請求量
    recent_visits = await db.execute(
        select(func.count(Visit.id)).where(Visit.visited_at >= window_start)
    )
    # 高頻 MAC（1小時內超過 5 次）
    suspicious = await db.execute(
        select(Visit.client_mac, func.count(Visit.id).label("cnt"))
        .where(Visit.visited_at >= window_start)
        .group_by(Visit.client_mac)
        .having(func.count(Visit.id) > 5)
        .order_by(func.count(Visit.id).desc())
        .limit(20)
    )
    # 今日總量
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_visits = await db.execute(
        select(func.count(Visit.id)).where(Visit.visited_at >= today_start)
    )
    today_ads = await db.execute(
        select(func.count(AdView.id)).where(AdView.viewed_at >= today_start)
    )
    return {
        "today_requests": today_visits.scalar_one() or 0,
        "today_ad_views": today_ads.scalar_one() or 0,
        "last_hour_requests": recent_visits.scalar_one() or 0,
        "suspicious_macs": [
            {"mac": row.client_mac, "count": row.cnt}
            for row in suspicious.all()
        ],
        "rate_limit_active": True,
        "auth_method": "Basic Auth (bcrypt recommended for production)",
    }
