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
<meta name="viewport" content="width=device-width,initial-scale=1">
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
