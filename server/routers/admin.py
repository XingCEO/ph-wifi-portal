from __future__ import annotations

import base64
import csv
import io
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.database import (
    AccessGrant, AdView, AdminAuditLog, BlockedDevice,
    DirectAdvertiser, Hotspot, Visit, get_db,
)
from models.schemas import (
    AuditLogResponse,
    BlockedDeviceCreate,
    BlockedDeviceResponse,
    DirectAdvertiserCreate,
    DirectAdvertiserResponse,
    DirectAdvertiserUpdate,
    HotspotCreate,
    HotspotResponse,
    HotspotUpdate,
    RevenueResponse,
    StatsResponse,
    HotspotStats,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from services.omada import OmadaError, get_omada_client
from services.redis_service import RedisService, get_redis

router = APIRouter(prefix="/admin")
logger = structlog.get_logger(__name__)


def verify_basic_auth(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        logger.warning("admin_auth_missing", ip=client_ip, path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        logger.warning("admin_auth_decode_failed", ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )
    if not (
        secrets.compare_digest(username, settings.admin_username)
        and secrets.compare_digest(password, settings.admin_password)
    ):
        logger.warning("admin_auth_failed", ip=client_ip, username=username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm=Admin Panel"},
        )


def _extract_username(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, _, _ = decoded.partition(":")
            return username
        except Exception:
            pass
    return "unknown"


async def record_audit(
    db: AsyncSession,
    request: Request,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    log_entry = AdminAuditLog(
        admin_user=_extract_username(request),
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.client.host if request.client else None,
    )
    db.add(log_entry)
    try:
        await db.flush()
    except Exception:
        pass


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
    <button class="nav-item" onclick="switchTab('advertisers',this)" data-tab="advertisers">
      <span class="icon">&#128230;</span>廣告主管理
    </button>
    <button class="nav-item" onclick="switchTab('devices',this)" data-tab="devices">
      <span class="icon">&#128267;</span>設備管理
    </button>
    <button class="nav-item" onclick="switchTab('sessions',this)" data-tab="sessions">
      <span class="icon">&#128268;</span>連線管理
    </button>
    <button class="nav-item" onclick="switchTab('settings',this)" data-tab="settings">
      <span class="icon">&#9881;</span>系統設定
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
        <span style="color:var(--gray-300)">|</span>
        <label class="form-label" style="margin:0">日期範圍：</label>
        <input type="date" class="form-control" id="rev-start" style="width:150px">
        <span>~</span>
        <input type="date" class="form-control" id="rev-end" style="width:150px">
        <button class="btn btn-outline" onclick="loadRevenueDaily()">每日查詢</button>
        <button class="btn btn-outline" onclick="window.location.href='/admin/api/export/revenue'">匯出 CSV</button>
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
      <div class="card" id="rev-daily-section" style="margin-top:16px;display:none">
        <div class="card-title">每日收入趨勢</div>
        <div class="kpi-grid" id="rev-daily-kpis" style="margin-bottom:12px"></div>
        <div class="chart-container"><canvas id="chart-revenue-daily"></canvas></div>
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
          <button class="btn btn-outline" onclick="window.location.href='/admin/api/export/visits'">匯出 CSV</button>
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
              <h3>&#128221; 管理操作記錄</h3>
              <div id="sec-audit-log">載入中...</div>
            </div>
            <div class="sec-section" style="margin-top:16px">
              <h3>&#128295; 系統資訊</h3>
              <div id="sec-sysinfo">
                <div class="loading-state"><span class="spinner"></span></div>
              </div>
            </div>
            <div class="sec-section" style="margin-top:16px">
              <div class="ip-stat-item">
                <span>封鎖裝置數</span>
                <span class="badge danger" id="sec-blocked-count">—</span>
              </div>
              <button class="btn btn-outline btn-sm" style="margin-top:8px" onclick="switchTab('devices',document.querySelector('[data-tab=devices]'))">管理封鎖裝置 &rarr;</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tab: Advertisers ── -->
    <div id="tab-advertisers" class="tab-pane">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px">
        <div class="search-wrap">
          <span class="search-icon">&#128269;</span>
          <input class="form-control" id="adv-search" placeholder="搜尋廣告主..." oninput="filterAdvertisers()" style="padding-left:36px">
        </div>
        <button class="btn btn-primary" onclick="openAdvModal()">+ 新增廣告主</button>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>名稱</th><th>聯絡人</th><th>月費(PHP)</th><th>狀態</th><th>開始</th><th>結束</th><th>操作</th></tr></thead>
            <tbody id="adv-table-body">
              <tr><td colspan="8"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Tab: Devices ── -->
    <div id="tab-devices" class="tab-pane">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px">
        <h3 style="font-size:15px;font-weight:600;color:var(--gray-800)">封鎖裝置</h3>
        <div style="display:flex;gap:8px">
          <button class="btn btn-outline" onclick="window.location.href='/admin/api/export/devices'">匯出 CSV</button>
          <button class="btn btn-danger" onclick="openBlockModal()">+ 封鎖裝置</button>
        </div>
      </div>
      <div class="card" style="margin-bottom:20px">
        <div class="table-wrap">
          <table>
            <thead><tr><th>MAC</th><th>原因</th><th>封鎖者</th><th>封鎖時間</th><th>到期</th><th>操作</th></tr></thead>
            <tbody id="blocked-table-body">
              <tr><td colspan="6"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-title">裝置查詢</div>
        <div style="display:flex;gap:8px;margin-bottom:16px">
          <input class="form-control" id="dev-lookup-mac" placeholder="輸入 MAC 地址 (AA:BB:CC:DD:EE:FF)" style="max-width:300px">
          <button class="btn btn-primary" onclick="lookupDevice()">查詢</button>
        </div>
        <div id="dev-history"></div>
      </div>
    </div>

    <!-- ── Tab: Sessions ── -->
    <div id="tab-sessions" class="tab-pane">
      <div class="kpi-grid" id="sess-kpis" style="margin-bottom:16px">
        <div class="loading-state"><span class="spinner"></span> 載入中...</div>
      </div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div class="card-title" style="margin:0">活躍連線</div>
          <div style="font-size:12px;color:var(--gray-400)"><span id="sess-refresh-countdown">30</span>s 後自動刷新</div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>MAC</th><th>熱點</th><th>開始時間</th><th>到期時間</th><th>剩餘(分鐘)</th><th>操作</th></tr></thead>
            <tbody id="sess-table-body">
              <tr><td colspan="7"><div class="loading-state"><span class="spinner"></span> 載入中...</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Tab: Settings ── -->
    <div id="tab-settings" class="tab-pane">
      <div class="section-grid cols-2">
        <div class="card">
          <div class="card-title">商業規則</div>
          <div class="form-group">
            <label class="form-label">廣告時長（秒）</label>
            <input class="form-control" id="set-ad-dur" type="number">
          </div>
          <div class="form-group">
            <label class="form-label">連線時長（秒）</label>
            <input class="form-control" id="set-sess-dur" type="number">
          </div>
          <div class="form-group">
            <label class="form-label">防刷間隔（秒）</label>
            <input class="form-control" id="set-spam-win" type="number">
          </div>
          <button class="btn btn-primary" onclick="saveSettings()" style="margin-top:8px">儲存設定</button>
          <div style="font-size:11px;color:var(--gray-400);margin-top:8px">注意：修改僅影響執行中的程序，重啟後回復 .env 設定</div>
        </div>
        <div class="card">
          <div class="card-title">系統資訊</div>
          <div id="settings-sysinfo"><div class="loading-state"><span class="spinner"></span></div></div>
          <div style="margin-top:16px">
            <button class="btn btn-outline" onclick="testOmada()">測試 Omada 連線</button>
            <span id="omada-test-result" style="margin-left:8px;font-size:13px"></span>
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

<!-- ══ Advertiser Modal ══ -->
<div class="modal-overlay" id="adv-modal">
  <div class="modal">
    <div class="modal-header">
      <h2 id="adv-modal-title">&#128230; 新增廣告主</h2>
      <button class="modal-close" onclick="closeAdvModal()">&times;</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="adv-edit-id">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">名稱 *</label>
          <input class="form-control" id="adv-name" placeholder="廣告主名稱">
        </div>
        <div class="form-group">
          <label class="form-label">聯絡人</label>
          <input class="form-control" id="adv-contact" placeholder="電話/Email">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Banner URL *</label>
        <input class="form-control" id="adv-banner" placeholder="https://...">
      </div>
      <div class="form-group">
        <label class="form-label">Click URL *</label>
        <input class="form-control" id="adv-click" placeholder="https://...">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">月費 (PHP) *</label>
          <input class="form-control" id="adv-fee" type="number" step="0.01" placeholder="5000">
        </div>
        <div class="form-group">
          <label class="form-label">狀態</label>
          <select class="form-control form-select" id="adv-active">
            <option value="true">啟用</option>
            <option value="false">停用</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">開始日期 *</label>
          <input class="form-control" id="adv-start" type="datetime-local">
        </div>
        <div class="form-group">
          <label class="form-label">結束日期</label>
          <input class="form-control" id="adv-end" type="datetime-local">
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" onclick="closeAdvModal()">取消</button>
      <button class="btn btn-primary" onclick="submitAdvertiser()">確認</button>
    </div>
  </div>
</div>

<!-- ══ Block Device Modal ══ -->
<div class="modal-overlay" id="block-modal">
  <div class="modal">
    <div class="modal-header">
      <h2>&#128683; 封鎖裝置</h2>
      <button class="modal-close" onclick="closeBlockModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">MAC 地址 *</label>
        <input class="form-control" id="block-mac" placeholder="AA:BB:CC:DD:EE:FF">
      </div>
      <div class="form-group">
        <label class="form-label">原因</label>
        <input class="form-control" id="block-reason" placeholder="封鎖原因">
      </div>
      <div class="form-group">
        <label class="form-label">到期時間（留空=永久）</label>
        <input class="form-control" id="block-expires" type="datetime-local">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" onclick="closeBlockModal()">取消</button>
      <button class="btn btn-danger" onclick="submitBlock()">確認封鎖</button>
    </div>
  </div>
</div>

<!-- ══ Hotspot Detail Modal ══ -->
<div class="modal-overlay" id="hs-detail-modal">
  <div class="modal" style="width:640px">
    <div class="modal-header">
      <h2 id="hs-detail-title">&#128205; 熱點詳情</h2>
      <button class="modal-close" onclick="closeHsDetail()">&times;</button>
    </div>
    <div class="modal-body" id="hs-detail-body">
      <div class="loading-state"><span class="spinner"></span> 載入中...</div>
    </div>
  </div>
</div>

<!-- ══ Confirm Dialog ══ -->
<div class="modal-overlay" id="confirm-modal">
  <div class="modal" style="width:400px">
    <div class="modal-header">
      <h2 id="confirm-title">確認操作</h2>
      <button class="modal-close" onclick="closeConfirm()">&times;</button>
    </div>
    <div class="modal-body">
      <p id="confirm-msg">確定要執行此操作？</p>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" onclick="closeConfirm()">取消</button>
      <button class="btn btn-danger" id="confirm-btn" onclick="confirmAction()">確認</button>
    </div>
  </div>
</div>

<div id="toast-container"></div>

<script>
// Auth handled by browser's built-in Basic Auth credential caching
const headers = { 'Content-Type': 'application/json' };
const headersGet = {};

// XSS escape helper
function esc(s) { if (s == null) return '—'; const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }

let trendChart = null;
let revenueChart = null;
let liveTimer = null;
let liveCountdown = 15;
let allHotspots = [];
let allUsers = [];
let allAdvertisers = [];
let usersPage = 0;
const PAGE_SIZE = 50;
let sessTimer = null;
let sessCountdown = 30;
let pendingConfirmFn = null;

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
const tabTitles = { dashboard:'Dashboard', hotspots:'熱點管理', revenue:'收入分析', live:'即時監控', users:'用戶記錄', security:'資安中心', advertisers:'廣告主管理', devices:'設備管理', sessions:'連線管理', settings:'系統設定' };
function switchTab(tab, el) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.getElementById('topbar-title').textContent = tabTitles[tab] || tab;
  const li = document.getElementById('live-indicator');
  if (tab === 'live') { li.style.display=''; startLiveTimer(); }
  else { li.style.display='none'; stopLiveTimer(); }
  if (tab !== 'sessions') stopSessTimer();
  if (tab === 'dashboard') loadDashboard();
  if (tab === 'hotspots') loadHotspots();
  if (tab === 'revenue') { setDefaultMonth(); loadRevenue(); }
  if (tab === 'live') loadLive();
  if (tab === 'users') loadUsers();
  if (tab === 'security') loadSecurity();
  if (tab === 'advertisers') loadAdvertisers();
  if (tab === 'devices') loadDevices();
  if (tab === 'sessions') { loadSessions(); startSessTimer(); }
  if (tab === 'settings') loadSettings();
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
    document.getElementById('dash-kpis').innerHTML = '<div class="empty-state"><div class="empty-icon">&#9888;</div>載入失敗：' + esc(e.message) + '</div>';
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
    '<tr><td><strong>' + esc(h.name || h.id) + '</strong></td>' +
    '<td>' + esc(h.location) + '</td>' +
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
    document.getElementById('hs-table-body').innerHTML = '<tr><td colspan="9"><div class="empty-state">&#9888; 載入失敗：' + esc(e.message) + '</div></td></tr>';
  }
}

function renderHotspotTable(hs) {
  const tbody = document.getElementById('hs-table-body');
  if (!hs.length) { tbody.innerHTML = '<tr><td colspan="9"><div class="empty-state"><div class="empty-icon">&#128205;</div>無熱點資料</div></td></tr>'; return; }
  tbody.innerHTML = hs.map(h =>
    '<tr>' +
    '<td>' + esc(h.id) + '</td>' +
    '<td><strong>' + esc(h.name) + '</strong></td>' +
    '<td>' + esc(h.location) + '</td>' +
    '<td><code style="font-size:11px;background:var(--gray-100);padding:2px 6px;border-radius:4px">' + esc(h.ap_mac) + '</code></td>' +
    '<td>' + esc(h.site_name || h.site_id || h.site) + '</td>' +
    '<td style="font-size:11px;color:var(--gray-500)">' + (h.latitude ? h.latitude.toFixed(4) + ', ' + (h.longitude || 0).toFixed(4) : '—') + '</td>' +
    '<td>' + fmt(h.today_visits || 0) + '</td>' +
    '<td><span class="badge ' + (h.is_active !== false ? 'success' : 'danger') + '">' + (h.is_active !== false ? '啟用' : '停用') + '</span></td>' +
    '<td style="white-space:nowrap">' +
    '<button class="btn btn-outline btn-sm" onclick="openHsDetail(' + h.id + ')" title="詳情">&#128269;</button> ' +
    '<button class="btn btn-outline btn-sm" onclick="openEditHotspot(' + h.id + ')" title="編輯">&#9998;</button> ' +
    '<button class="btn btn-outline btn-sm" onclick="toggleHotspot(' + h.id + ',' + (h.is_active !== false) + ')">' + (h.is_active !== false ? '停用' : '啟用') + '</button> ' +
    '<button class="btn btn-sm" style="color:var(--danger)" onclick="confirmDeleteHotspot(' + h.id + ')" title="刪除">&#128465;</button>' +
    '</td></tr>'
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

function openAddModal() { document.getElementById('add-modal').classList.add('show'); document.getElementById('add-modal').dataset.editId = ''; }
function closeModal() { document.getElementById('add-modal').classList.remove('show'); document.getElementById('add-modal').dataset.editId = ''; }

async function submitAddHotspot() {
  const name = document.getElementById('f-name').value.trim();
  const location = document.getElementById('f-location').value.trim();
  if (!name || !location) { toast('請填寫名稱與地點', 'error'); return; }
  const editId = document.getElementById('add-modal').dataset.editId;
  const payload = {
    name, location,
    ap_mac: document.getElementById('f-mac').value.trim() || null,
    site_name: document.getElementById('f-site').value.trim() || null,
    latitude: parseFloat(document.getElementById('f-lat').value) || null,
    longitude: parseFloat(document.getElementById('f-lng').value) || null,
  };
  try {
    const url = editId ? '/admin/api/hotspots/' + editId : '/admin/api/hotspots';
    const method = editId ? 'PATCH' : 'POST';
    if (!editId) payload.is_active = true;
    const r = await fetch(url, { method, headers, body:JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || r.status); }
    toast(editId ? '熱點已更新！' : '熱點新增成功！', 'success');
    closeModal();
    loadHotspots();
    ['f-name','f-location','f-mac','f-site','f-lat','f-lng','f-note'].forEach(id => { document.getElementById(id).value = ''; });
  } catch(e) {
    toast('操作失敗：' + e.message, 'error');
  }
}

function populateHotspotFilter(hs) {
  const sel = document.getElementById('usr-hotspot-filter');
  const cur = sel.value;
  sel.innerHTML = '<option value="">所有熱點</option>' + hs.map(h => '<option value="' + h.id + '">' + esc(h.name || h.id) + '</option>').join('');
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
    document.getElementById('rev-kpis').innerHTML = '<div class="empty-state">&#9888; 載入失敗：' + esc(e.message) + '</div>';
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
    return '<tr><td><strong>' + esc(r.hotspot_name || r.name) + '</strong></td>' +
      '<td>' + esc(r.location) + '</td>' +
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
    document.getElementById('live-table-body').innerHTML = '<tr><td colspan="6"><div class="empty-state">&#9888; 載入失敗：' + esc(e.message) + '</div></td></tr>';
  }
}

function renderLiveTable(hs) {
  const tbody = document.getElementById('live-table-body');
  if (!hs.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">無熱點在線</div></td></tr>'; return; }
  tbody.innerHTML = hs.map(h =>
    '<tr>' +
    '<td><strong>' + esc(h.name) + '</strong></td>' +
    '<td>' + esc(h.location) + '</td>' +
    '<td style="font-size:18px;font-weight:700;color:var(--primary)">' + fmt(h.online || h.online_users || 0) + '</td>' +
    '<td>' + fmt(h.today_visits || 0) + '</td>' +
    '<td>' + esc(fmtDate(h.last_activity || h.last_seen)) + '</td>' +
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
    document.getElementById('usr-table-body').innerHTML = '<tr><td colspan="6"><div class="empty-state">&#9888; 載入失敗：' + esc(e.message) + '</div></td></tr>';
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
      '<td><code style="font-size:12px;background:var(--gray-100);padding:2px 6px;border-radius:4px">' + esc(u.mac || u.mac_address) + '</code></td>' +
      '<td>' + esc(u.hotspot_name || u.hotspot) + '</td>' +
      '<td><code style="font-size:12px">' + esc(u.ip || u.ip_address) + '</code></td>' +
      '<td>' + esc(fmtDate(u.created_at || u.timestamp || u.visited_at)) + '</td>' +
      '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(u.user_agent || '') + '">' + esc(truncate(u.user_agent, 35)) + '</td>' +
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
  await Promise.all([loadSecurityStats(), loadSysInfo(), loadAuditLog(), loadBlockedCount()]);
}

async function loadAuditLog() {
  try {
    const r = await fetch('/admin/api/audit-log?limit=15', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const div = document.getElementById('sec-audit-log');
    if (!d.items || !d.items.length) { div.innerHTML = '<div class="empty-state">無記錄</div>'; return; }
    div.innerHTML = d.items.map(l =>
      '<div class="ip-stat-item"><div><strong>' + esc(l.action) + '</strong>' +
      (l.target_type ? ' <span class="badge gray">' + esc(l.target_type) + (l.target_id ? '#' + esc(l.target_id) : '') + '</span>' : '') +
      '<div style="font-size:11px;color:var(--gray-400);margin-top:2px">' + esc(l.admin_user) + ' | ' + fmtDate(l.created_at) + '</div></div></div>'
    ).join('');
  } catch(e) {
    document.getElementById('sec-audit-log').innerHTML = '<div class="empty-state">載入失敗</div>';
  }
}

async function loadBlockedCount() {
  try {
    const r = await fetch('/admin/api/devices/blocked', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    document.getElementById('sec-blocked-count').textContent = d.length;
  } catch(e) { document.getElementById('sec-blocked-count').textContent = '?'; }
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
        '<div class="ip-stat-item"><code style="font-size:12px">' + esc(mac) + '</code><span class="badge danger">' + c + ' 次</span></div>'
      ).join('');
    }
    if (topIPs.length) {
      document.getElementById('sec-ip-stats').innerHTML = topIPs.map(([ip, c]) =>
        '<div class="ip-stat-item"><code style="font-size:12px">' + esc(ip) + '</code><span class="badge info">' + c + ' 次</span></div>'
      ).join('');
    } else {
      document.getElementById('sec-ip-stats').innerHTML = '<div class="empty-state">無 IP 統計資料</div>';
    }
  } catch(e) {
    document.getElementById('sec-stats').innerHTML = '<div class="empty-state">&#9888; ' + esc(e.message) + '</div>';
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

// ── Hotspot Detail/Edit/Delete ──
async function openHsDetail(id) {
  document.getElementById('hs-detail-modal').classList.add('show');
  document.getElementById('hs-detail-body').innerHTML = '<div class="loading-state"><span class="spinner"></span> 載入中...</div>';
  try {
    const r = await fetch('/admin/api/hotspots/' + id + '/detail', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const h = d.hotspot;
    let html = '<div class="kpi-grid" style="margin-bottom:16px">' +
      '<div class="kpi-card primary"><div class="kpi-label">今日訪問</div><div class="kpi-value">' + fmt(d.visits_today) + '</div></div>' +
      '<div class="kpi-card success"><div class="kpi-label">7日訪問</div><div class="kpi-value">' + fmt(d.visits_week) + '</div></div>' +
      '<div class="kpi-card warning"><div class="kpi-label">今日廣告</div><div class="kpi-value">' + fmt(d.ads_today) + '</div></div></div>';
    if (d.top_devices && d.top_devices.length) {
      html += '<h4 style="margin:12px 0 8px;font-size:13px;font-weight:600">Top 裝置</h4><table><thead><tr><th>MAC</th><th>訪問次數</th></tr></thead><tbody>';
      d.top_devices.forEach(td => { html += '<tr><td><code>' + esc(td.mac) + '</code></td><td>' + td.count + '</td></tr>'; });
      html += '</tbody></table>';
    }
    document.getElementById('hs-detail-title').innerHTML = '&#128205; ' + esc(h.name);
    document.getElementById('hs-detail-body').innerHTML = html;
  } catch(e) {
    document.getElementById('hs-detail-body').innerHTML = '<div class="empty-state">載入失敗：' + esc(e.message) + '</div>';
  }
}
function closeHsDetail() { document.getElementById('hs-detail-modal').classList.remove('show'); }

function openEditHotspot(id) {
  const h = allHotspots.find(x => x.id === id);
  if (!h) return;
  document.getElementById('f-name').value = h.name || '';
  document.getElementById('f-location').value = h.location || '';
  document.getElementById('f-mac').value = h.ap_mac || '';
  document.getElementById('f-site').value = h.site_name || '';
  document.getElementById('f-lat').value = h.latitude || '';
  document.getElementById('f-lng').value = h.longitude || '';
  document.getElementById('add-modal').classList.add('show');
  document.getElementById('add-modal').dataset.editId = id;
}

async function confirmDeleteHotspot(id) {
  showConfirm('確定要刪除此熱點？此操作無法復原。', async () => {
    try {
      const r = await fetch('/admin/api/hotspots/' + id, { method: 'DELETE', headers });
      if (!r.ok) throw new Error(r.status);
      toast('熱點已刪除', 'success');
      loadHotspots();
    } catch(e) { toast('刪除失敗：' + e.message, 'error'); }
  });
}

// ── Revenue Daily ──
let revDailyChart = null;
async function loadRevenueDaily() {
  const start = document.getElementById('rev-start').value;
  const end = document.getElementById('rev-end').value;
  if (!start || !end) { toast('請選擇日期範圍', 'error'); return; }
  try {
    const r = await fetch('/admin/api/revenue/daily?start=' + start + '&end=' + end, { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    document.getElementById('rev-daily-section').style.display = 'block';
    document.getElementById('rev-daily-kpis').innerHTML =
      '<div class="kpi-card success"><div class="kpi-label">總收入</div><div class="kpi-value">$' + d.total_revenue + '</div></div>' +
      '<div class="kpi-card primary"><div class="kpi-label">總展示</div><div class="kpi-value">' + fmt(d.total_views) + '</div></div>' +
      '<div class="kpi-card warning"><div class="kpi-label">CPM</div><div class="kpi-value">$' + d.cpm + '</div></div>';
    const ctx = document.getElementById('chart-revenue-daily');
    if (revDailyChart) { revDailyChart.destroy(); revDailyChart = null; }
    revDailyChart = new Chart(ctx, {
      type:'line',
      data:{ labels: d.days.map(x=>x.date), datasets:[{ label:'Revenue', data:d.days.map(x=>parseFloat(x.revenue)), borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,.1)', fill:true, tension:.3 }] },
      options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true } } }
    });
  } catch(e) { toast('查詢失敗：' + e.message, 'error'); }
}

// ── Advertisers ──
async function loadAdvertisers() {
  try {
    const r = await fetch('/admin/api/advertisers', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    allAdvertisers = await r.json();
    renderAdvTable(allAdvertisers);
  } catch(e) {
    document.getElementById('adv-table-body').innerHTML = '<tr><td colspan="8"><div class="empty-state">載入失敗</div></td></tr>';
  }
}

function renderAdvTable(advs) {
  const tbody = document.getElementById('adv-table-body');
  if (!advs.length) { tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state">無廣告主</div></td></tr>'; return; }
  tbody.innerHTML = advs.map(a =>
    '<tr><td>' + a.id + '</td><td><strong>' + esc(a.name) + '</strong></td><td>' + esc(a.contact) + '</td>' +
    '<td>PHP ' + fmt(a.monthly_fee_php) + '</td>' +
    '<td><span class="badge ' + (a.is_active ? 'success' : 'danger') + '">' + (a.is_active ? '啟用' : '停用') + '</span></td>' +
    '<td>' + fmtDate(a.starts_at) + '</td><td>' + fmtDate(a.ends_at) + '</td>' +
    '<td style="white-space:nowrap">' +
    '<button class="btn btn-outline btn-sm" onclick="editAdvertiser(' + a.id + ')">&#9998;</button> ' +
    '<button class="btn btn-sm" style="color:var(--danger)" onclick="deleteAdvertiser(' + a.id + ')">&#128465;</button></td></tr>'
  ).join('');
}

function filterAdvertisers() {
  const q = document.getElementById('adv-search').value.toLowerCase();
  renderAdvTable(allAdvertisers.filter(a => (a.name||'').toLowerCase().includes(q) || (a.contact||'').toLowerCase().includes(q)));
}

function openAdvModal(editId) {
  document.getElementById('adv-edit-id').value = editId || '';
  document.getElementById('adv-modal-title').textContent = editId ? '&#9998; 編輯廣告主' : '&#128230; 新增廣告主';
  if (!editId) {
    ['adv-name','adv-contact','adv-banner','adv-click','adv-fee','adv-start','adv-end'].forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('adv-active').value = 'true';
  }
  document.getElementById('adv-modal').classList.add('show');
}

function closeAdvModal() { document.getElementById('adv-modal').classList.remove('show'); }

function editAdvertiser(id) {
  const a = allAdvertisers.find(x => x.id === id);
  if (!a) return;
  document.getElementById('adv-edit-id').value = id;
  document.getElementById('adv-name').value = a.name || '';
  document.getElementById('adv-contact').value = a.contact || '';
  document.getElementById('adv-banner').value = a.banner_url || '';
  document.getElementById('adv-click').value = a.click_url || '';
  document.getElementById('adv-fee').value = a.monthly_fee_php || '';
  document.getElementById('adv-active').value = String(a.is_active);
  document.getElementById('adv-start').value = a.starts_at ? a.starts_at.slice(0,16) : '';
  document.getElementById('adv-end').value = a.ends_at ? a.ends_at.slice(0,16) : '';
  document.getElementById('adv-modal').classList.add('show');
  document.getElementById('adv-modal-title').textContent = '&#9998; 編輯廣告主';
}

async function submitAdvertiser() {
  const editId = document.getElementById('adv-edit-id').value;
  const payload = {
    name: document.getElementById('adv-name').value.trim(),
    contact: document.getElementById('adv-contact').value.trim() || null,
    banner_url: document.getElementById('adv-banner').value.trim(),
    click_url: document.getElementById('adv-click').value.trim(),
    monthly_fee_php: parseFloat(document.getElementById('adv-fee').value) || 0,
    is_active: document.getElementById('adv-active').value === 'true',
    starts_at: document.getElementById('adv-start').value ? new Date(document.getElementById('adv-start').value).toISOString() : null,
    ends_at: document.getElementById('adv-end').value ? new Date(document.getElementById('adv-end').value).toISOString() : null,
    hotspot_ids: [],
  };
  if (!payload.name || !payload.banner_url || !payload.click_url) { toast('請填寫必要欄位', 'error'); return; }
  try {
    const url = editId ? '/admin/api/advertisers/' + editId : '/admin/api/advertisers';
    const method = editId ? 'PATCH' : 'POST';
    const r = await fetch(url, { method, headers, body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || r.status); }
    toast(editId ? '廣告主已更新' : '廣告主已新增', 'success');
    closeAdvModal();
    loadAdvertisers();
  } catch(e) { toast('操作失敗：' + e.message, 'error'); }
}

async function deleteAdvertiser(id) {
  showConfirm('確定要停用此廣告主？', async () => {
    try {
      const r = await fetch('/admin/api/advertisers/' + id, { method: 'DELETE', headers });
      if (!r.ok) throw new Error(r.status);
      toast('廣告主已停用', 'success');
      loadAdvertisers();
    } catch(e) { toast('操作失敗：' + e.message, 'error'); }
  });
}

// ── Devices ──
async function loadDevices() {
  try {
    const r = await fetch('/admin/api/devices/blocked', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    renderBlockedTable(d);
  } catch(e) {
    document.getElementById('blocked-table-body').innerHTML = '<tr><td colspan="6"><div class="empty-state">載入失敗</div></td></tr>';
  }
}

function renderBlockedTable(devices) {
  const tbody = document.getElementById('blocked-table-body');
  if (!devices.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state">無封鎖裝置</div></td></tr>'; return; }
  tbody.innerHTML = devices.map(d =>
    '<tr><td><code>' + esc(d.client_mac) + '</code></td><td>' + esc(d.reason) + '</td><td>' + esc(d.blocked_by) + '</td>' +
    '<td>' + fmtDate(d.blocked_at) + '</td><td>' + (d.expires_at ? fmtDate(d.expires_at) : '永久') + '</td>' +
    '<td><button class="btn btn-outline btn-sm" onclick="unblockDevice(' + d.id + ')">解除</button></td></tr>'
  ).join('');
}

function openBlockModal() { document.getElementById('block-modal').classList.add('show'); }
function closeBlockModal() { document.getElementById('block-modal').classList.remove('show'); }

async function submitBlock() {
  const mac = document.getElementById('block-mac').value.trim();
  if (!mac) { toast('請輸入 MAC 地址', 'error'); return; }
  const payload = {
    client_mac: mac,
    reason: document.getElementById('block-reason').value.trim() || null,
    expires_at: document.getElementById('block-expires').value ? new Date(document.getElementById('block-expires').value).toISOString() : null,
  };
  try {
    const r = await fetch('/admin/api/devices/block', { method: 'POST', headers, body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || r.status); }
    toast('裝置已封鎖', 'success');
    closeBlockModal();
    ['block-mac','block-reason','block-expires'].forEach(id => { document.getElementById(id).value = ''; });
    loadDevices();
  } catch(e) { toast('封鎖失敗：' + e.message, 'error'); }
}

async function unblockDevice(id) {
  showConfirm('確定要解除封鎖？', async () => {
    try {
      const r = await fetch('/admin/api/devices/block/' + id, { method: 'DELETE', headers });
      if (!r.ok) throw new Error(r.status);
      toast('已解除封鎖', 'success');
      loadDevices();
    } catch(e) { toast('操作失敗：' + e.message, 'error'); }
  });
}

async function lookupDevice() {
  const mac = document.getElementById('dev-lookup-mac').value.trim();
  if (!mac) { toast('請輸入 MAC', 'error'); return; }
  const div = document.getElementById('dev-history');
  div.innerHTML = '<div class="loading-state"><span class="spinner"></span> 查詢中...</div>';
  try {
    const r = await fetch('/admin/api/devices/' + encodeURIComponent(mac) + '/history', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    let html = '<div class="kpi-grid" style="margin-bottom:12px">' +
      '<div class="kpi-card primary"><div class="kpi-label">訪問</div><div class="kpi-value">' + d.visits.length + '</div></div>' +
      '<div class="kpi-card success"><div class="kpi-label">連線</div><div class="kpi-value">' + d.grants.length + '</div></div>' +
      '<div class="kpi-card warning"><div class="kpi-label">廣告</div><div class="kpi-value">' + d.ad_views.length + '</div></div></div>';
    if (d.visits.length) {
      html += '<h4 style="margin:8px 0;font-size:13px">最近訪問</h4><table><thead><tr><th>時間</th><th>IP</th><th>熱點ID</th></tr></thead><tbody>';
      d.visits.slice(0,10).forEach(v => { html += '<tr><td>' + fmtDate(v.at) + '</td><td>' + esc(v.ip) + '</td><td>' + v.hotspot_id + '</td></tr>'; });
      html += '</tbody></table>';
    }
    div.innerHTML = html;
  } catch(e) { div.innerHTML = '<div class="empty-state">查詢失敗：' + esc(e.message) + '</div>'; }
}

// ── Sessions ──
function startSessTimer() {
  stopSessTimer();
  sessCountdown = 30;
  sessTimer = setInterval(() => {
    sessCountdown--;
    const el = document.getElementById('sess-refresh-countdown');
    if (el) el.textContent = sessCountdown;
    if (sessCountdown <= 0) { sessCountdown = 30; loadSessions(); }
  }, 1000);
}
function stopSessTimer() { if (sessTimer) { clearInterval(sessTimer); sessTimer = null; } }

async function loadSessions() {
  sessCountdown = 30;
  try {
    const r = await fetch('/admin/api/sessions/active', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    document.getElementById('sess-kpis').innerHTML =
      '<div class="kpi-card primary"><div class="kpi-icon">&#128268;</div><div class="kpi-label">活躍連線</div><div class="kpi-value">' + fmt(d.total) + '</div></div>' +
      '<div class="kpi-card success"><div class="kpi-icon">&#9200;</div><div class="kpi-label">平均剩餘</div><div class="kpi-value">' + Math.round(d.avg_remaining_seconds / 60) + ' 分鐘</div></div>';
    const tbody = document.getElementById('sess-table-body');
    if (!d.items.length) { tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state">無活躍連線</div></td></tr>'; return; }
    tbody.innerHTML = d.items.map(s =>
      '<tr><td>' + s.id + '</td><td><code>' + esc(s.client_mac) + '</code></td><td>' + esc(s.hotspot_name) + '</td>' +
      '<td>' + fmtDate(s.granted_at) + '</td><td>' + fmtDate(s.expires_at) + '</td>' +
      '<td>' + Math.round(s.remaining_seconds / 60) + '</td>' +
      '<td><button class="btn btn-danger btn-sm" onclick="revokeSession(' + s.id + ')">撤銷</button></td></tr>'
    ).join('');
    setLastUpdate();
  } catch(e) {
    document.getElementById('sess-table-body').innerHTML = '<tr><td colspan="7"><div class="empty-state">載入失敗</div></td></tr>';
  }
}

async function revokeSession(id) {
  showConfirm('確定要撤銷此連線？裝置將失去網路存取。', async () => {
    try {
      const r = await fetch('/admin/api/sessions/' + id + '/revoke', { method: 'POST', headers });
      if (!r.ok) throw new Error(r.status);
      toast('連線已撤銷', 'success');
      loadSessions();
    } catch(e) { toast('撤銷失敗：' + e.message, 'error'); }
  });
}

// ── Settings ──
async function loadSettings() {
  try {
    const r = await fetch('/admin/api/settings', { headers: headersGet });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    document.getElementById('set-ad-dur').value = d.ad_duration_seconds;
    document.getElementById('set-sess-dur').value = d.session_duration_seconds;
    document.getElementById('set-spam-win').value = d.anti_spam_window_seconds;
    document.getElementById('settings-sysinfo').innerHTML =
      '<div class="ip-stat-item"><span>App Name</span><span class="badge gray">' + esc(d.app_name) + '</span></div>' +
      '<div class="ip-stat-item"><span>Environment</span><span class="badge ' + (d.environment === 'production' ? 'danger' : 'info') + '">' + esc(d.environment) + '</span></div>' +
      '<div class="ip-stat-item"><span>Omada Host</span><span class="badge gray">' + esc(d.omada_host) + '</span></div>';
  } catch(e) { toast('載入設定失敗', 'error'); }
}

async function saveSettings() {
  const payload = {
    ad_duration_seconds: parseInt(document.getElementById('set-ad-dur').value) || null,
    session_duration_seconds: parseInt(document.getElementById('set-sess-dur').value) || null,
    anti_spam_window_seconds: parseInt(document.getElementById('set-spam-win').value) || null,
  };
  try {
    const r = await fetch('/admin/api/settings', { method: 'PATCH', headers, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(r.status);
    toast('設定已儲存', 'success');
  } catch(e) { toast('儲存失敗：' + e.message, 'error'); }
}

async function testOmada() {
  const el = document.getElementById('omada-test-result');
  el.innerHTML = '<span class="spinner"></span>';
  try {
    const r = await fetch('/admin/api/settings/test-omada', { method: 'POST', headers });
    const d = await r.json();
    el.innerHTML = d.status === 'ok'
      ? '<span class="badge success">連線成功</span>'
      : '<span class="badge danger">' + esc(d.message) + '</span>';
  } catch(e) { el.innerHTML = '<span class="badge danger">測試失敗</span>'; }
}

// ── Confirm Dialog ──
function showConfirm(msg, fn) {
  pendingConfirmFn = fn;
  document.getElementById('confirm-msg').textContent = msg;
  document.getElementById('confirm-modal').classList.add('show');
}
function closeConfirm() { document.getElementById('confirm-modal').classList.remove('show'); pendingConfirmFn = null; }
async function confirmAction() {
  closeConfirm();
  if (pendingConfirmFn) { await pendingConfirmFn(); pendingConfirmFn = null; }
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

    hotspots_result = await db.execute(select(Hotspot).where(Hotspot.is_active == True))  # noqa: E712
    hotspots = hotspots_result.scalars().all()

    # Batch queries with GROUP BY instead of N+1
    visits_by_hs = await db.execute(
        select(Visit.hotspot_id, func.count(Visit.id).label("cnt"))
        .where(Visit.visited_at >= today_start)
        .group_by(Visit.hotspot_id)
    )
    visits_map = {row.hotspot_id: row.cnt for row in visits_by_hs.all()}

    adviews_by_hs = await db.execute(
        select(AdView.hotspot_id, func.count(AdView.id).label("cnt"), func.sum(AdView.estimated_revenue_usd).label("rev"))
        .where(AdView.viewed_at >= today_start)
        .group_by(AdView.hotspot_id)
    )
    adviews_map: dict[int, tuple[int, Decimal]] = {}
    for row in adviews_by_hs.all():
        adviews_map[row.hotspot_id] = (row.cnt, row.rev or Decimal("0.0000"))

    redis_svc = RedisService(redis)
    hotspot_stats: list[HotspotStats] = []
    active_users_total = 0

    for hotspot in hotspots:
        active = await redis_svc.get_active_users_count(hotspot.id)
        active_users_total += active
        av_cnt, av_rev = adviews_map.get(hotspot.id, (0, Decimal("0.0000")))
        hotspot_stats.append(HotspotStats(
            hotspot_id=hotspot.id,
            hotspot_name=hotspot.name,
            visits_today=visits_map.get(hotspot.id, 0),
            ad_views_today=av_cnt,
            revenue_today_usd=av_rev,
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
    await record_audit(db, request, "create_hotspot", "hotspot", str(hotspot.id), {"name": hotspot.name})
    await db.commit()
    logger.info("hotspot_created", hotspot_id=hotspot.id)
    return HotspotResponse.model_validate(hotspot)


@router.patch("/api/hotspots/{hotspot_id}", response_model=HotspotResponse)
async def update_hotspot(
    request: Request,
    hotspot_id: int,
    body: HotspotUpdate,
    db: AsyncSession = Depends(get_db),
) -> HotspotResponse:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if hotspot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotspot not found")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hotspot, field, value)
    hotspot.updated_at = datetime.now(tz=timezone.utc)
    await db.flush()
    await db.refresh(hotspot)
    await record_audit(db, request, "update_hotspot", "hotspot", str(hotspot_id), update_data)
    await db.commit()
    logger.info("hotspot_updated", hotspot_id=hotspot_id, fields=list(update_data.keys()))
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

    # Batch query with GROUP BY instead of N+1
    rev_by_hs = await db.execute(
        select(
            AdView.hotspot_id,
            func.sum(AdView.estimated_revenue_usd).label("rev"),
            func.count(AdView.id).label("cnt"),
        )
        .where(AdView.viewed_at >= period_start, AdView.viewed_at < period_end)
        .group_by(AdView.hotspot_id)
    )
    rev_map = {row.hotspot_id: (row.rev or Decimal("0.0000"), row.cnt) for row in rev_by_hs.all()}

    hotspots_result = await db.execute(select(Hotspot))
    breakdown: list[dict[str, Any]] = []
    for h in hotspots_result.scalars().all():
        rev, cnt = rev_map.get(h.id, (Decimal("0.0000"), 0))
        breakdown.append({"hotspot_id": h.id, "hotspot_name": h.name, "revenue_usd": str(rev), "ad_views": cnt})

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


# ── Advertiser CRUD ──────────────────────────────────────────────────────


@router.get("/api/advertisers")
async def list_advertisers(
    request: Request, db: AsyncSession = Depends(get_db),
) -> list[DirectAdvertiserResponse]:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).order_by(DirectAdvertiser.id.desc()))
    return [DirectAdvertiserResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/api/advertisers", response_model=DirectAdvertiserResponse, status_code=201)
async def create_advertiser(
    request: Request, body: DirectAdvertiserCreate, db: AsyncSession = Depends(get_db),
) -> DirectAdvertiserResponse:
    verify_basic_auth(request)
    adv = DirectAdvertiser(**body.model_dump())
    db.add(adv)
    await db.flush()
    await db.refresh(adv)
    await record_audit(db, request, "create_advertiser", "advertiser", str(adv.id), {"name": adv.name})
    await db.commit()
    return DirectAdvertiserResponse.model_validate(adv)


@router.patch("/api/advertisers/{adv_id}", response_model=DirectAdvertiserResponse)
async def update_advertiser(
    request: Request, adv_id: int, body: DirectAdvertiserUpdate, db: AsyncSession = Depends(get_db),
) -> DirectAdvertiserResponse:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).where(DirectAdvertiser.id == adv_id))
    adv = result.scalar_one_or_none()
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(adv, field, value)
    await db.flush()
    await db.refresh(adv)
    await record_audit(db, request, "update_advertiser", "advertiser", str(adv_id), update_data)
    await db.commit()
    return DirectAdvertiserResponse.model_validate(adv)


@router.delete("/api/advertisers/{adv_id}")
async def delete_advertiser(
    request: Request, adv_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(DirectAdvertiser).where(DirectAdvertiser.id == adv_id))
    adv = result.scalar_one_or_none()
    if not adv:
        raise HTTPException(status_code=404, detail="Advertiser not found")
    adv.is_active = False
    await record_audit(db, request, "delete_advertiser", "advertiser", str(adv_id), {"name": adv.name})
    await db.commit()
    return {"status": "deactivated"}


# ── Device Management ────────────────────────────────────────────────────


@router.get("/api/devices/blocked")
async def list_blocked_devices(
    request: Request, db: AsyncSession = Depends(get_db),
) -> list[BlockedDeviceResponse]:
    verify_basic_auth(request)
    result = await db.execute(
        select(BlockedDevice).where(BlockedDevice.is_active == True).order_by(BlockedDevice.blocked_at.desc())  # noqa: E712
    )
    return [BlockedDeviceResponse.model_validate(d) for d in result.scalars().all()]


@router.post("/api/devices/block", response_model=BlockedDeviceResponse, status_code=201)
async def block_device(
    request: Request, body: BlockedDeviceCreate, db: AsyncSession = Depends(get_db),
) -> BlockedDeviceResponse:
    verify_basic_auth(request)
    existing = await db.execute(
        select(BlockedDevice).where(BlockedDevice.client_mac == body.client_mac, BlockedDevice.is_active == True)  # noqa: E712
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Device already blocked")
    device = BlockedDevice(
        client_mac=body.client_mac,
        reason=body.reason,
        blocked_by=_extract_username(request),
        expires_at=body.expires_at,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    await record_audit(db, request, "block_device", "device", body.client_mac, {"reason": body.reason})
    await db.commit()
    return BlockedDeviceResponse.model_validate(device)


@router.delete("/api/devices/block/{block_id}")
async def unblock_device(
    request: Request, block_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(BlockedDevice).where(BlockedDevice.id == block_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Blocked device not found")
    device.is_active = False
    await record_audit(db, request, "unblock_device", "device", device.client_mac)
    await db.commit()
    return {"status": "unblocked"}


@router.get("/api/devices/{mac}/history")
async def device_history(
    request: Request,
    mac: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    visits_r = await db.execute(
        select(Visit).where(Visit.client_mac == mac).order_by(Visit.visited_at.desc()).limit(50)
    )
    grants_r = await db.execute(
        select(AccessGrant).where(AccessGrant.client_mac == mac).order_by(AccessGrant.granted_at.desc()).limit(50)
    )
    ads_r = await db.execute(
        select(AdView).where(AdView.client_mac == mac).order_by(AdView.viewed_at.desc()).limit(50)
    )
    return {
        "mac": mac,
        "visits": [
            {"id": v.id, "hotspot_id": v.hotspot_id, "ip": v.ip_address, "at": v.visited_at.isoformat()}
            for v in visits_r.scalars().all()
        ],
        "grants": [
            {"id": g.id, "hotspot_id": g.hotspot_id, "granted_at": g.granted_at.isoformat(),
             "expires_at": g.expires_at.isoformat(), "revoked": g.revoked}
            for g in grants_r.scalars().all()
        ],
        "ad_views": [
            {"id": a.id, "hotspot_id": a.hotspot_id, "network": a.ad_network, "at": a.viewed_at.isoformat()}
            for a in ads_r.scalars().all()
        ],
    }


# ── Session Management ───────────────────────────────────────────────────


@router.get("/api/sessions/active")
async def list_active_sessions(
    request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        select(AccessGrant, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, AccessGrant.hotspot_id == Hotspot.id, isouter=True)
        .where(AccessGrant.expires_at > now, AccessGrant.revoked == False)  # noqa: E712
        .order_by(AccessGrant.expires_at.asc())
    )
    rows = result.all()
    items = []
    for row in rows:
        grant = row.AccessGrant
        remaining = (grant.expires_at - now).total_seconds()
        items.append({
            "id": grant.id,
            "client_mac": grant.client_mac,
            "hotspot_name": row.hotspot_name or "Unknown",
            "hotspot_id": grant.hotspot_id,
            "granted_at": grant.granted_at.isoformat(),
            "expires_at": grant.expires_at.isoformat(),
            "remaining_seconds": max(0, int(remaining)),
        })
    avg_remaining = sum(i["remaining_seconds"] for i in items) / len(items) if items else 0
    return {"total": len(items), "avg_remaining_seconds": int(avg_remaining), "items": items}


@router.post("/api/sessions/{grant_id}/revoke")
async def revoke_session(
    request: Request, grant_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(AccessGrant).where(AccessGrant.id == grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Session not found")
    if grant.revoked:
        raise HTTPException(status_code=400, detail="Already revoked")
    grant.revoked = True
    # Try to revoke via Omada
    try:
        hs_result = await db.execute(select(Hotspot).where(Hotspot.id == grant.hotspot_id))
        hotspot = hs_result.scalar_one_or_none()
        if hotspot:
            omada = get_omada_client()
            await omada.revoke_access(client_mac=grant.client_mac, site=hotspot.site_name)
    except (OmadaError, RuntimeError) as exc:
        logger.warning("omada_revoke_failed_on_session_revoke", error=str(exc))
    await record_audit(db, request, "revoke_session", "session", str(grant_id), {"mac": grant.client_mac})
    await db.commit()
    return {"status": "revoked"}


# ── Audit Log ────────────────────────────────────────────────────────────


@router.get("/api/audit-log")
async def list_audit_log(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    action: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    q = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        q = q.where(AdminAuditLog.action == action)
    total_q = select(func.count(AdminAuditLog.id))
    if action:
        total_q = total_q.where(AdminAuditLog.action == action)
    result = await db.execute(q)
    total = (await db.execute(total_q)).scalar_one()
    return {
        "total": total,
        "items": [AuditLogResponse.model_validate(r).model_dump(mode="json") for r in result.scalars().all()],
    }


# ── Revenue Daily ────────────────────────────────────────────────────────


@router.get("/api/revenue/daily")
async def revenue_daily(
    request: Request,
    start: str = Query(default="", description="YYYY-MM-DD"),
    end: str = Query(default="", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    now = datetime.now(tz=timezone.utc)
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc) if start else now - timedelta(days=30)
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) if end else now
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    result = await db.execute(
        select(
            func.date(AdView.viewed_at).label("day"),
            func.count(AdView.id).label("views"),
            func.sum(AdView.estimated_revenue_usd).label("revenue"),
        )
        .where(AdView.viewed_at >= start_dt, AdView.viewed_at < end_dt)
        .group_by(func.date(AdView.viewed_at))
        .order_by(func.date(AdView.viewed_at))
    )
    rows = result.all()
    total_views = sum(r.views for r in rows)
    total_revenue = sum(r.revenue or Decimal("0") for r in rows)
    cpm = (total_revenue / total_views * 1000) if total_views > 0 else Decimal("0")
    return {
        "days": [{"date": str(r.day), "views": r.views, "revenue": str(r.revenue or "0")} for r in rows],
        "total_views": total_views,
        "total_revenue": str(total_revenue),
        "cpm": str(cpm.quantize(Decimal("0.0001")) if isinstance(cpm, Decimal) else cpm),
    }


# ── CSV Exports ──────────────────────────────────────────────────────────


@router.get("/api/export/visits")
async def export_visits(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(
        select(Visit, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, Visit.hotspot_id == Hotspot.id, isouter=True)
        .order_by(Visit.visited_at.desc())
        .limit(10000)
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Hotspot", "IP Address", "User Agent", "Visited At"])
    for row in result.all():
        v = row.Visit
        writer.writerow([v.id, v.client_mac, row.hotspot_name, v.ip_address, v.user_agent,
                         v.visited_at.isoformat() if v.visited_at else ""])
    buf.seek(0)
    await record_audit(db, request, "export_visits")
    await db.commit()
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=visits.csv"})


@router.get("/api/export/revenue")
async def export_revenue(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(
        select(AdView, Hotspot.name.label("hotspot_name"))
        .join(Hotspot, AdView.hotspot_id == Hotspot.id, isouter=True)
        .order_by(AdView.viewed_at.desc())
        .limit(10000)
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Hotspot", "Network", "Revenue USD", "Viewed At"])
    for row in result.all():
        a = row.AdView
        writer.writerow([a.id, a.client_mac, row.hotspot_name, a.ad_network,
                         str(a.estimated_revenue_usd), a.viewed_at.isoformat() if a.viewed_at else ""])
    buf.seek(0)
    await record_audit(db, request, "export_revenue")
    await db.commit()
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=revenue.csv"})


@router.get("/api/export/devices")
async def export_blocked_devices(
    request: Request, db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    verify_basic_auth(request)
    result = await db.execute(select(BlockedDevice).order_by(BlockedDevice.blocked_at.desc()))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Client MAC", "Reason", "Blocked By", "Blocked At", "Expires At", "Active"])
    for d in result.scalars().all():
        writer.writerow([d.id, d.client_mac, d.reason, d.blocked_by,
                         d.blocked_at.isoformat() if d.blocked_at else "",
                         d.expires_at.isoformat() if d.expires_at else "", d.is_active])
    buf.seek(0)
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=blocked_devices.csv"})


# ── Settings ─────────────────────────────────────────────────────────────


@router.get("/api/settings", response_model=SystemSettingsResponse)
async def get_settings(request: Request) -> SystemSettingsResponse:
    verify_basic_auth(request)
    return SystemSettingsResponse(
        ad_duration_seconds=settings.ad_duration_seconds,
        session_duration_seconds=settings.session_duration_seconds,
        anti_spam_window_seconds=settings.anti_spam_window_seconds,
        omada_host=settings.omada_host,
        environment=settings.environment,
        app_name=settings.app_name,
    )


@router.patch("/api/settings")
async def update_settings(
    request: Request, body: SystemSettingsUpdate, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    updated: dict[str, Any] = {}
    if body.ad_duration_seconds is not None:
        settings.ad_duration_seconds = body.ad_duration_seconds
        updated["ad_duration_seconds"] = body.ad_duration_seconds
    if body.session_duration_seconds is not None:
        settings.session_duration_seconds = body.session_duration_seconds
        updated["session_duration_seconds"] = body.session_duration_seconds
    if body.anti_spam_window_seconds is not None:
        settings.anti_spam_window_seconds = body.anti_spam_window_seconds
        updated["anti_spam_window_seconds"] = body.anti_spam_window_seconds
    await record_audit(db, request, "update_settings", "settings", None, updated)
    await db.commit()
    return {"status": "updated", "changes": updated}


@router.post("/api/settings/test-omada")
async def test_omada_connection(request: Request) -> dict[str, Any]:
    verify_basic_auth(request)
    try:
        omada = get_omada_client()
        await omada.get_online_clients("Default")
        return {"status": "ok", "message": "Omada connection successful"}
    except (OmadaError, RuntimeError) as exc:
        return {"status": "error", "message": str(exc)}


# ── Hotspot Delete + Detail ──────────────────────────────────────────────


@router.delete("/api/hotspots/{hotspot_id}")
async def delete_hotspot(
    request: Request, hotspot_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    await record_audit(db, request, "delete_hotspot", "hotspot", str(hotspot_id), {"name": hotspot.name})
    await db.delete(hotspot)
    await db.commit()
    return {"status": "deleted"}


@router.get("/api/hotspots/{hotspot_id}/detail")
async def hotspot_detail(
    request: Request, hotspot_id: int, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    verify_basic_auth(request)
    result = await db.execute(select(Hotspot).where(Hotspot.id == hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    visits_today = (await db.execute(
        select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= today_start)
    )).scalar_one() or 0
    visits_week = (await db.execute(
        select(func.count(Visit.id)).where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
    )).scalar_one() or 0
    ads_today = (await db.execute(
        select(func.count(AdView.id)).where(AdView.hotspot_id == hotspot_id, AdView.viewed_at >= today_start)
    )).scalar_one() or 0
    # Top devices
    top_devices = await db.execute(
        select(Visit.client_mac, func.count(Visit.id).label("cnt"))
        .where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
        .group_by(Visit.client_mac)
        .order_by(func.count(Visit.id).desc())
        .limit(10)
    )
    # Daily trend
    daily = await db.execute(
        select(func.date(Visit.visited_at).label("day"), func.count(Visit.id).label("cnt"))
        .where(Visit.hotspot_id == hotspot_id, Visit.visited_at >= week_ago)
        .group_by(func.date(Visit.visited_at))
        .order_by(func.date(Visit.visited_at))
    )
    return {
        "hotspot": HotspotResponse.model_validate(hotspot).model_dump(mode="json"),
        "visits_today": visits_today,
        "visits_week": visits_week,
        "ads_today": ads_today,
        "top_devices": [{"mac": r.client_mac, "count": r.cnt} for r in top_devices.all()],
        "daily_trend": [{"date": str(r.day), "count": r.cnt} for r in daily.all()],
    }
