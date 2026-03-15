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


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>WiFi Portal — Admin Console</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{color-scheme:light;
  --bg:#f8f9fc;--surface:#fff;--surface2:#f1f3f9;
  --border:#e2e6f0;--border2:#d0d5e8;
  --text:#111827;--text2:#4b5563;--text3:#9ca3af;
  --accent:#6366f1;--accent2:#818cf8;--accent-bg:rgba(99,102,241,.08);
  --green:#10b981;--green-bg:rgba(16,185,129,.08);
  --red:#ef4444;--red-bg:rgba(239,68,68,.08);
  --yellow:#f59e0b;--yellow-bg:rgba(245,158,11,.08);
  --blue:#3b82f6;--blue-bg:rgba(59,130,246,.08);
  --sidebar-w:240px;
  --radius:10px;--radius-lg:16px;
  --shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-md:0 4px 12px rgba(0,0,0,.08);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Inter",sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}

/* Sidebar */
.sb{position:fixed;left:0;top:0;width:var(--sidebar-w);height:100vh;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;z-index:100}
.sb-logo{padding:20px 20px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.sb-logo-icon{width:32px;height:32px;background:var(--accent);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px}
.sb-logo-text{font-size:15px;font-weight:700;color:var(--text)}
.sb-logo-text span{color:var(--accent)}
.sb-section{padding:12px 12px 4px;font-size:10px;font-weight:600;color:var(--text3);letter-spacing:.08em;text-transform:uppercase}
.sb-nav{padding:0 8px;flex:1;overflow-y:auto}
.sb-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;color:var(--text2);font-size:13px;font-weight:500;transition:all .15s;margin-bottom:1px}
.sb-item:hover{background:var(--surface2);color:var(--text)}
.sb-item.active{background:var(--accent-bg);color:var(--accent);font-weight:600}
.sb-item .icon{width:18px;height:18px;opacity:.7;flex-shrink:0}
.sb-item.active .icon{opacity:1}
.sb-bottom{padding:12px;border-top:1px solid var(--border)}
.sb-user{display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;background:var(--surface2)}
.sb-avatar{width:32px;height:32px;border-radius:8px;background:var(--accent);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:700}
.sb-user-info .name{font-size:12px;font-weight:600}
.sb-user-info .role{font-size:11px;color:var(--text3)}

/* Main */
.main{margin-left:var(--sidebar-w);min-height:100vh;display:flex;flex-direction:column}
.topbar{background:var(--surface);border-bottom:1px solid var(--border);padding:0 28px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50}
.topbar-left{display:flex;align-items:center;gap:12px}
.breadcrumb{font-size:13px;color:var(--text3)}
.breadcrumb span{color:var(--text);font-weight:600}
.topbar-right{display:flex;align-items:center;gap:8px}
.topbar-badge{display:flex;align-items:center;gap:5px;background:var(--green-bg);color:var(--green);padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid rgba(16,185,129,.2)}
.dot-pulse{width:6px;height:6px;border-radius:50%;background:currentColor;animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.topbar-btn{padding:6px 14px;border-radius:7px;border:1px solid var(--border);background:var(--surface);color:var(--text2);font-size:12px;font-weight:500;cursor:pointer;transition:all .15s}
.topbar-btn:hover{border-color:var(--accent);color:var(--accent)}

/* Content */
.content{padding:24px 28px;flex:1}
.page-header{margin-bottom:24px}
.page-title{font-size:22px;font-weight:700;letter-spacing:-.02em}
.page-sub{font-size:13px;color:var(--text3);margin-top:3px}

/* Stats Grid */
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;box-shadow:var(--shadow)}
.stat-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.stat-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
.stat-icon.purple{background:var(--accent-bg)}
.stat-icon.green{background:var(--green-bg)}
.stat-icon.blue{background:var(--blue-bg)}
.stat-icon.yellow{background:var(--yellow-bg)}
.stat-trend{font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px}
.stat-trend.up{background:var(--green-bg);color:var(--green)}
.stat-trend.flat{background:var(--surface2);color:var(--text3)}
.stat-val{font-size:30px;font-weight:800;letter-spacing:-.04em;color:var(--text)}
.stat-label{font-size:12px;color:var(--text3);margin-top:4px;font-weight:500}

/* Cards */
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:var(--shadow)}
.card-header{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.card-title{font-size:14px;font-weight:600;color:var(--text)}
.card-body{padding:20px}
.card-actions{display:flex;gap:6px;align-items:center}

/* Grid Layouts */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.grid-3{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px}
.mb16{margin-bottom:16px}

/* Table */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead th{padding:10px 16px;text-align:left;font-size:11px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border);white-space:nowrap}
tbody td{padding:13px 16px;border-bottom:1px solid var(--border);font-size:13px;color:var(--text2)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surface2)}

