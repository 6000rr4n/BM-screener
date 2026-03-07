"""Dashboard generator: single-file HTML with inline CSS + JS, dark theme."""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_dashboard(signals: list[dict[str, Any]], scan_info: dict[str, Any]) -> str:
    """Generate a single-file HTML dashboard with embedded data.

    Args:
        signals: List of signal dicts from the scanner.
        scan_info: Dict with total_tickers, scan_time, mode, use_ema_filter.

    Returns:
        Complete HTML string.
    """
    scan_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    total_tickers = scan_info.get("total_tickers", 0)
    scan_duration = scan_info.get("scan_time", 0)
    mode = scan_info.get("mode", "Aggressive")
    use_ema = scan_info.get("use_ema_filter", False)

    # Stats
    total_signals = len(signals)
    breakout_count = sum(1 for s in signals if s["signal_type"] == "BREAKOUT")
    meanrev_count = sum(1 for s in signals if s["signal_type"] == "MEAN_REV")
    bullish_count = sum(1 for s in signals if s["signal_direction"] == "BULLISH")
    bearish_count = sum(1 for s in signals if s["signal_direction"] == "BEARISH")

    # Serialize signals for JS (handle NaN/None)
    signals_json = json.dumps(signals, default=str)

    from scanner import config as _cfg
    github_repo = _cfg.GITHUB_REPO

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock Scanner</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: system-ui, -apple-system, sans-serif;
    background: #0f172a; color: #f1f5f9;
    min-height: 100vh;
}}
.header {{
    background: #1e293b; border-bottom: 1px solid #334155;
    padding: 16px 24px; display: flex; align-items: center;
    justify-content: space-between; flex-wrap: wrap; gap: 12px;
}}
.header-left h1 {{ font-size: 20px; font-weight: 700; }}
.header-left .meta {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
.header-right {{ display: flex; gap: 8px; align-items: center; }}
.btn {{
    padding: 8px 16px; border-radius: 6px; border: 1px solid #334155;
    background: #1e293b; color: #f1f5f9; cursor: pointer;
    font-size: 13px; transition: all 0.15s;
}}
.btn:hover {{ background: #334155; }}
.btn-primary {{ background: #3b82f6; border-color: #3b82f6; }}
.btn-primary:hover {{ background: #2563eb; }}
.status-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block; margin-right: 4px;
}}
.status-green {{ background: #22c55e; }}
.status-red {{ background: #ef4444; }}
.controls {{
    background: #1e293b; border-bottom: 1px solid #334155;
    padding: 12px 24px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
}}
.control-group {{ display: flex; gap: 4px; align-items: center; }}
.control-group label {{
    font-size: 11px; color: #94a3b8; text-transform: uppercase;
    letter-spacing: 0.5px; margin-right: 6px;
}}
.toggle-btn {{
    padding: 5px 12px; border-radius: 4px; border: 1px solid #334155;
    background: transparent; color: #94a3b8; cursor: pointer;
    font-size: 12px; transition: all 0.15s;
}}
.toggle-btn.active {{ background: #3b82f6; color: #fff; border-color: #3b82f6; }}
select {{
    padding: 5px 10px; border-radius: 4px; border: 1px solid #334155;
    background: #0f172a; color: #f1f5f9; font-size: 12px;
}}
.single-scan {{
    display: flex; gap: 4px; margin-left: auto;
}}
.single-scan input {{
    padding: 5px 10px; border-radius: 4px; border: 1px solid #334155;
    background: #0f172a; color: #f1f5f9; font-size: 12px; width: 100px;
}}
.stats {{
    display: flex; gap: 12px; padding: 16px 24px; flex-wrap: wrap;
}}
.stat-card {{
    background: #1e293b; border: 1px solid #334155; border-radius: 8px;
    padding: 12px 20px; flex: 1; min-width: 120px; text-align: center;
}}
.stat-card .value {{ font-size: 24px; font-weight: 700; }}
.stat-card .label {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
.table-container {{
    padding: 0 24px 24px; overflow-x: auto;
}}
table {{
    width: 100%; border-collapse: collapse; font-size: 12px;
}}
thead th {{
    background: #1e293b; color: #94a3b8; text-align: left;
    padding: 10px 8px; border-bottom: 2px solid #334155;
    cursor: pointer; user-select: none; white-space: nowrap;
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px;
}}
thead th:hover {{ color: #f1f5f9; }}
thead th .sort-arrow {{ margin-left: 4px; opacity: 0.5; }}
tbody td {{
    padding: 8px; border-bottom: 1px solid #1e293b;
    vertical-align: top;
}}
tbody tr:hover {{ background: #1e293b; }}
.ticker-link {{
    color: #3b82f6; text-decoration: none; font-weight: 600;
}}
.ticker-link:hover {{ color: #60a5fa; text-decoration: underline; }}
.signal-bull-break {{ color: #22c55e; font-weight: 700; font-size: 13px; }}
.signal-bear-break {{ color: #ef4444; font-weight: 700; font-size: 13px; }}
.signal-bull-mr {{ color: #4ade80; font-weight: 500; font-size: 12px; }}
.signal-bear-mr {{ color: #f87171; font-weight: 500; font-size: 12px; }}
.regime-badge {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 10px; margin-top: 2px;
}}
.regime-squeeze {{ background: #1e3a5f; color: #60a5fa; }}
.regime-expansion {{ background: #3b1f1f; color: #f87171; }}
.regime-neutral {{ background: #1e293b; color: #94a3b8; }}
.stock-buy {{ color: #22c55e; font-weight: 700; }}
.stock-sell {{ color: #ef4444; font-weight: 700; }}
.score-bar {{
    width: 60px; height: 6px; background: #334155; border-radius: 3px;
    overflow: hidden; display: inline-block; vertical-align: middle;
}}
.score-fill {{ height: 100%; border-radius: 3px; }}
.score-green {{ background: #22c55e; }}
.score-yellow {{ background: #eab308; }}
.score-red {{ background: #ef4444; }}
.rsi-high {{ color: #ef4444; }}
.rsi-low {{ color: #22c55e; }}
.iv-low {{ color: #22c55e; }}
.iv-mid {{ color: #eab308; }}
.iv-high {{ color: #ef4444; }}
.weekly-bull {{ color: #22c55e; }}
.weekly-bear {{ color: #ef4444; }}
.weekly-neutral {{ color: #94a3b8; }}
.ttm-squeeze {{ color: #3b82f6; }}
.ttm-fired {{ color: #f97316; font-weight: 700; }}
.ttm-off {{ color: #475569; }}
.confirm-yes {{ color: #22c55e; font-weight: 700; font-size: 13px; }}
.confirm-no {{ color: #ef4444; font-weight: 700; font-size: 13px; }}
.confirm-detail {{ font-size: 10px; color: #94a3b8; }}
.pattern-tag {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    background: #334155; color: #94a3b8; font-size: 10px;
    margin: 1px;
}}
canvas.sparkline {{ display: block; }}
.sub-text {{ font-size: 10px; color: #94a3b8; }}
.toast {{
    position: fixed; bottom: 24px; right: 24px;
    background: #ef4444; color: #fff; padding: 12px 20px;
    border-radius: 8px; font-size: 13px; display: none;
    z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}}
.toast.show {{ display: block; }}

/* ── Card Layout (mobile) ─────────────────────────────────────────── */
.card-container {{
    display: none;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
}}
.signal-card {{
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 16px; transition: border-color 0.15s;
}}
.signal-card:active {{ border-color: #3b82f6; }}
.card-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
}}
.card-ticker {{
    font-size: 18px; font-weight: 700;
}}
.card-ticker a {{ color: #3b82f6; text-decoration: none; }}
.card-price {{ font-size: 16px; font-weight: 600; color: #f1f5f9; }}
.card-signal {{
    margin: 8px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}}
.card-metrics {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px;
    font-size: 13px; margin-top: 8px;
}}
.card-metrics .metric-label {{ color: #64748b; font-size: 11px; }}
.card-metrics .metric-value {{ color: #e2e8f0; font-weight: 500; }}
.card-details {{
    display: none; margin-top: 12px; border-top: 1px solid #334155;
    padding-top: 12px;
}}
.signal-card.expanded .card-details {{ display: block; }}
.card-expand-btn {{
    background: none; border: none; color: #64748b; font-size: 12px;
    cursor: pointer; padding: 8px 0; width: 100%; text-align: center;
    margin-top: 4px;
}}
.card-expand-btn:active {{ color: #3b82f6; }}
.card-detail-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px;
    font-size: 13px;
}}

/* ── Mobile Responsive ────────────────────────────────────────────── */
@media (max-width: 768px) {{
    .table-container {{ display: none; }}
    .card-container {{ display: flex; }}
    .header {{
        flex-direction: column; align-items: flex-start;
        padding: 12px 16px;
    }}
    .header-right {{
        width: 100%; display: flex; flex-wrap: wrap; gap: 6px;
    }}
    .header-right .btn {{
        min-height: 44px; flex: 1; min-width: 0;
        display: flex; align-items: center; justify-content: center;
    }}
    .controls {{
        padding: 10px 16px; gap: 8px;
        flex-direction: column; align-items: stretch;
    }}
    .control-group {{
        flex-wrap: wrap;
    }}
    .toggle-btn {{
        min-height: 44px; padding: 8px 14px; font-size: 13px;
    }}
    select {{
        min-height: 44px; font-size: 14px; padding: 8px 12px;
    }}
    .single-scan {{
        margin-left: 0; width: 100%;
    }}
    .single-scan input {{
        flex: 1; min-height: 44px; font-size: 14px;
    }}
    .single-scan .btn {{
        min-height: 44px;
    }}
    .stats {{
        padding: 12px 16px; gap: 8px;
    }}
    .stat-card {{
        flex: 1 1 calc(50% - 4px); min-width: 0;
        padding: 10px 12px;
    }}
    .stat-card .value {{ font-size: 20px; }}
    .stat-card .label {{ font-size: 10px; }}
    .toast {{
        left: 16px; right: 16px; bottom: 16px;
        text-align: center;
    }}
    .server-only {{ display: none !important; }}
}}
</style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <h1>Stock Scanner</h1>
        <div class="meta">
            {scan_time} &middot; {total_tickers} tickers scanned &middot;
            {total_signals} signals &middot; {scan_duration}s
        </div>
    </div>
    <div class="header-right">
        <span id="serverStatus" class="server-only"><span class="status-dot status-red"></span>Offline</span>
        <button class="btn server-only" onclick="downloadExcel()">Excel Download</button>
        <button class="btn server-only" onclick="runNewScan()">Novi Scan</button>
        <button class="btn btn-primary" onclick="triggerGitHubScan()">&#9729; Cloud Scan</button>
    </div>
</div>

<div class="controls">
    <div class="control-group">
        <label>Liste:</label>
        <button class="toggle-btn active" data-list="sp500" onclick="toggleList(this)">S&P 500</button>
        <button class="toggle-btn active" data-list="nasdaq" onclick="toggleList(this)">Nasdaq 100</button>
        <button class="toggle-btn active" data-list="dow" onclick="toggleList(this)">Dow 30</button>
        <button class="toggle-btn active" data-list="custom" onclick="toggleList(this)">Custom</button>
    </div>
    <div class="control-group">
        <label>Mode:</label>
        <select id="modeSelect">
            <option value="Aggressive" {"selected" if mode == "Aggressive" else ""}>Aggressive</option>
            <option value="Normal" {"selected" if mode == "Normal" else ""}>Normal</option>
        </select>
    </div>
    <div class="control-group">
        <label>EMA Filter:</label>
        <select id="emaSelect">
            <option value="false" {"selected" if not use_ema else ""}>Isključen</option>
            <option value="true" {"selected" if use_ema else ""}>Uključen</option>
        </select>
    </div>
    <div class="control-group">
        <label>Signal:</label>
        <button class="toggle-btn active" data-filter="all" onclick="setSignalFilter(this)">Svi</button>
        <button class="toggle-btn" data-filter="BREAKOUT" onclick="setSignalFilter(this)">Breakout</button>
        <button class="toggle-btn" data-filter="MEAN_REV" onclick="setSignalFilter(this)">Mean Rev</button>
    </div>
    <div class="control-group">
        <label>Smjer:</label>
        <button class="toggle-btn active" data-dir="all" onclick="setDirFilter(this)">Svi</button>
        <button class="toggle-btn" data-dir="BULLISH" onclick="setDirFilter(this)">Bullish</button>
        <button class="toggle-btn" data-dir="BEARISH" onclick="setDirFilter(this)">Bearish</button>
    </div>
    <div class="single-scan">
        <input type="text" id="singleTicker" placeholder="AAPL" />
        <button class="btn" onclick="scanSingle()">Scan</button>
    </div>
</div>

<div class="stats">
    <div class="stat-card"><div class="value" id="statTotal">{total_signals}</div><div class="label">Ukupno</div></div>
    <div class="stat-card"><div class="value" style="color:#3b82f6" id="statBreakout">{breakout_count}</div><div class="label">Breakout</div></div>
    <div class="stat-card"><div class="value" style="color:#a855f7" id="statMeanrev">{meanrev_count}</div><div class="label">Mean Rev</div></div>
    <div class="stat-card"><div class="value" style="color:#22c55e" id="statBullish">{bullish_count}</div><div class="label">Bullish</div></div>
    <div class="stat-card"><div class="value" style="color:#ef4444" id="statBearish">{bearish_count}</div><div class="label">Bearish</div></div>
</div>

<div class="table-container">
<table id="signalTable">
<thead>
<tr>
    <th onclick="sortTable(0)">Ticker <span class="sort-arrow"></span></th>
    <th onclick="sortTable(1)">Cijena <span class="sort-arrow"></span></th>
    <th>Signal</th>
    <th>Dionička str.</th>
    <th>Opcijska str.</th>
    <th onclick="sortTable(5,'num')">Score <span class="sort-arrow"></span></th>
    <th onclick="sortTable(6,'num')">RSI <span class="sort-arrow"></span></th>
    <th onclick="sortTable(7,'num')">BBW% <span class="sort-arrow"></span></th>
    <th onclick="sortTable(8,'num')">ATR% <span class="sort-arrow"></span></th>
    <th onclick="sortTable(9,'num')">IV Rank <span class="sort-arrow"></span></th>
    <th onclick="sortTable(10)">Weekly <span class="sort-arrow"></span></th>
    <th>TTM Squeeze</th>
    <th>Potvrda</th>
    <th>Patterns</th>
    <th>Chart</th>
</tr>
</thead>
<tbody id="signalBody"></tbody>
</table>
</div>

<div class="card-container" id="cardContainer"></div>

<div class="toast" id="toast"></div>

<script>
const SIGNALS = {signals_json};
let currentSignalFilter = 'all';
let currentDirFilter = 'all';
let sortCol = -1;
let sortAsc = true;

function getSignalHTML(s) {{
    let cls, icon, label;
    if (s.signal_type === 'BREAKOUT' && s.signal_direction === 'BULLISH') {{
        cls = 'signal-bull-break'; icon = '&#8593;'; label = 'Bullish Breakout';
    }} else if (s.signal_type === 'BREAKOUT' && s.signal_direction === 'BEARISH') {{
        cls = 'signal-bear-break'; icon = '&#8595;'; label = 'Bearish Breakout';
    }} else if (s.signal_type === 'MEAN_REV' && s.signal_direction === 'BULLISH') {{
        cls = 'signal-bull-mr'; icon = '&#8593;'; label = 'Bull MeanRev';
    }} else {{
        cls = 'signal-bear-mr'; icon = '&#8595;'; label = 'Bear MeanRev';
    }}
    let regimeCls = s.regime === 'SQUEEZE' ? 'regime-squeeze' : s.regime === 'EXPANSION' ? 'regime-expansion' : 'regime-neutral';
    return `<span class="${{cls}}">${{icon}} ${{label}}</span><br><span class="regime-badge ${{regimeCls}}">${{s.regime}}</span>`;
}}

function getScoreHTML(s) {{
    let score = s.score || 0;
    let cls = score >= 65 ? 'score-green' : score >= 45 ? 'score-yellow' : 'score-red';
    let lbl = s.signal_type === 'BREAKOUT' ? 'Squeeze' : 'Expansion';
    return `<div>${{score.toFixed(1)}}</div><div class="score-bar"><div class="score-fill ${{cls}}" style="width:${{score}}%"></div></div><div class="sub-text">${{lbl}}</div>`;
}}

function getRSIHTML(rsi) {{
    if (rsi == null) return '-';
    let cls = rsi > 65 ? 'rsi-high' : rsi < 35 ? 'rsi-low' : '';
    return `<span class="${{cls}}">${{rsi.toFixed(1)}}</span>`;
}}

function getIVRankHTML(rank) {{
    if (rank == null) return '-';
    let cls = rank < 30 ? 'iv-low' : rank > 70 ? 'iv-high' : 'iv-mid';
    return `<span class="${{cls}}">${{rank.toFixed(1)}}</span>`;
}}

function getWeeklyHTML(s) {{
    let cls = s.weekly_trend === 'Bullish' ? 'weekly-bull' : s.weekly_trend === 'Bearish' ? 'weekly-bear' : 'weekly-neutral';
    let arrow = s.weekly_trend === 'Bullish' ? '&#8593;' : s.weekly_trend === 'Bearish' ? '&#8595;' : '&#8594;';
    let rsi = s.weekly_rsi != null ? `<div class="sub-text">RSI ${{s.weekly_rsi.toFixed(1)}}</div>` : '';
    return `<span class="${{cls}}">${{arrow}} ${{s.weekly_trend}}</span>${{rsi}}`;
}}

function getTTMHTML(s) {{
    let statusHTML;
    if (s.ttm_squeeze_on) {{
        statusHTML = '<span class="ttm-squeeze">&#9679; SQUEEZE</span>';
    }} else if (s.ttm_squeeze_off) {{
        statusHTML = '<span class="ttm-fired">&#9679; FIRED!</span>';
    }} else {{
        statusHTML = '<span class="ttm-off">&#9675; OFF</span>';
    }}
    let colorMap = {{lime:'#22c55e',green:'#15803d',red:'#ef4444',maroon:'#7f1d1d',flat:'#475569'}};
    let hColor = colorMap[s.ttm_hist_color] || '#475569';
    let dirArrow = s.ttm_momentum_dir === 'UP' ? '&#8593;' : s.ttm_momentum_dir === 'DOWN' ? '&#8595;' : '&#8594;';
    return `${{statusHTML}}<br><span style="color:${{hColor}}">&#9632;</span> ${{dirArrow}} ${{s.ttm_momentum_dir}}`;
}}

function getConfirmHTML(s) {{
    let main = s.confirmed ? '<span class="confirm-yes">Da</span>' : '<span class="confirm-no">Ne</span>';
    let details = (s.confirm_details || []).map(d => {{
        let color = d.startsWith('✓') ? '#22c55e' : '#ef4444';
        return `<span style="color:${{color}}">${{d}}</span>`;
    }}).join(' &middot; ');
    return `${{main}}<div class="confirm-detail">${{details}}</div>`;
}}

function getPatternsHTML(patterns) {{
    if (!patterns) return '';
    return patterns.split(', ').map(p => `<span class="pattern-tag">${{p}}</span>`).join('');
}}

function renderTable() {{
    let filtered = SIGNALS.filter(s => {{
        if (currentSignalFilter !== 'all' && s.signal_type !== currentSignalFilter) return false;
        if (currentDirFilter !== 'all' && s.signal_direction !== currentDirFilter) return false;
        return true;
    }});

    // Update stats
    document.getElementById('statTotal').textContent = filtered.length;
    document.getElementById('statBreakout').textContent = filtered.filter(s => s.signal_type === 'BREAKOUT').length;
    document.getElementById('statMeanrev').textContent = filtered.filter(s => s.signal_type === 'MEAN_REV').length;
    document.getElementById('statBullish').textContent = filtered.filter(s => s.signal_direction === 'BULLISH').length;
    document.getElementById('statBearish').textContent = filtered.filter(s => s.signal_direction === 'BEARISH').length;

    let tbody = document.getElementById('signalBody');
    tbody.innerHTML = '';

    filtered.forEach((s, idx) => {{
        let tr = document.createElement('tr');
        let stockDir = s.signal_direction === 'BULLISH'
            ? '<span class="stock-buy">&#8593; BUY</span>'
            : '<span class="stock-sell">&#8595; SELL</span>';
        let optStr = `${{s.option_strategy}}<div class="sub-text">${{s.dte_range}}</div>`;

        tr.innerHTML = `
            <td><a class="ticker-link" href="https://www.tradingview.com/chart/?symbol=${{s.ticker}}" target="_blank">${{s.ticker}}</a></td>
            <td>$${{s.last_price.toFixed(2)}}</td>
            <td>${{getSignalHTML(s)}}</td>
            <td>${{stockDir}}</td>
            <td>${{optStr}}</td>
            <td>${{getScoreHTML(s)}}</td>
            <td>${{getRSIHTML(s.rsi)}}</td>
            <td>${{s.bbw_pct != null ? s.bbw_pct.toFixed(1) : '-'}}</td>
            <td>${{s.atr_pct != null ? s.atr_pct.toFixed(2) : '-'}}</td>
            <td>${{getIVRankHTML(s.iv_rank)}}</td>
            <td>${{getWeeklyHTML(s)}}</td>
            <td>${{getTTMHTML(s)}}</td>
            <td>${{getConfirmHTML(s)}}</td>
            <td>${{getPatternsHTML(s.patterns)}}</td>
            <td><canvas class="sparkline" id="spark-${{idx}}" width="80" height="30"></canvas></td>
        `;
        tbody.appendChild(tr);
    }});

    // Draw sparklines
    filtered.forEach((s, idx) => {{
        let canvas = document.getElementById('spark-' + idx);
        if (canvas && s.sparkline && s.sparkline.length > 1) {{
            drawSparkline(canvas, s.sparkline);
        }}
    }});

    // Render cards for mobile
    renderCards(filtered);
}}

function renderCards(filtered) {{
    let container = document.getElementById('cardContainer');
    if (!container) return;
    container.innerHTML = '';

    filtered.forEach((s, idx) => {{
        let dirCls = s.signal_direction === 'BULLISH' ? 'stock-buy' : 'stock-sell';
        let dirLabel = s.signal_direction === 'BULLISH' ? '&#8593; BUY' : '&#8595; SELL';
        let signalHtml = getSignalHTML(s);
        let scoreVal = (s.score || 0).toFixed(1);
        let scoreCls = s.score >= 65 ? 'score-green' : s.score >= 45 ? 'score-yellow' : 'score-red';

        let card = document.createElement('div');
        card.className = 'signal-card';
        card.innerHTML = `
            <div class="card-header">
                <div class="card-ticker">
                    <a href="https://www.tradingview.com/chart/?symbol=${{s.ticker}}" target="_blank">${{s.ticker}}</a>
                    <span class="${{dirCls}}" style="font-size:14px;margin-left:6px">${{dirLabel}}</span>
                </div>
                <div class="card-price">$${{s.last_price.toFixed(2)}}</div>
            </div>
            <div class="card-signal">${{signalHtml}}</div>
            <div style="margin:6px 0">
                <span style="font-weight:600">${{scoreVal}}</span>
                <div class="score-bar" style="width:80px;margin-left:8px">
                    <div class="score-fill ${{scoreCls}}" style="width:${{s.score || 0}}%"></div>
                </div>
            </div>
            <div class="card-metrics">
                <div><span class="metric-label">RSI</span><br><span class="metric-value">${{getRSIHTML(s.rsi)}}</span></div>
                <div><span class="metric-label">BBW%</span><br><span class="metric-value">${{s.bbw_pct != null ? s.bbw_pct.toFixed(1) : '-'}}</span></div>
                <div><span class="metric-label">Weekly</span><br><span class="metric-value">${{getWeeklyHTML(s)}}</span></div>
                <div><span class="metric-label">TTM</span><br><span class="metric-value">${{getTTMHTML(s)}}</span></div>
            </div>
            <div class="card-details">
                <div class="card-detail-grid">
                    <div><span class="metric-label">ATR%</span><br><span class="metric-value">${{s.atr_pct != null ? s.atr_pct.toFixed(2) : '-'}}</span></div>
                    <div><span class="metric-label">IV Rank</span><br><span class="metric-value">${{getIVRankHTML(s.iv_rank)}}</span></div>
                    <div><span class="metric-label">Option</span><br><span class="metric-value">${{s.option_strategy}}</span></div>
                    <div><span class="metric-label">DTE</span><br><span class="metric-value">${{s.dte_range}}</span></div>
                </div>
                <div style="margin-top:8px">${{getConfirmHTML(s)}}</div>
                <div style="margin-top:6px">${{getPatternsHTML(s.patterns)}}</div>
                <canvas class="sparkline" id="card-spark-${{idx}}" width="240" height="40" style="margin-top:8px;width:100%"></canvas>
            </div>
            <button class="card-expand-btn" onclick="toggleCard(this)">Detalji &#9660;</button>
        `;
        container.appendChild(card);
    }});
}}

function toggleCard(btn) {{
    let card = btn.closest('.signal-card');
    let wasExpanded = card.classList.contains('expanded');
    card.classList.toggle('expanded');
    btn.innerHTML = wasExpanded ? 'Detalji &#9660;' : 'Zatvori &#9650;';

    // Draw sparkline on first expand
    if (!wasExpanded) {{
        let canvas = card.querySelector('.sparkline');
        if (canvas && canvas.id.startsWith('card-spark-')) {{
            let idx = parseInt(canvas.id.replace('card-spark-', ''));
            let filtered = SIGNALS.filter(s => {{
                if (currentSignalFilter !== 'all' && s.signal_type !== currentSignalFilter) return false;
                if (currentDirFilter !== 'all' && s.signal_direction !== currentDirFilter) return false;
                return true;
            }});
            let sig = filtered[idx];
            if (sig && sig.sparkline && sig.sparkline.length > 1) {{
                requestAnimationFrame(() => drawSparkline(canvas, sig.sparkline));
            }}
        }}
    }}
}}

function drawSparkline(canvas, data) {{
    let ctx = canvas.getContext('2d');
    let w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    let min = Math.min(...data), max = Math.max(...data);
    let range = max - min || 1;
    let color = data[data.length-1] >= data[0] ? '#22c55e' : '#ef4444';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    data.forEach((v, i) => {{
        let x = (i / (data.length - 1)) * w;
        let y = h - ((v - min) / range) * (h - 4) - 2;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }});
    ctx.stroke();
}}

function sortTable(colIdx, type) {{
    let tbody = document.getElementById('signalBody');
    let rows = Array.from(tbody.querySelectorAll('tr'));
    if (sortCol === colIdx) {{ sortAsc = !sortAsc; }} else {{ sortCol = colIdx; sortAsc = true; }}
    rows.sort((a, b) => {{
        let aVal = a.cells[colIdx].textContent.trim().replace('$','');
        let bVal = b.cells[colIdx].textContent.trim().replace('$','');
        if (type === 'num') {{
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }}
        if (aVal < bVal) return sortAsc ? -1 : 1;
        if (aVal > bVal) return sortAsc ? 1 : -1;
        return 0;
    }});
    rows.forEach(r => tbody.appendChild(r));
}}

function toggleList(btn) {{
    btn.classList.toggle('active');
}}

function setSignalFilter(btn) {{
    btn.parentElement.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentSignalFilter = btn.dataset.filter;
    renderTable();
}}

function setDirFilter(btn) {{
    btn.parentElement.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentDirFilter = btn.dataset.dir;
    renderTable();
}}

function showToast(msg) {{
    let t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 4000);
}}

async function runNewScan() {{
    let params = {{
        mode: document.getElementById('modeSelect').value,
        use_ema: document.getElementById('emaSelect').value === 'true',
        use_sp500: document.querySelector('[data-list="sp500"]').classList.contains('active'),
        use_nasdaq: document.querySelector('[data-list="nasdaq"]').classList.contains('active'),
        use_dow: document.querySelector('[data-list="dow"]').classList.contains('active'),
        use_custom: document.querySelector('[data-list="custom"]').classList.contains('active'),
    }};
    try {{
        let resp = await fetch('/run_scan', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(params)
        }});
        if (resp.ok) {{ location.reload(); }}
        else {{ showToast('Scan error: ' + resp.statusText); }}
    }} catch(e) {{
        showToast('Server nije dostupan. Pokrenite: python scanner/main.py');
    }}
}}

async function scanSingle() {{
    let ticker = document.getElementById('singleTicker').value.trim().toUpperCase();
    if (!ticker) return;
    let mode = document.getElementById('modeSelect').value;
    let ema = document.getElementById('emaSelect').value;
    try {{
        let resp = await fetch(`/scan_single?ticker=${{ticker}}&mode=${{mode}}&use_ema=${{ema}}`);
        if (resp.ok) {{ location.reload(); }}
        else {{ showToast('Ticker ' + ticker + ': no signal or error'); }}
    }} catch(e) {{
        showToast('Server nije dostupan.');
    }}
}}

async function downloadExcel() {{
    try {{
        let resp = await fetch('/download_excel');
        if (resp.ok) {{
            let blob = await resp.blob();
            let url = URL.createObjectURL(blob);
            let a = document.createElement('a');
            a.href = url; a.download = 'scanner_results.xlsx';
            a.click(); URL.revokeObjectURL(url);
        }} else {{ showToast('Excel download failed'); }}
    }} catch(e) {{
        showToast('Server nije dostupan za download.');
    }}
}}

// GitHub Actions dispatch
const GITHUB_REPO = '{github_repo}';
async function triggerGitHubScan() {{
    let token = localStorage.getItem('gh_pat');
    if (!token) {{
        token = prompt('GitHub Personal Access Token (actions:write scope).\\nSprema se lokalno na ovom uređaju:');
        if (!token) return;
        localStorage.setItem('gh_pat', token);
    }}
    try {{
        showToast('Pokrećem Cloud Scan...');
        let resp = await fetch(
            `https://api.github.com/repos/${{GITHUB_REPO}}/actions/workflows/daily_scan.yml/dispatches`,
            {{
                method: 'POST',
                headers: {{
                    'Authorization': `token ${{token}}`,
                    'Accept': 'application/vnd.github.v3+json'
                }},
                body: JSON.stringify({{ ref: 'main' }})
            }}
        );
        if (resp.status === 204) {{
            showToast('Scan pokrenut! Rezultati za ~5 min. Osvježi stranicu.');
        }} else if (resp.status === 401) {{
            localStorage.removeItem('gh_pat');
            showToast('Token nevažeći. Pokušaj ponovo.');
        }} else {{
            showToast('Greška: ' + resp.status);
        }}
    }} catch(e) {{
        showToast('Mrežna greška. Provjeri internetsku vezu.');
    }}
}}

function clearGitHubToken() {{
    localStorage.removeItem('gh_pat');
    showToast('GitHub token obrisan.');
}}

// Server heartbeat
async function checkServer() {{
    try {{
        let resp = await fetch('/health');
        if (resp.ok) {{
            document.getElementById('serverStatus').innerHTML =
                '<span class="status-dot status-green"></span>Online';
        }} else {{ throw new Error(); }}
    }} catch(e) {{
        document.getElementById('serverStatus').innerHTML =
            '<span class="status-dot status-red"></span>Offline';
    }}
}}

// Init
renderTable();
checkServer();
setInterval(checkServer, 30000);
</script>
</body>
</html>"""

    return html