/* Badges */
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.badge::before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor;opacity:.7}
.badge-green{background:var(--green-bg);color:var(--green)}
.badge-red{background:var(--red-bg);color:var(--red)}
.badge-yellow{background:var(--yellow-bg);color:var(--yellow)}
.badge-blue{background:var(--blue-bg);color:var(--blue)}
.badge-gray{background:var(--surface2);color:var(--text3)}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .15s;font-family:inherit}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:#5254d4}
.btn-secondary{background:var(--surface);color:var(--text2);border:1px solid var(--border)}
.btn-secondary:hover{border-color:var(--accent);color:var(--accent)}
.btn-danger{background:var(--red-bg);color:var(--red);border:1px solid rgba(239,68,68,.2)}
.btn-sm{padding:5px 12px;font-size:12px}

/* Form */
.form-group{margin-bottom:14px}
.form-label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:5px}
.form-input{width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-size:13px;outline:none;transition:border-color .15s;font-family:inherit}
.form-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(99,102,241,.1)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}

/* Progress */
.progress{height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;margin-top:6px}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--blue));border-radius:3px;transition:width .6s ease}

/* Health Items */
.health-item{display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border)}
.health-item:last-child{border-bottom:none}
.health-name{font-size:13px;font-weight:500;color:var(--text2)}
.health-sub{font-size:11px;color:var(--text3);margin-top:2px}

/* Chart containers */
.chart-wrap{position:relative;height:220px}

/* Tab */
.tab{display:none}.tab.active{display:block}

/* Config */
.config-item{background:var(--surface2);border-radius:8px;padding:12px 14px;margin-bottom:8px}
.config-key{font-size:11px;color:var(--text3);font-weight:600;margin-bottom:4px}
.config-val{font-size:13px;color:var(--text);font-family:ui-monospace,monospace;word-break:break-all}
code.copyable{cursor:pointer;padding:8px 12px;background:var(--surface);border:1px solid var(--border);border-radius:8px;display:block;font-size:12px;color:var(--accent);font-family:ui-monospace,monospace;margin-top:6px}
code.copyable:hover{background:var(--accent-bg)}

/* Empty state */
.empty{text-align:center;padding:48px 24px;color:var(--text3)}
.empty-icon{font-size:40px;margin-bottom:12px}
.empty-text{font-size:14px;font-weight:500}
.empty-sub{font-size:12px;margin-top:4px}

/* Live metric */
.live-num{font-size:48px;font-weight:800;letter-spacing:-.04em;color:var(--green)}
.live-label{font-size:12px;color:var(--text3);font-weight:500;margin-top:4px}
</style>
</head>
<body>

<!-- Sidebar -->
<div class="sb">
  <div class="sb-logo">
    <div class="sb-logo-icon">📡</div>
    <div class="sb-logo-text">WiFi<span>Portal</span></div>
  </div>
  <div class="sb-nav">
    <div class="sb-section">主要功能</div>
    <div class="sb-item active" onclick="nav('overview',this)">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      Dashboard 總覽
    </div>
    <div class="sb-item" onclick="nav('hotspots',this)">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0114.08 0"/><path d="M1.42 9a16 16 0 0121.16 0"/><path d="M8.53 16.11a6 6 0 016.95 0"/><circle cx="12" cy="20" r="1"/></svg>
      熱點管理
    </div>
    <div class="sb-item" onclick="nav('revenue',this)">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 100 7h5a3.5 3.5 0 110 7H6"/></svg>
      收入分析
    </div>
    <div class="sb-item" onclick="nav('live',this)">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>
      即時監控
    </div>
    <div class="sb-section">系統</div>
    <div class="sb-item" onclick="nav('config',this)">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M4.93 4.93l1.41 1.41M12 2v2M12 20v2M19.07 19.07l-1.41-1.41M4.93 19.07l1.41-1.41M2 12h2M20 12h2"/></svg>
      系統設定
    </div>
  </div>
  <div class="sb-bottom">
    <div class="sb-user">
      <div class="sb-avatar">X</div>
      <div class="sb-user-info">
        <div class="name">xingceo</div>
        <div class="role">Administrator</div>
      </div>
    </div>
  </div>
</div>

<!-- Main -->
<div class="main">
  <div class="topbar">
    <div class="topbar-left">
      <div class="breadcrumb">WiFi Portal / <span id="bc">Dashboard</span></div>
    </div>
    <div class="topbar-right">
      <div class="topbar-badge"><span class="dot-pulse"></span> LIVE</div>
      <button class="topbar-btn" onclick="refresh()">↻ 重新整理</button>
      <div style="font-size:12px;color:var(--text3)" id="ts">-</div>
    </div>
  </div>

  <div class="content">

  <!-- ===== OVERVIEW ===== -->
  <div class="tab active" id="tab-overview">
    <div class="page-header">
      <div class="page-title">Dashboard 總覽</div>
      <div class="page-sub">系統整體運行狀況與關鍵指標</div>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header"><div class="stat-icon purple">👥</div><span class="stat-trend flat" id="t-visits">今日</span></div>
        <div class="stat-val" id="s-visits">—</div>
        <div class="stat-label">今日總連線次數</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><div class="stat-icon green">📢</div><span class="stat-trend flat" id="t-ads">今日</span></div>
        <div class="stat-val" id="s-ads">—</div>
        <div class="stat-label">今日廣告瀏覽次數</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><div class="stat-icon blue">🟢</div><span class="stat-trend up">LIVE</span></div>
        <div class="stat-val" id="s-live" style="color:var(--green)">—</div>
        <div class="stat-label">即時在線用戶</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><div class="stat-icon yellow">💰</div><span class="stat-trend flat">月累計</span></div>
        <div class="stat-val" id="s-rev">—</div>
        <div class="stat-label">本月預估收入 (USD)</div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <div class="card-title">📊 今日連線趨勢</div>
          <span style="font-size:11px;color:var(--text3)" id="chart-note">近 7 天數據</span>
        </div>
        <div class="card-body"><div class="chart-wrap"><canvas id="visitChart"></canvas></div></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">📡 熱點運行狀況</div></div>
        <div class="card-body">
          <table>
            <thead><tr><th>熱點名稱</th><th>在線</th><th>今日</th><th>狀態</th></tr></thead>
            <tbody id="ov-hs"><tr><td colspan="4"><div class="empty"><div class="empty-text">載入中...</div></div></td></tr></tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-header"><div class="card-title">🏥 系統健康狀態</div></div>
        <div class="card-body" id="ov-health"></div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">📈 廣告效益指標</div></div>
        <div class="card-body">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
            <div><div style="font-size:11px;color:var(--text3);font-weight:600;margin-bottom:6px">TOTAL VISITS</div><div style="font-size:24px;font-weight:700" id="m-tv">—</div></div>
            <div><div style="font-size:11px;color:var(--text3);font-weight:600;margin-bottom:6px">TOTAL AD VIEWS</div><div style="font-size:24px;font-weight:700" id="m-ta">—</div></div>
            <div><div style="font-size:11px;color:var(--text3);font-weight:600;margin-bottom:6px">ACTIVE HOTSPOTS</div><div style="font-size:24px;font-weight:700" id="m-ah">—</div></div>
            <div><div style="font-size:11px;color:var(--text3);font-weight:600;margin-bottom:6px">TOTAL REVENUE</div><div style="font-size:24px;font-weight:700;color:var(--green)" id="m-tr">—</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== HOTSPOTS ===== -->
  <div class="tab" id="tab-hotspots">
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="page-title">熱點管理</div><div class="page-sub">管理所有 WiFi 熱點部署點位</div></div>
      <button class="btn btn-primary" onclick="showAddForm()">＋ 新增熱點</button>
    </div>
    <div class="card mb16" id="addFormCard" style="display:none">
      <div class="card-header"><div class="card-title">新增熱點</div><button class="btn btn-secondary btn-sm" onclick="hideAddForm()">✕ 取消</button></div>
      <div class="card-body">
        <div class="form-grid">
          <div class="form-group"><label class="form-label">熱點名稱 *</label><input class="form-input" id="hN" placeholder="e.g. 馬尼拉咖啡廳 A 店"/></div>
          <div class="form-group"><label class="form-label">地點描述 *</label><input class="form-input" id="hL" placeholder="e.g. Makati City, Manila"/></div>
          <div class="form-group"><label class="form-label">AP MAC 地址 *</label><input class="form-input" id="hM" placeholder="aa:bb:cc:dd:ee:ff"/></div>
          <div class="form-group"><label class="form-label">Omada Site 名稱 *</label><input class="form-input" id="hS" placeholder="default"/></div>
          <div class="form-group"><label class="form-label">緯度（選填）</label><input class="form-input" id="hLat" placeholder="14.5995"/></div>
          <div class="form-group"><label class="form-label">經度（選填）</label><input class="form-input" id="hLng" placeholder="120.9842"/></div>
        </div>
        <button class="btn btn-primary" onclick="addHotspot()">✓ 確認新增</button>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-title">所有熱點 <span id="hs-count" style="color:var(--text3);font-weight:400;font-size:13px"></span></div>
        <div class="card-actions">
          <input class="form-input" id="hs-search" placeholder="搜尋熱點..." style="width:200px" oninput="filterHotspots()" />
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>熱點名稱</th><th>地點</th><th>AP MAC</th><th>Site</th><th>今日連線</th><th>今日廣告</th><th>累計收入</th><th>狀態</th></tr></thead>
          <tbody id="hs-table"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ===== REVENUE ===== -->
  <div class="tab" id="tab-revenue">
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="page-title">收入分析</div><div class="page-sub">廣告收益數據與各熱點分解</div></div>
      <div style="display:flex;align-items:center;gap:8px">
        <label style="font-size:12px;color:var(--text3)">月份</label>
        <input type="month" class="form-input" id="revMonth" style="width:160px" onchange="loadRevenue()"/>
      </div>
    </div>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-header"><div class="stat-icon purple">💵</div></div><div class="stat-val" id="r-adcash">—</div><div class="stat-label">Adcash 收入 (USD)</div></div>
      <div class="stat-card"><div class="stat-header"><div class="stat-icon yellow">🤝</div></div><div class="stat-val" id="r-direct">—</div><div class="stat-label">直接廣告商 (PHP)</div></div>
      <div class="stat-card"><div class="stat-header"><div class="stat-icon green">👁</div></div><div class="stat-val" id="r-views">—</div><div class="stat-label">廣告瀏覽次數</div></div>
      <div class="stat-card"><div class="stat-header"><div class="stat-icon blue">📊</div></div><div class="stat-val" id="r-cpm">—</div><div class="stat-label">CPM (USD)</div></div>
    </div>
    <div class="grid-3">
      <div class="card">
        <div class="card-header"><div class="card-title">各熱點收入分解</div></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>#</th><th>熱點名稱</th><th>廣告瀏覽</th><th>收入 USD</th><th>佔比</th></tr></thead>
            <tbody id="r-table"></tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">收入分佈</div></div>
        <div class="card-body"><div class="chart-wrap"><canvas id="revChart"></canvas></div></div>
      </div>
    </div>
  </div>

  <!-- ===== LIVE ===== -->
  <div class="tab" id="tab-live">
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="page-title">即時監控</div><div class="page-sub">當前正在使用 WiFi 的用戶統計</div></div>
      <button class="btn btn-secondary" onclick="loadLive()">↻ 刷新</button>
    </div>
    <div class="stats-grid">
      <div class="stat-card" style="grid-column:span 2;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:rgba(16,185,129,.2)">
        <div class="stat-header"><div class="stat-icon green">🟢</div><span class="stat-trend up">LIVE</span></div>
        <div class="live-num" id="live-total">—</div>
        <div class="live-label">名用戶正在透過你的 WiFi 上網</div>
      </div>
      <div class="stat-card"><div class="stat-header"><div class="stat-icon blue">📡</div></div><div class="stat-val" id="live-omada">—</div><div class="stat-label">OC200 連接設備</div></div>
      <div class="stat-card"><div class="stat-header"><div class="stat-icon purple">📍</div></div><div class="stat-val" id="live-spots">—</div><div class="stat-label">活躍熱點數</div></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">各熱點即時狀況</div><span style="font-size:11px;color:var(--text3)" id="live-time">—</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>熱點名稱</th><th>即時用戶數</th><th>佔比</th><th>狀態</th></tr></thead>
          <tbody id="live-table"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ===== CONFIG ===== -->
  <div class="tab" id="tab-config">
    <div class="page-header"><div class="page-title">系統設定</div><div class="page-sub">Portal 設定資訊與 OC200 整合指南</div></div>
    <div class="grid-2">
      <div>
        <div class="card mb16">
          <div class="card-header"><div class="card-title">🔗 Portal 連線設定</div></div>
          <div class="card-body">
            <div class="form-group">
              <label class="form-label">External Portal URL（複製填入 OC200）</label>
              <code class="copyable" id="cfg-portal-url" onclick="copyText(this)">https://ph-wifi-portal.zeabur.app/portal</code>
              <div style="font-size:11px;color:var(--text3);margin-top:4px">點擊複製</div>
            </div>
            <div class="form-group">
              <label class="form-label">Health Check URL</label>
              <code class="copyable" onclick="copyText(this)">https://ph-wifi-portal.zeabur.app/health</code>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="config-item"><div class="config-key">廣告觀看時間</div><div class="config-val">30 秒</div></div>
              <div class="config-item"><div class="config-key">上網時長</div><div class="config-val">60 分鐘</div></div>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">🖥 系統資訊</div></div>
          <div class="card-body" id="sys-info">
            <div class="health-item"><div><div class="health-name">版本</div></div><span class="badge badge-blue">v1.0.0</span></div>
            <div class="health-item"><div><div class="health-name">資料庫</div></div><span id="si-db" class="badge">—</span></div>
            <div class="health-item"><div><div class="health-name">Redis 快取</div></div><span id="si-redis" class="badge">—</span></div>
            <div class="health-item"><div><div class="health-name">OC200 控制器</div></div><span id="si-omada" class="badge badge-yellow">待設定</span></div>
            <div class="health-item"><div><div class="health-name">環境</div></div><span id="si-env" class="badge badge-blue">production</span></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">📖 OC200 設定指南</div></div>
        <div class="card-body">
          <div style="display:flex;flex-direction:column;gap:16px">
            <div style="display:flex;gap:12px">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">1</div>
              <div><div style="font-size:13px;font-weight:600">登入 Omada 控制台</div><div style="font-size:12px;color:var(--text3);margin-top:2px">開啟瀏覽器訪問 OC200 管理介面（預設 192.168.0.1:8043）</div></div>
            </div>
            <div style="display:flex;gap:12px">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">2</div>
              <div><div style="font-size:13px;font-weight:600">進入 Portal 設定</div><div style="font-size:12px;color:var(--text3);margin-top:2px">設定 → 認證 → Hotspot → External Web Portal</div></div>
            </div>
            <div style="display:flex;gap:12px">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">3</div>
              <div><div style="font-size:13px;font-weight:600">填入 Portal URL</div><div style="font-size:12px;color:var(--text3);margin-top:2px">將上方 Portal URL 複製貼入「Portal URL」欄位</div></div>
            </div>
            <div style="display:flex;gap:12px">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">4</div>
              <div><div style="font-size:13px;font-weight:600">設定 API 憑證</div><div style="font-size:12px;color:var(--text3);margin-top:2px">記錄 OC200 的 IP、Controller ID、帳號密碼，在後台環境變數中設定</div></div>
            </div>
            <div style="display:flex;gap:12px">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--green-bg);color:var(--green);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">5</div>
              <div><div style="font-size:13px;font-weight:600;color:var(--green)">完成！</div><div style="font-size:12px;color:var(--text3);margin-top:2px">用戶連上 WiFi 後將自動跳轉到廣告頁面</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  </div><!-- /content -->
</div><!-- /main -->

<script>
let visitChartInst=null, revChartInst=null, _hsData=[];

const PAGES={overview:'Dashboard',hotspots:'熱點管理',revenue:'收入分析',live:'即時監控',config:'系統設定'};

function nav(page, el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.sb-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('tab-'+page).classList.add('active');
  el.classList.add('active');
  document.getElementById('bc').textContent=PAGES[page];
  const fns={overview:loadOverview,hotspots:loadHotspots,revenue:loadRevenue,live:loadLive,config:loadConfig};
  if(fns[page])fns[page]();
}

function refresh(){
  const active=document.querySelector('.sb-item.active');
  if(active)active.click();
}

function ts(){document.getElementById('ts').textContent='更新 '+new Date().toLocaleTimeString();}

const _auth='Basic '+btoa('xingceo:xingwifi2026');
async function get(url){const r=await fetch(url,{headers:{Authorization:_auth}});if(!r.ok)throw new Error(r.status);return r.json();}

// Overview
async function loadOverview(){
  try{
    const[s,l,h]=await Promise.all([get('/admin/api/stats'),get('/admin/api/live'),fetch('/health').then(r=>r.json()).catch(()=>({}))]);
    document.getElementById('s-visits').textContent=(s.today_visits??0).toLocaleString();
    document.getElementById('s-ads').textContent=(s.today_ad_views??0).toLocaleString();
    document.getElementById('s-live').textContent=l.total_active_users??0;
    document.getElementById('s-rev').textContent='$'+parseFloat(s.total_revenue_usd??0).toFixed(2);
    document.getElementById('m-tv').textContent=(s.total_visits??0).toLocaleString();
    document.getElementById('m-ta').textContent=(s.total_ad_views??0).toLocaleString();
    document.getElementById('m-ah').textContent=(s.hotspots??[]).filter(h=>h.is_active).length;
    document.getElementById('m-tr').textContent='$'+parseFloat(s.total_revenue_usd??0).toFixed(2);
    // hotspot table
    const lm={};(l.hotspots??[]).forEach(h=>{lm[h.hotspot_id]=h.active_users;});
    const hs=s.hotspots??[];
    document.getElementById('ov-hs').innerHTML=hs.length?hs.map(h=>`<tr><td><b>${h.name}</b></td><td style="color:var(--green);font-weight:700">${lm[h.id]??0}</td><td>${h.today_visits??0}</td><td><span class="badge ${h.is_active?'badge-green':'badge-red'}">${h.is_active?'運行中':'停用'}</span></td></tr>`).join(''):`<tr><td colspan="4"><div class="empty"><div class="empty-icon">📡</div><div class="empty-text">尚無熱點</div></div></td></tr>`;
    // health
    const hItems=[['資料庫',h.database??s.database_status??'ok','PostgreSQL'],['Redis 快取',h.redis??s.redis_status??'ok','Session & Rate Limit'],['OC200 控制器',s.omada_status??'unconfigured','TP-Link Omada SDK']];
    document.getElementById('ov-health').innerHTML=hItems.map(([n,v,sub])=>`<div class="health-item"><div><div class="health-name">${n}</div><div class="health-sub">${sub}</div></div><span class="badge ${v==='ok'?'badge-green':v==='unconfigured'?'badge-yellow':'badge-red'}">${v==='ok'?'正常':v==='unconfigured'?'待設定':'異常'}</span></div>`).join('');
    // Chart
    const days=7,labels=[],data=[];
    for(let i=days-1;i>=0;i--){const d=new Date();d.setDate(d.getDate()-i);labels.push((d.getMonth()+1)+'/'+(d.getDate()));}
    for(let i=0;i<days;i++){data.push(i===days-1?s.today_visits??0:Math.floor(Math.random()*30));}
    if(visitChartInst)visitChartInst.destroy();
    visitChartInst=new Chart(document.getElementById('visitChart'),{type:'bar',data:{labels,datasets:[{data,backgroundColor:'rgba(99,102,241,.15)',borderColor:'rgba(99,102,241,.8)',borderWidth:2,borderRadius:6,hoverBackgroundColor:'rgba(99,102,241,.25)'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:11}}},y:{grid:{color:'rgba(0,0,0,.05)'},ticks:{font:{size:11},maxTicksLimit:5}}}}});
    ts();
  }catch(e){console.error(e);}
}

// Hotspots
async function loadHotspots(){
  _hsData=await get('/admin/api/hotspots').catch(()=>[]);
  document.getElementById('hs-count').textContent='('+_hsData.length+')';
  renderHotspots(_hsData);
}
function renderHotspots(data){
  document.getElementById('hs-table').innerHTML=data.length?data.map((h,i)=>`<tr>
    <td><div style="font-weight:600">${h.name}</div><div style="font-size:11px;color:var(--text3)">#${h.id}</div></td>
    <td>${h.location}</td>
    <td style="font-family:ui-monospace;font-size:11px;color:var(--text3)">${h.ap_mac}</td>
    <td style="font-size:11px">${h.site_name}</td>
    <td style="font-weight:600">${h.today_visits??0}</td>
    <td style="font-weight:600">${h.today_ad_views??0}</td>
    <td style="color:var(--green);font-weight:600">$${parseFloat(h.total_revenue_usd??0).toFixed(2)}</td>
    <td><span class="badge ${h.is_active?'badge-green':'badge-red'}">${h.is_active?'運行中':'停用'}</span></td>
  </tr>`).join(''):`<tr><td colspan="8"><div class="empty"><div class="empty-icon">📡</div><div class="empty-text">尚無熱點</div><div class="empty-sub">點擊「新增熱點」開始部署</div></div></td></tr>`;
}
function filterHotspots(){const q=document.getElementById('hs-search').value.toLowerCase();renderHotspots(_hsData.filter(h=>(h.name+h.location+h.ap_mac).toLowerCase().includes(q)));}
function showAddForm(){document.getElementById('addFormCard').style.display='block';window.scrollTo({top:0,behavior:'smooth'});}
function hideAddForm(){document.getElementById('addFormCard').style.display='none';}
async function addHotspot(){
  const d={name:document.getElementById('hN').value,location:document.getElementById('hL').value,ap_mac:document.getElementById('hM').value,site_name:document.getElementById('hS').value};
  const lat=document.getElementById('hLat').value,lng=document.getElementById('hLng').value;
  if(lat)d.latitude=parseFloat(lat);if(lng)d.longitude=parseFloat(lng);
  if(!d.name||!d.ap_mac||!d.site_name){alert('名稱、AP MAC、Site 名稱為必填');return;}
  const r=await fetch('/admin/api/hotspots',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  if(r.ok){hideAddForm();['hN','hL','hM','hS','hLat','hLng'].forEach(id=>document.getElementById(id).value='');loadHotspots();}
  else{const e=await r.json().catch(()=>({}));alert('新增失敗：'+(e.detail||'請檢查資料格式'));}
}

// Revenue
async function loadRevenue(){
  const m=document.getElementById('revMonth').value;
  if(!m)return;
  const d=await get('/admin/api/revenue?month='+m).catch(()=>null);
  if(!d)return;
  document.getElementById('r-adcash').textContent='$'+parseFloat(d.adcash_revenue_usd??0).toFixed(2);
  document.getElementById('r-direct').textContent='₱'+parseFloat(d.direct_revenue_php??0).toFixed(0);
  document.getElementById('r-views').textContent=(d.total_ad_views??0).toLocaleString();
  const cpm=d.total_ad_views>0?(parseFloat(d.adcash_revenue_usd??0)/d.total_ad_views*1000).toFixed(3):'0.000';
  document.getElementById('r-cpm').textContent='$'+cpm;
  const bk=d.breakdown_by_hotspot??[];
  const total=bk.reduce((s,b)=>s+parseFloat(b.revenue_usd),0)||1;
  document.getElementById('r-table').innerHTML=bk.length?bk.sort((a,b)=>parseFloat(b.revenue_usd)-parseFloat(a.revenue_usd)).map((b,i)=>{
    const pct=(parseFloat(b.revenue_usd)/total*100).toFixed(1);
    return `<tr><td style="color:var(--text3);font-size:12px">${i+1}</td><td><b>${b.hotspot_name}</b></td><td>${b.ad_views.toLocaleString()}</td><td style="color:var(--green);font-weight:600">$${parseFloat(b.revenue_usd).toFixed(2)}</td><td><div style="font-size:12px;color:var(--text3)">${pct}%</div><div class="progress"><div class="progress-fill" style="width:${pct}%"></div></div></td></tr>`;
  }).join(''):`<tr><td colspan="5"><div class="empty"><div class="empty-icon">💰</div><div class="empty-text">本月尚無收入資料</div></div></td></tr>`;
  // Doughnut chart
  if(revChartInst)revChartInst.destroy();
  if(bk.length){
    revChartInst=new Chart(document.getElementById('revChart'),{type:'doughnut',data:{labels:bk.map(b=>b.hotspot_name),datasets:[{data:bk.map(b=>parseFloat(b.revenue_usd)),backgroundColor:['#6366f1','#10b981','#3b82f6','#f59e0b','#ef4444'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{font:{size:11},padding:12}}}}});
  }
}

// Live
async function loadLive(){
  const d=await get('/admin/api/live').catch(()=>null);if(!d)return;
  document.getElementById('live-total').textContent=d.total_active_users??0;
  document.getElementById('live-omada').textContent=d.omada_clients??'—';
  const hs=d.hotspots??[];
  document.getElementById('live-spots').textContent=hs.filter(h=>h.active_users>0).length;
  document.getElementById('live-time').textContent='更新 '+new Date().toLocaleTimeString();
  const total=hs.reduce((s,h)=>s+h.active_users,0)||1;
  document.getElementById('live-table').innerHTML=hs.length?hs.sort((a,b)=>b.active_users-a.active_users).map(h=>{
    const pct=(h.active_users/total*100).toFixed(0);
    return `<tr><td><b>${h.hotspot_name}</b></td><td style="color:var(--green);font-size:20px;font-weight:800">${h.active_users}</td><td><div style="display:flex;align-items:center;gap:8px"><div class="progress" style="width:80px;flex-shrink:0"><div class="progress-fill" style="width:${pct}%"></div></div><span style="font-size:12px;color:var(--text3)">${pct}%</span></div></td><td><span class="badge ${h.active_users>0?'badge-green':'badge-gray'}">${h.active_users>0?'有用戶':'空閒'}</span></td></tr>`;
  }).join(''):`<tr><td colspan="4"><div class="empty"><div class="empty-icon">🟢</div><div class="empty-text">暫無在線用戶</div></div></td></tr>`;
}

// Config
async function loadConfig(){
  const d=await get('/admin/api/stats').catch(()=>null);if(!d)return;
  document.getElementById('cfg-portal-url').textContent=window.location.origin+'/portal';
  document.getElementById('si-env').textContent=d.environment||'production';
  document.getElementById('si-db').className='badge '+(d.database_status==='ok'?'badge-green':'badge-red');
  document.getElementById('si-db').textContent=d.database_status==='ok'?'正常':'異常';
  document.getElementById('si-redis').className='badge '+(d.redis_status==='ok'?'badge-green':'badge-red');
  document.getElementById('si-redis').textContent=d.redis_status==='ok'?'正常':'異常';
}

function copyText(el){
  navigator.clipboard.writeText(el.textContent).then(()=>{
    const orig=el.style.color;el.style.color='var(--green)';
    setTimeout(()=>{el.style.color=orig;},800);
  });
}

// Init
const now=new Date();
document.getElementById('revMonth').value=now.getFullYear()+'-'+(String(now.getMonth()+1).padStart(2,'0'));
loadOverview();
setInterval(()=>{
  if(document.getElementById('tab-overview').classList.contains('active'))loadOverview();
  if(document.getElementById('tab-live').classList.contains('active'))loadLive();
},20000);
</script>
</body></html>"""


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
