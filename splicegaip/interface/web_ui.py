"""SpliceGAIP web UI - Modern AI Scientific Workspace.

Redesigned as an interactive multi-agent analysis platform with:
- 仪表盘 with real-time project status
- AI 流水线 visualization with agent workflow
- Results 探索r with filtering and search
- Independent chart management
- 基因-level exploration

Backend API remains unchanged (FastAPI endpoints in splicegaip/api/app.py).
Frontend uses vanilla JS SPA architecture for zero-build deployment.
"""

from __future__ import annotations

from fastapi.responses import HTMLResponse

_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpliceGAIP - AI 智能分析平台</title>
<style>
/* Ocean lab theme: data-dense, calm, and unmistakably scientific. */
:root {
  --black: #06131b;
  --gray-900: #e8f5f4;
  --gray-700: #b0c8cc;
  --gray-500: #76929d;
  --gray-300: #284653;
  --gray-100: #102733;
  --white: #f3fbf8;
  --bg: #07151e;
  --surface: #0c202b;
  --surface-2: #112b36;
  --surface-3: #173944;
  --text: #e8f5f4;
  --text-secondary: #a6c1c5;
  --text-muted: #718e99;
  --accent: #5eead4;
  --secondary: #b7e36a;
  --warning: #f3bd72;
  --danger: #fb7185;
  --border: #244957;
  --font-sans: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;
  --shadow-sm: 0 4px 16px rgba(0, 0, 0, .18);
  --shadow: 0 12px 30px rgba(0, 0, 0, .24);
  --shadow-lg: 0 22px 70px rgba(0, 0, 0, .32);
  --radius: 12px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--bg); }
body { font-family: var(--font-sans); background: var(--bg); color: var(--text); line-height: 1.6; font-size: 15px; -webkit-font-smoothing: antialiased; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: -1; background: radial-gradient(circle at 82% -8%, rgba(94,234,212,.14), transparent 32%), radial-gradient(circle at 5% 100%, rgba(183,227,106,.08), transparent 28%), linear-gradient(120deg, rgba(255,255,255,.015) 1px, transparent 1px); background-size: auto, auto, 34px 34px; }
.app { display: flex; min-height: 100vh; }
.sidebar { width: 264px; background: rgba(7, 21, 30, .88); border-right: 1px solid var(--border); position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 100; backdrop-filter: blur(18px); }
.main { margin-left: 264px; flex: 1; min-height: 100vh; background: transparent; }
.topbar { height: 72px; background: rgba(7, 21, 30, .72); border-bottom: 1px solid rgba(36,73,87,.8); display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-6); position: sticky; top: 0; z-index: 50; backdrop-filter: blur(18px); }
.content { padding: 30px 34px 60px; max-width: 1600px; margin: 0 auto; }

.brand { padding: 28px 22px 24px; border-bottom: 1px solid var(--border); position: relative; }
.brand::before { content: ""; display: block; width: 34px; height: 34px; margin-bottom: 16px; border-radius: 11px; background: radial-gradient(circle at 30% 25%, #e7fff8 0 8%, var(--accent) 9% 35%, #157f83 36% 70%, #0b303a 71%); box-shadow: 0 0 0 5px rgba(94,234,212,.08), 0 0 32px rgba(94,234,212,.23); }
.brand-name { font-size: 21px; font-weight: 750; color: var(--white); letter-spacing: -.4px; }
.brand-tagline { font-size: 10px; color: var(--accent); margin-top: 4px; text-transform: uppercase; letter-spacing: 1.7px; font-weight: 700; }
.nav-section { padding: 22px 0 0; }
.nav-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.7px; color: var(--text-muted); padding: 0 22px; margin-bottom: 9px; }
.nav-item { display: flex; align-items: center; gap: 11px; padding: 11px 20px; margin: 3px 12px 3px 0; color: var(--text-secondary); cursor: pointer; transition: all .2s ease; font-size: 14px; font-weight: 600; border-left: 2px solid transparent; border-radius: 0 9px 9px 0; }
.nav-item::before { content: "·"; color: var(--text-muted); width: 16px; text-align: center; font-size: 22px; line-height: 0; }
.nav-item[data-page="dashboard"]::before { content: "⌂"; font-size: 16px; }
.nav-item[data-page="pipeline"]::before { content: "◌"; font-size: 19px; }
.nav-item[data-page="explorer"]::before { content: "⌁"; font-size: 19px; }
.nav-item[data-page="visualization"]::before { content: "◒"; font-size: 16px; }
.nav-item[data-page="gene"]::before { content: "⌬"; font-size: 18px; }
.nav-item[data-page="report"]::before { content: "▤"; font-size: 15px; }
.nav-item[data-page="assistant"]::before { content: "✦"; font-size: 15px; color: var(--accent); }
.nav-item:hover { background: rgba(94,234,212,.07); color: var(--white); }
.nav-item.active { background: linear-gradient(90deg, rgba(94,234,212,.16), rgba(94,234,212,.04)); color: var(--white); border-left-color: var(--accent); box-shadow: inset 0 0 24px rgba(94,234,212,.04); }

.card, .chart-container, .filters { background: linear-gradient(145deg, rgba(17,43,54,.92), rgba(10,29,39,.92)); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-5); box-shadow: var(--shadow-sm); }
.card { transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease; }
.card:hover { border-color: rgba(94,234,212,.48); transform: translateY(-1px); box-shadow: var(--shadow); }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .9px; color: var(--text-secondary); }
.grid { display: grid; gap: 18px; }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

.status { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; padding: 5px 10px; border-radius: 999px; border: 1px solid transparent; }
.status-running { background: rgba(94,234,212,.12); color: var(--accent); border-color: rgba(94,234,212,.22); }
.status-completed { background: rgba(183,227,106,.12); color: var(--secondary); border-color: rgba(183,227,106,.22); }
.status-waiting { background: rgba(118,146,157,.12); color: var(--text-secondary); border-color: rgba(118,146,157,.2); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); box-shadow: 0 0 0 3px rgba(118,146,157,.12); }
.status-running .status-dot { background: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.12), 0 0 12px var(--accent); }
.status-completed .status-dot { background: var(--secondary); box-shadow: 0 0 0 3px rgba(183,227,106,.12); }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2); padding: 10px 18px; font-size: 13px; font-weight: 700; border-radius: 9px; border: 1px solid transparent; cursor: pointer; transition: all .2s ease; font-family: var(--font-sans); }
.btn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn-primary { background: linear-gradient(135deg, #6af3d9, #34bdb2); color: #062027; border-color: #6af3d9; box-shadow: 0 6px 20px rgba(94,234,212,.18); }
.btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 9px 25px rgba(94,234,212,.28); }
.btn-secondary { background: rgba(17,43,54,.55); color: var(--text-secondary); border-color: var(--border); }
.btn-secondary:hover { color: var(--white); border-color: var(--accent); background: rgba(94,234,212,.08); }
.btn-sm { padding: 7px 13px; font-size: 12px; }

.table-container { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { background: rgba(94,234,212,.06); }
th { text-align: left; padding: 11px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
td { padding: 11px 14px; border-bottom: 1px solid rgba(36,73,87,.65); color: var(--text-secondary); }
tr:last-child td { border-bottom: none; }
tr:hover { background: rgba(94,234,212,.045); }

.pipeline { display: flex; flex-direction: column; gap: 12px; }
.pipeline-step { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-4); background: rgba(12,32,43,.78); border: 1px solid var(--border); border-radius: 10px; cursor: pointer; transition: all .2s ease; }
.pipeline-step:hover { border-color: var(--accent); transform: translateX(2px); }
.pipeline-step.active { border-color: var(--accent); background: linear-gradient(90deg, rgba(94,234,212,.13), rgba(94,234,212,.03)); }
.pipeline-step.completed { border-color: rgba(183,227,106,.46); }
.step-number { width: 36px; height: 36px; border-radius: 11px; background: var(--surface-3); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 750; color: var(--text-secondary); flex-shrink: 0; }
.pipeline-step.active .step-number { background: var(--accent); color: #062027; }
.pipeline-step.completed .step-number { background: rgba(183,227,106,.18); color: var(--secondary); }
.step-info { flex: 1; }
.step-name { font-weight: 700; font-size: 14px; margin-bottom: var(--space-1); }
.step-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.filters { display: flex; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-5); }
.filter-group { display: flex; align-items: center; gap: var(--space-2); }
.filter-label { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
.checkbox-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.checkbox-label { display: flex; align-items: center; gap: var(--space-2); font-size: 13px; cursor: pointer; padding: 4px 8px; border-radius: 7px; color: var(--text-secondary); }
.checkbox-label:hover { background: rgba(94,234,212,.08); color: var(--white); }
input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
.search-bar { display: flex; gap: var(--space-3); margin-bottom: var(--space-5); }
.search-input, input, select, textarea { flex: 1; padding: 10px 13px; border: 1px solid var(--border); border-radius: 9px; font-size: 14px; font-family: var(--font-sans); color: var(--text); background: rgba(8,25,34,.78); }
.search-input::placeholder, input::placeholder, textarea::placeholder { color: var(--text-muted); }
.search-input:focus, input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.1); }
#upload-modal input, #project-name, #analysis-query { color: var(--text) !important; background: rgba(8,25,34,.9) !important; border-color: var(--border) !important; }
#upload-modal input::placeholder, #project-name::placeholder, #analysis-query::placeholder { color: var(--text-muted) !important; opacity: 1; }
select option { color: var(--text); background: var(--surface); }
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus { -webkit-text-fill-color: var(--text); -webkit-box-shadow: 0 0 0 1000px rgba(8,25,34,.9) inset; transition: background-color 9999s ease-out; }
.chart-container { margin-bottom: var(--space-5); }
.chart-placeholder { height: 360px; background: repeating-linear-gradient(0deg, rgba(94,234,212,.025) 0 1px, transparent 1px 40px), linear-gradient(145deg, rgba(94,234,212,.06), rgba(12,32,43,.8)); border-radius: 9px; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 14px; border: 1px dashed rgba(94,234,212,.22); }

.page { display: none; }
.page.active { display: block; animation: pageIn .24s ease-out; }
.hero-panel { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding: 27px 30px; margin-bottom: 22px; border: 1px solid rgba(94,234,212,.28); border-radius: 16px; background: radial-gradient(circle at 92% 10%, rgba(94,234,212,.2), transparent 32%), linear-gradient(120deg, rgba(17,43,54,.96), rgba(9,28,38,.92)); box-shadow: var(--shadow); }
.eyebrow { color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: 1.8px; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
.eyebrow-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary); box-shadow: 0 0 12px var(--secondary); }
.hero-copy h1 { font-size: clamp(24px, 3vw, 37px); line-height: 1.15; letter-spacing: -.8px; max-width: 700px; margin: 10px 0 8px; color: var(--white); }
.hero-copy p { color: var(--text-secondary); font-size: 14px; max-width: 680px; }
.hero-meta { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.hero-chip { padding: 7px 10px; border: 1px solid rgba(94,234,212,.26); border-radius: 999px; color: var(--text-secondary); background: rgba(94,234,212,.07); font-size: 11px; font-weight: 700; white-space: nowrap; }
.chat-message { animation: fadeIn .3s ease; }
.message-header { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.agent-icon { font-size: 14px; }
.agent-name { font-weight: 700; }
.message-time { color: var(--text-muted); margin-left: auto; font-size: 11px; }
.message-content { font-size: 13px; line-height: 1.6; margin-top: 6px; color: var(--text-secondary); }
.log-entry { margin-bottom: 4px; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
#chat-messages, #skill-results { background: rgba(8,25,34,.72) !important; border-color: var(--border) !important; }
#chat-messages .chat-message { padding: 12px; margin-bottom: 12px; background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: var(--radius); color: var(--text) !important; box-shadow: 0 1px 2px rgba(0,0,0,.18); }
#chat-messages .chat-message.user-message { background: rgba(94,234,212,.12) !important; border-color: rgba(94,234,212,.3) !important; }
#chat-messages .chat-message > div { background: transparent !important; color: inherit !important; }
#chat-messages .chat-message .message-author { color: var(--accent) !important; }
#skill-results { color: var(--text); }
.model-config { margin-bottom: 16px; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(8,25,34,.5); }
.model-config summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 10px; padding: 10px 14px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }
.model-config summary::-webkit-details-marker { display: none; }
.model-config summary .status { margin-left: auto; }
.model-config summary::after { content: "▾"; color: var(--text-muted); font-size: 11px; }
.model-config[open] summary::after { content: "▴"; }
.model-config-body { display: flex; flex-direction: column; gap: 10px; padding: 0 14px 14px; }
.model-config-body .cfg-row { display: flex; align-items: center; gap: 10px; }
.model-config-body .cfg-row label { flex: none; width: 88px; font-size: 12px; font-weight: 700; color: var(--text-secondary); }
.model-config-body .cfg-row input { flex: 1; padding: 8px 10px; font-size: 13px; }
.model-config-body .cfg-hint, .model-config-body .cfg-msg { font-size: 12px; line-height: 1.6; color: var(--text-muted); }
.model-config-body .cfg-msg.ok { color: var(--secondary); }
.model-config-body .cfg-msg.err { color: var(--danger); }

/* Smart-ingestion review dialog */
#ingest-modal { display: none; position: fixed; inset: 0; z-index: 1200; padding: 24px; background: rgba(3,12,17,.84); backdrop-filter: blur(10px); align-items: center; justify-content: center; }
#ingest-modal.open { display: flex; }
.ingest-panel { width: min(980px, 96vw); max-height: 90vh; display: flex; flex-direction: column; background: linear-gradient(160deg, var(--surface), #091b25); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--shadow-lg); overflow: hidden; }
.ingest-head { display: flex; align-items: flex-start; gap: 12px; padding: 20px 24px 16px; border-bottom: 1px solid var(--border); background: rgba(7,21,30,.72); }
.ingest-head .ingest-title { font-size: 20px; font-weight: 750; color: var(--white); letter-spacing: -.3px; }
.ingest-head .ingest-sub { margin-top: 4px; font-size: 12px; color: var(--text-muted); }
.ingest-close { margin-left: auto; flex: none; width: 32px; height: 32px; border-radius: 9px; border: 1px solid var(--border); background: rgba(8,25,34,.7); color: var(--text-secondary); font-size: 18px; line-height: 1; cursor: pointer; }
.ingest-close:hover { color: var(--white); border-color: var(--accent); }
.ingest-body { padding: 18px 24px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.ingest-trace { display: flex; gap: 8px; flex-wrap: wrap; }
.ingest-step { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border: 1px solid var(--border); border-radius: 999px; background: rgba(8,25,34,.55); font-size: 11px; font-weight: 650; color: var(--text-secondary); }
.ingest-step .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.ingest-step.ok .dot { background: var(--secondary); box-shadow: 0 0 8px rgba(183,227,106,.5); }
.ingest-step.warn .dot { background: var(--warning); }
.ingest-step.error .dot { background: var(--danger); }
.ingest-step.running .dot { background: var(--accent); box-shadow: 0 0 8px rgba(94,234,212,.6); }
.ingest-step.skip { opacity: .62; }
.ingest-source { font-size: 12px; color: var(--text-muted); }
.ingest-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ingest-stat { padding: 12px 14px; border: 1px solid var(--border); border-radius: 11px; background: rgba(8,25,34,.52); }
.ingest-stat .v { font-size: 22px; font-weight: 750; color: var(--white); line-height: 1.2; }
.ingest-stat .k { font-size: 10px; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); margin-top: 3px; }
.ingest-files { font-size: 12px; color: var(--text-muted); line-height: 1.85; }
.ingest-files code { font-family: var(--font-mono); color: var(--text-secondary); background: rgba(94,234,212,.06); padding: 1px 5px; border-radius: 5px; }
.ingest-section-title { font-size: 11px; font-weight: 800; letter-spacing: 1.3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.ingest-map-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 16px; }
.ingest-map-row { display: flex; align-items: center; gap: 9px; }
.ingest-map-row label { flex: none; width: 132px; font-size: 12px; font-weight: 650; color: var(--text-secondary); }
.ingest-map-row select { flex: 1; min-width: 0; padding: 7px 9px; font-size: 12px; border-radius: 8px; }
.ingest-map-row select.missing { border-color: rgba(243,189,114,.55); }
.ingest-issues { display: flex; flex-direction: column; gap: 6px; }
.ingest-issue { display: flex; gap: 8px; padding: 8px 10px; border-radius: 9px; font-size: 12px; line-height: 1.55; border: 1px solid var(--border); background: rgba(8,25,34,.45); color: var(--text-secondary); }
.ingest-issue .tag { flex: none; font-weight: 800; font-size: 10px; letter-spacing: .6px; padding: 2px 6px; border-radius: 5px; height: fit-content; }
.ingest-issue.error { border-color: rgba(251,113,133,.3); }
.ingest-issue.error .tag { background: rgba(251,113,133,.14); color: var(--danger); }
.ingest-issue.warning .tag { background: rgba(243,189,114,.14); color: var(--warning); }
.ingest-issue.info .tag { background: rgba(94,234,212,.12); color: var(--accent); }
.ingest-preview-table { max-height: 260px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; }
.ingest-preview-table table { min-width: 620px; }
.ingest-privacy { font-size: 11px; color: var(--text-muted); line-height: 1.6; }
.ingest-footer { display: flex; align-items: center; gap: 12px; padding: 14px 24px; border-top: 1px solid var(--border); background: rgba(7,21,30,.9); }
.ingest-footer .ingest-error { color: var(--danger); font-size: 12px; margin-right: auto; }
.ingest-footer .spacer { margin-right: auto; }
@media (max-width: 760px) { .ingest-stats { grid-template-columns: repeat(2, 1fr); } .ingest-map-grid { grid-template-columns: 1fr; } .ingest-map-row label { width: 112px; } }
#stat-samples, #stat-events, #stat-significant { color: var(--white) !important; text-shadow: 0 0 20px rgba(94,234,212,.16); }
#progress-bar { background: linear-gradient(90deg, var(--accent), var(--secondary)) !important; }
#upload-modal { background: rgba(3,12,17,.75) !important; }
#upload-modal > div { background: var(--surface) !important; border-color: var(--border) !important; color: var(--text) !important; }
#event-detail-modal { background: rgba(3,12,17,.78) !important; backdrop-filter: blur(8px); }
#event-detail-modal > div { background: var(--surface) !important; border-color: var(--border) !important; color: var(--text) !important; box-shadow: var(--shadow-lg); }
#event-detail-modal > div > div:first-child { background: linear-gradient(135deg, #0d4d56, #102a39) !important; }
#event-detail-modal [style*="font-size: 32px"] { color: var(--accent) !important; }

/* MCP tool console */
.mcp-panel { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 12px; }
.mcp-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mcp-title { font-size: 16px; font-weight: 750; color: var(--white); letter-spacing: -.2px; }
.mcp-sub { font-size: 11px; color: var(--text-muted); margin-top: 3px; letter-spacing: .4px; }
.mcp-badge { padding: 4px 9px; border-radius: 999px; font-size: 11px; font-weight: 750; border: 1px solid var(--border); color: var(--text-secondary); background: rgba(8,25,34,.6); white-space: nowrap; }
.mcp-badge.ok { color: var(--secondary); border-color: rgba(183,227,106,.35); background: rgba(183,227,106,.08); }
.mcp-badge.err { color: var(--danger); border-color: rgba(251,113,133,.35); background: rgba(251,113,133,.08); }
.mcp-field { display: flex; flex-direction: column; gap: 6px; }
.mcp-field > label { font-size: 11px; font-weight: 800; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); }
.mcp-inline { display: flex; gap: 8px; align-items: center; }
.mcp-inline select { flex: 1; min-width: 0; }
.mcp-panel select, .mcp-panel textarea, .mcp-panel input[type="text"] { width: 100%; padding: 9px 11px; border: 1px solid var(--border); border-radius: 9px; background: rgba(8,25,34,.9); color: var(--text); font-family: inherit; font-size: 13px; }
.mcp-panel input[type="text"]::placeholder { color: var(--text-muted); }
.mcp-panel textarea { font-family: var(--font-mono); font-size: 12px; line-height: 1.55; resize: vertical; min-height: 86px; }
.mcp-desc { font-size: 12px; line-height: 1.6; color: var(--text-secondary); min-height: 18px; }
.mcp-hint { font-size: 11px; line-height: 1.5; color: var(--text-muted); word-break: break-all; }
.mcp-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mcp-result { margin: 0; padding: 12px; max-height: 300px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; background: rgba(3,12,17,.75); color: var(--text-secondary); font-family: var(--font-mono); font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
.mcp-result.err { color: var(--danger); }
.mcp-empty { padding: 10px 12px; border: 1px dashed var(--border); border-radius: 9px; font-size: 12px; color: var(--text-muted); }

@keyframes pageIn { from { opacity: .25; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 1100px) { .sidebar { width: 236px; } .main { margin-left: 236px; } .grid-4 { grid-template-columns: repeat(2, 1fr); } .hero-panel { align-items: flex-start; flex-direction: column; } .hero-meta { justify-content: flex-start; } }
@media (max-width: 768px) { .sidebar { display: none; } .main { margin-left: 0; } .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } .content { padding: 20px 16px 40px; } .topbar { padding: 0 16px; } .hero-panel { padding: 22px; } .hero-copy h1 { font-size: 26px; } }
.lang-toggle { display: inline-flex; align-items: center; gap: 2px; padding: 3px; background: rgba(8, 25, 34, .06); border: 1px solid var(--border); border-radius: 999px; }
.lang-toggle button { border: 0; background: transparent; color: var(--text-secondary); font-family: inherit; font-size: 12px; font-weight: 700; line-height: 1; padding: 6px 10px; border-radius: 999px; cursor: pointer; transition: background .18s ease, color .18s ease; }
.lang-toggle button:hover { color: var(--text); }
.lang-toggle button.active { background: var(--black); color: var(--white); box-shadow: 0 1px 3px rgba(0,0,0,.18); }
@media (max-width: 520px) { .lang-toggle button { padding: 5px 7px; font-size: 11px; } }
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><div class="brand-name">SpliceGAIP</div><div class="brand-tagline">AI 智能分析平台</div></div>
    <div class="nav-section"><div class="nav-label">主菜单</div>
      <div class="nav-item active" data-page="dashboard">仪表盘</div>
      <div class="nav-item" data-page="pipeline">AI 流水线</div>
      <div class="nav-item" data-page="explorer">事件浏览器</div>
    </div>
    <div class="nav-section"><div class="nav-label">分析工具</div>
      <div class="nav-item" data-page="visualization">可视化</div>
      <div class="nav-item" data-page="gene">基因浏览器</div>
      <div class="nav-item" data-page="report">报告</div>
    </div>
    <div class="nav-section"><div class="nav-label">智能助手</div>
      <div class="nav-item" data-page="assistant">🤖 AI 助手</div>
    </div>
  </aside>
  <main class="main">
    <div class="topbar">
      <div style="font-size: 14px; color: var(--text-secondary);" id="current-project">未加载项目</div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <div class="lang-toggle" role="group" aria-label="Language" data-no-i18n>
          <button type="button" data-lang="zh" class="active" aria-pressed="true">简体中文</button>
          <button type="button" data-lang="zh-Hant" aria-pressed="false">繁體中文</button>
          <button type="button" data-lang="en" aria-pressed="false">EN</button>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="refreshData()">刷新</button>
        <button class="btn btn-primary btn-sm" onclick="showUploadModal()">+ 新建分析</button>
      </div>
    </div>
    <div class="content">
      <div class="page active" id="page-dashboard">
        <section class="hero-panel">
          <div class="hero-copy">
            <div class="eyebrow"><span class="eyebrow-dot"></span>Splice intelligence workspace</div>
            <h1>从剪接事件，到可复现的生物学证据。</h1>
            <p>让 Agent 整理数据、追踪分析状态，并把每一个结论连接到可验证的结果。</p>
          </div>
          <div class="hero-meta">
            <span class="hero-chip">Agentic mode</span>
            <span class="hero-chip">FDR 0.05</span>
            <span class="hero-chip">ΔPSI 0.10</span>
          </div>
        </section>
        <div class="grid grid-4" style="margin-bottom: 32px;">
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">总样本数</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-samples">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">RNA-seq 样本</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">剪接事件</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-events">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">检测到的事件总数</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">显著事件</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-significant">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">FDR < 0.05 & |ΔPSI| > 0.1</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">系统状态</div>
            <div style="margin-top: 8px;" id="stat-status"><span class="status status-waiting"><span class="status-dot"></span>空闲</span></div>
          </div>
        </div>
        <div class="grid grid-2">
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">当前运行 Agent</div>
              <div id="current-agent-indicator" style="display: none;"><span class="status status-running"><span class="status-dot"></span>分析中</span></div>
            </div>
            <div id="current-agent">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;">🤖</div>
                <div style="font-size: 14px;">暂无运行中的分析</div>
                <button class="btn btn-primary" style="margin-top: 16px;" onclick="showUploadModal()">启动新分析</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">历史项目</div>
              <button class="btn btn-sm btn-secondary" onclick="loadDashboard()">刷新</button>
            </div>
            <input id="project-search" type="search" placeholder="搜索历史项目" oninput="renderProjectHistory()" style="width:100%;margin-bottom:12px;padding:9px;border:1px solid var(--border);border-radius:6px;">
            <div id="recent-projects" style="max-height:440px;overflow:auto;">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;">📁</div>
                <div style="font-size: 14px;">暂无项目</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-pipeline">
        <div class="card" style="margin-bottom: 24px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div>
              <div style="font-size: 18px; font-weight: 700;">分析进度</div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;" id="pipeline-status-text">等待启动...</div>
            </div>
            <div id="pipeline-progress" style="font-size: 24px; font-weight: 800; color: var(--accent);">0%</div>
          </div>
          <div style="height: 8px; background: var(--gray-100); border-radius: 4px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
            <div id="progress-bar" style="height: 100%; width: 0%; background: var(--black); transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 4px rgba(8, 145, 178, 0.3);"></div>
          </div>
        </div>
        
        <div class="card" style="margin-bottom: 24px;">
          <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">Agent 工作流</div>
          <div class="pipeline" id="pipeline-steps">
            <div class="pipeline-step waiting">
              <div class="step-number">1</div>
              <div class="step-info">
                <div class="step-name">📊 数据 Agent</div>
                <div class="step-desc">加载并验证输入数据，检查文件格式和完整性</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">2</div>
              <div class="step-info">
                <div class="step-name">✅ 质控 Agent</div>
                <div class="step-desc">执行质量控制检查，过滤低质量样本</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">3</div>
              <div class="step-info">
                <div class="step-name">🔬 剪接检测 Agent</div>
                <div class="step-desc">使用统计模型检测可变剪接事件</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">4</div>
              <div class="step-info">
                <div class="step-name">📈 统计 Agent</div>
                <div class="step-desc">计算显著性（FDR）和效应量（Delta PSI）</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">5</div>
              <div class="step-info">
                <div class="step-name">🧬 注释 Agent</div>
                <div class="step-desc">功能注释、通路富集和文献证据收集</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">6</div>
              <div class="step-info">
                <div class="step-name">🤖 解读 Agent</div>
                <div class="step-desc">生成生物学解读和专业分析报告</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-explorer">
        <div class="card" style="margin-bottom: 24px;">
          <div style="font-size: 16px; font-weight: 700; margin-bottom: 20px;">筛选条件</div>
          <div class="search-bar" style="margin-bottom: 20px;">
            <input type="text" class="search-input" placeholder="搜索基因名称、事件ID或染色体位置..." id="search-input" onkeypress="if(event.key==='Enter') applyFilters()">
            <button class="btn btn-primary" onclick="applyFilters()">🔍 应用筛选</button>
          </div>
          <div class="filters" style="margin-bottom: 0;">
            <div class="filter-group">
              <div class="filter-label">事件类型</div>
              <div class="checkbox-group">
                <label class="checkbox-label"><input type="checkbox" value="SE" checked> SE (外显子跳跃)</label>
                <label class="checkbox-label"><input type="checkbox" value="MXE" checked> MXE (互斥外显子)</label>
                <label class="checkbox-label"><input type="checkbox" value="A3SS" checked> A3SS (可变3'剪接)</label>
                <label class="checkbox-label"><input type="checkbox" value="A5SS" checked> A5SS (可变5'剪接)</label>
                <label class="checkbox-label"><input type="checkbox" value="RI" checked> RI (内含子保留)</label>
              </div>
            </div>
            <div class="filter-group">
              <div class="filter-label">统计阈值</div>
              <div style="display: flex; gap: 20px;">
                <label class="checkbox-label"><input type="checkbox" id="filter-fdr" checked> FDR &lt; 0.05</label>
                <label class="checkbox-label"><input type="checkbox" id="filter-dpsi" checked> |Delta PSI| &gt; 0.1</label>
              </div>
            </div>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>事件 ID</th>
                <th>基因</th>
                <th>类型</th>
                <th>Delta PSI</th>
                <th>FDR</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody id="events-table">
              <tr>
                <td colspan="6" style="text-align: center; padding: 60px; color: var(--text-muted);">
                  <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;">📋</div>
                  <div style="font-size: 16px; font-weight: 600;">未加载事件数据</div>
                  <div style="font-size: 14px; margin-top: 8px;">请完成分析后查看结果</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="page" id="page-visualization">
        <div class="grid grid-2">
          <div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);">📊 核心统计图</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">差异剪接的显著性与效应量</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('volcano')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🌋 火山图 Volcano</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">ΔPSI vs -log10(FDR)，标注显著性阈值</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_waterfall')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">💧 ΔPSI 瀑布图 Waterfall</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">Top 25 效应量排序，区分包含上调/下调</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_ecdf')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">📈 ΔPSI 累积分布 ECDF</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">效应量经验累积分布与阈值占比</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('fdr_scree')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🪜 显著性碎石图 Scree</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">候选排名 vs -log10(FDR)，定位显著性拐点</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);">🧬 事件组成与机制</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">剪接事件类型构成与分子机制</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('event_type_counts')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">📊 事件类型分布</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">SE/MXE/A5SS/A3SS/RI 五类事件计数</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_significance')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🎯 类型×显著性堆叠图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">各类型中显著与非显著事件构成</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_schematic')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🧩 剪接机制示意图 Schematic</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">五类可变剪接的外显子-内含子结构模式图</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);">🔬 样本与质控</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">队列构成与样本水平 PSI 模式</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('psi_heatmap')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🌡️ PSI 热图 Heatmap</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">Top 事件逐样本 PSI 聚类热图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('psi_distribution')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">📦 分组 PSI 箱线图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">各组 PSI 分布与离群样本检测</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('sample_composition')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🥧 队列构成图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">分组占比与批次分布（QC 必备）</div></div>
                </button>
              </div>
            </div>
            <div class="card">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);">🤖 AI 排序与功能富集</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">智能体候选评分与通路注释</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('candidate_ranking')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🏆 候选基因排名</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">综合评分 Top 15 候选事件条形图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('score_components')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🧮 评分分解堆叠图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">显著性/效应/生物学/文献四维贡献</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('enrichment')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;">🕸️ 功能富集点图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">GO/KEGG 富集倍数 vs FDR 气泡图</div></div>
                </button>
              </div>
            </div>
          </div>
          <div>
            <div class="chart-container" id="chart-display" style="min-height: 600px; position: sticky; top: 88px;">
              <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;">📈</div>
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">选择图表类型</div>
                <div style="font-size: 14px;">左侧共 13 张专业科研图，点击即可渲染</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-gene">
        <div class="search-bar">
          <input type="text" class="search-input" placeholder="输入基因符号（如 TP53、BRCA1、MYC）..." id="gene-search" onkeypress="if(event.key==='Enter') exploreGene()">
          <button class="btn btn-primary" onclick="exploreGene()">🔍 探索</button>
        </div>
        <div style="margin-bottom: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-700);">
          <div style="font-size: 13px; font-weight: 700; color: var(--secondary); margin-bottom: 8px;">💡 提示</div>
          <div style="font-size: 13px; line-height: 1.8; color: var(--text);">
            输入基因符号查看该基因的所有剪接事件、统计信息和文献证据。支持热门基因如 TP53、BRCA1、MYC、EGFR 等。
          </div>
        </div>
        <div id="gene-details">
          <div class="card">
            <div style="padding: 60px; text-align: center; color: var(--text-muted);">
              <div style="font-size: 64px; margin-bottom: 16px; opacity: 0.3;">🧬</div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">探索基因剪接模式</div>
              <div style="font-size: 14px;">在上方输入基因符号以探索其剪接事件和生物学功能</div>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-report">
        <div class="card">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
            <div>
              <div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">生成分析报告</div>
              <div style="font-size: 13px; color: var(--text-secondary);">基于当前分析结果生成专业报告</div>
            </div>
            <div style="display: flex; gap: 12px;">
              <button class="btn btn-primary" onclick="generateReport('html')">
                <span>📄 HTML 报告</span>
              </button>
              <button class="btn btn-secondary" onclick="generateReport('pdf')">
                <span>📑 PDF 报告</span>
              </button>
            </div>
          </div>
          
          <div id="report-output">
            <div style="padding: 40px; text-align: center; color: var(--text-muted);">
              <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;">📊</div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">准备生成报告</div>
              <div style="font-size: 14px;">完成分析后可生成包含统计结果、可视化和生物学解读的专业报告</div>
            </div>
          </div>
          
          <div style="margin-top: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--black);">
            <div style="font-size: 13px; font-weight: 700; color: var(--accent); margin-bottom: 8px;">💡 报告内容</div>
            <div style="font-size: 13px; line-height: 1.8; color: var(--text);">
              <div>• 项目概览与样本统计</div>
              <div>• 显著剪接事件列表（FDR < 0.05）</div>
              <div>• 关键基因的功能注释与通路富集</div>
              <div>• 可视化图表（火山图、热图、分布图）</div>
              <div>• AI 生成的生物学解读与建议</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- AI Assistant Page -->
      <div class="page" id="page-assistant">
        <div class="grid grid-2" style="height: calc(100vh - 140px);">
          <!-- Chat Interface -->
          <div class="card" style="display: flex; flex-direction: column;">
            <div style="font-size: 18px; font-weight: 700; margin-bottom: 16px;">🤖 SpliceGAIP 智能助手</div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
              支持基因注释、文献搜索、通路富集、剪接事件解读等专业技能，并可通过 MCP 调用外部工具
            </div>

            <details class="model-config" id="model-config">
              <summary>
                <span>⚙️ 模型配置</span>
                <span class="status status-waiting" id="cfg-status"><span class="status-dot"></span><span id="cfg-status-text">检查中…</span></span>
              </summary>
              <div class="model-config-body">
                <div class="cfg-row"><label for="cfg-base">Base URL</label><input id="cfg-base" type="text" autocomplete="off" placeholder="https://api.deepseek.com"></div>
                <div class="cfg-row"><label for="cfg-model">模型名</label><input id="cfg-model" type="text" autocomplete="off" placeholder="deepseek-flash"></div>
                <div class="cfg-row"><label for="cfg-key">API Key</label><input id="cfg-key" type="password" autocomplete="off" placeholder="留空则保持当前密钥"></div>
                <div class="cfg-row">
                  <button class="btn btn-primary btn-sm" id="cfg-save" type="button" onclick="saveModelConfig()">保存并启用</button>
                  <span class="cfg-msg" id="cfg-msg"></span>
                </div>
                <div class="cfg-hint">密钥仅保存在本机 .env / 配置大模型.env，不会写入报告或日志；保存后即时生效。</div>
              </div>
            </details>
            
            <!-- Skill Buttons -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px;">
              <button class="btn btn-sm btn-secondary" onclick="loadSkill('gene_annotation')" style="text-align: left; padding: 12px;">
                <div style="font-size: 16px; margin-bottom: 4px;">🧬</div>
                <div style="font-size: 13px; font-weight: 600;">基因注释</div>
              </button>
              <button class="btn btn-sm btn-secondary" onclick="loadSkill('literature_search')" style="text-align: left; padding: 12px;">
                <div style="font-size: 16px; margin-bottom: 4px;">📚</div>
                <div style="font-size: 13px; font-weight: 600;">文献搜索</div>
              </button>
              <button class="btn btn-sm btn-secondary" onclick="loadSkill('pathway_enrichment')" style="text-align: left; padding: 12px;">
                <div style="font-size: 16px; margin-bottom: 4px;">🔬</div>
                <div style="font-size: 13px; font-weight: 600;">通路富集</div>
              </button>
              <button class="btn btn-sm btn-secondary" onclick="loadSkill('splice_interpretation')" style="text-align: left; padding: 12px;">
                <div style="font-size: 16px; margin-bottom: 4px;">⚕️</div>
                <div style="font-size: 13px; font-weight: 600;">剪接解读</div>
              </button>
            </div>
            
            <!-- Chat Messages -->
            <div id="chat-messages" style="flex: 1; overflow-y: auto; border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; background: #f8fafc; margin-bottom: 16px;">
              <div class="chat-message assistant-message">
                <div class="message-author" style="font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 4px;">🤖 SpliceGAIP</div>
                <div style="font-size: 14px; line-height: 1.6; color: var(--text);">
                  你好！我是 SpliceGAIP 智能助手，可以帮助你：<br>
                  • 查询基因注释和剪接位点信息<br>
                  • 搜索相关科学文献<br>
                  • 执行通路富集分析<br>
                  • 解读剪接事件的临床意义<br>
                  • 通过 MCP 调用外部工具与项目数据<br><br>
                  请选择上方的技能按钮开始，或直接输入你的问题。
                </div>
              </div>
            </div>
            
            <!-- Chat Input -->
            <div style="display: flex; gap: 12px;">
              <input type="text" id="chat-input" placeholder="输入问题或选择上方技能..." 
                     style="flex: 1; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 14px;"
                     onkeypress="if(event.key==='Enter') sendChatMessage()">
              <button class="btn btn-primary" onclick="sendChatMessage()">发送</button>
            </div>
          </div>
          
          <!-- Results Panel -->
          <div class="card" style="overflow-y: auto;">
            <div style="font-size: 18px; font-weight: 700; margin-bottom: 16px;">📊 分析结果</div>
            <div id="skill-results">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;">📈</div>
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">等待分析结果</div>
                <div style="font-size: 14px;">选择左侧的技能按钮执行专业分析</div>
              </div>
            </div>

            <!-- MCP Tool Console -->
            <div class="mcp-panel" id="mcp-panel">
              <div class="mcp-head">
                <div>
                  <div class="mcp-title">🔌 MCP 工具</div>
                  <div class="mcp-sub">Model Context Protocol · 运行时外部工具调用</div>
                </div>
                <span class="mcp-badge" id="mcp-status">未加载</span>
              </div>

              <div class="mcp-field">
                <label for="mcp-agent-question">自然语言指令</label>
                <div class="mcp-inline">
                  <input id="mcp-agent-question" type="text" placeholder="例如：查一下 CD44 有哪些显著剪接事件" onkeypress="if(event.key==='Enter') runMcpAgent()">
                  <button class="btn btn-primary btn-sm" id="mcp-agent-btn" type="button" onclick="runMcpAgent()">AI 调用</button>
                </div>
                <div class="mcp-hint" id="mcp-agent-status">模型选择 MCP 工具 → 本地校验 → 执行并返回结果</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-server-select">MCP 服务器</label>
                <div class="mcp-inline">
                  <select id="mcp-server-select" onchange="onMcpServerChange()"></select>
                  <button class="btn btn-secondary btn-sm" type="button" onclick="loadMcpServers(true)">刷新</button>
                </div>
                <div class="mcp-hint" id="mcp-server-hint">正在读取服务器配置…</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-tool-select">工具</label>
                <select id="mcp-tool-select" onchange="onMcpToolChange()"></select>
                <div class="mcp-desc" id="mcp-tool-desc">选择服务器与工具后调用</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-args">参数（JSON）</label>
                <textarea id="mcp-args" spellcheck="false" rows="4">{}</textarea>
              </div>

              <div class="mcp-actions">
                <button class="btn btn-primary btn-sm" id="mcp-call-btn" type="button" onclick="callMcpTool()">调用工具</button>
                <span class="mcp-hint" id="mcp-call-status"></span>
              </div>

              <pre class="mcp-result" id="mcp-result">尚未调用</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
</div>

<!-- Upload Modal -->
<div id="upload-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--white); z-index: 1000; align-items: center; justify-content: center;">
  <div style="background: var(--white); border: 1px solid var(--gray-300); border-radius: var(--radius); padding: 32px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
      <h2 style="font-size: 20px; font-weight: 600; color: var(--black);">新建分析项目</h2>
      <button onclick="closeUploadModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--gray-700);">×</button>
    </div>
    <div style="margin-bottom: 20px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--gray-700);">项目名称</label>
      <input type="text" id="project-name" placeholder="输入项目名称（如 My_RNA_Study）" style="width: 100%; padding: 10px; border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; font-family: var(--font-sans); color: var(--gray-900); background: var(--white);">
    </div>
    <div style="margin-bottom: 20px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--gray-700);">分析查询</label>
      <input type="text" id="analysis-query" placeholder="输入分析查询（如 compare treatment vs control）" style="width: 100%; padding: 10px; border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; font-family: var(--font-sans); color: var(--gray-900); background: var(--white);">
    </div>
    <div style="margin-bottom: 24px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--gray-700);">上传文件</label>
      <div id="drop-zone" style="border: 2px dashed var(--gray-300); border-radius: var(--radius); padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--gray-100);" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)" onclick="document.getElementById('file-input').click()">
        <div style="font-size: 48px; margin-bottom: 12px;">📁</div>
        <div style="font-size: 14px; color: var(--gray-700);">拖拽文件到此处，或点击选择文件</div>
        <div style="font-size: 12px; color: var(--gray-500); margin-top: 8px;">支持 CSV、TSV、TXT 表格（Excel 请另存为 CSV），可同时上传样本分组表</div>
      </div>
      <input type="file" id="file-input" multiple style="display: none;" onchange="handleFileSelect(event)">
      <div id="file-list" style="margin-top: 12px;"></div>
    </div>
    <div style="display: flex; gap: 12px; justify-content: flex-end;">
      <button class="btn btn-secondary" onclick="closeUploadModal()">取消</button>
      <button class="btn btn-primary" id="start-analysis-btn" onclick="startAnalysis()" disabled>开始分析</button>
    </div>
  </div>
</div>

<!-- Smart Ingestion Review Modal -->
<div id="ingest-modal" role="dialog" aria-modal="true" aria-labelledby="ingest-title">
  <div class="ingest-panel">
    <div class="ingest-head">
      <div>
        <div class="ingest-title" id="ingest-title">智能接入检查</div>
        <div class="ingest-sub" id="ingest-sub">Agent 已读取数据结构，请确认字段映射后开始分析。</div>
      </div>
      <button class="ingest-close" type="button" onclick="closeIngestModal()" aria-label="关闭">×</button>
    </div>
    <div class="ingest-body" id="ingest-body"></div>
    <div class="ingest-footer">
      <div class="ingest-error" id="ingest-error"></div>
      <button class="btn btn-secondary" type="button" id="ingest-cancel" onclick="closeIngestModal()">取消</button>
      <button class="btn btn-primary" type="button" id="ingest-confirm" onclick="confirmIngest()">确认映射并分析</button>
    </div>
  </div>
</div>

<script src="agent_chat_ui.js"></script>
<script>
const state = { currentProject: localStorage.getItem('splicegaip.currentProject'), projects: [], analysis状态: null, events: [], currentPage: 'dashboard' };
document.querySelectorAll('.nav-item').forEach(item => { item.addEventListener('click', () => { navigateTo(item.dataset.page); }); });
function navigateTo(page) {
  document.querySelectorAll('.nav-item').forEach(item => { item.classList.toggle('active', item.dataset.page === page); });
  document.querySelectorAll('.page').forEach(p => { p.classList.toggle('active', p.id === `page-${page}`); });
  state.currentPage = page;
  if (page === 'dashboard') loadDashboard();
  if (page === 'pipeline') loadPipeline();
  if (page === 'explorer') loadExplorer();
  if (page === 'assistant') { loadModelConfig(); loadMcpServers(); }
}
async function apiCall(endpoint, options = {}) {
  try { const response = await fetch(`/api${endpoint}`, { headers: { 'Content-Type': 'application/json' }, ...options }); return await response.json(); }
  catch (error) { console.error('API Error:', error); return null; }
}
async function loadDashboard() {
  const response = await apiCall('/projects');
  const projectsData = response.projects || response || [];
  state.projects = Array.isArray(projectsData) ? projectsData : [];
  
  // Keep the selected historical project across refreshes.
  if (state.projects.length > 0) {
    const selectedProject = state.projects.find(p => p.project_id === state.currentProject) || state.projects[0];
    state.currentProject = selectedProject.project_id;
    localStorage.setItem('splicegaip.currentProject', state.currentProject);
    const status = await apiCall(`/status/${selectedProject.project_id}`);
    
    if (status) {
      document.getElementById('stat-samples').textContent = (status.samples || []).length;
      document.getElementById('stat-events').textContent = status.events || 0;
      
      const candidates = status.candidates || [];
      const significantCount = (typeof status.significant === 'number')
        ? status.significant
        : candidates.filter(c => c.fdr < 0.05 && Math.abs(c.delta_psi || 0) > 0.1).length;
      document.getElementById('stat-significant').textContent = significantCount;
      
      // Update current project
      document.getElementById('current-project').textContent = selectedProject.name || selectedProject.project_id;
    }
  } else {
    document.getElementById('stat-samples').textContent = '-';
    document.getElementById('stat-events').textContent = '-';
    document.getElementById('stat-significant').textContent = '-';
  }
  
  renderProjectHistory();
}
function renderProjectHistory() {
  const projectsList = document.getElementById('recent-projects');
  const term = (document.getElementById('project-search')?.value || '').toLowerCase();
  const projects = state.projects.filter(p => ((p.name || '') + ' ' + (p.project_id || '') + ' ' + (p.query || '')).toLowerCase().includes(term));
  if (state.projects.length === 0) { 
    projectsList.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">暂无项目</div>'; 
  } else { 
    projectsList.innerHTML = projects.map(p =>
      `<div style="padding: 12px; border-bottom: 1px solid var(--border); cursor: pointer; ${p.project_id === state.currentProject ? 'background:var(--gray-100);' : ''}" onclick="selectProject('${ingestEsc(p.project_id)}')">
        <div style="font-weight: 600;">${ingestEsc(p.name || p.project_id)}</div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${ingestEsc(p.created_at || '')} · ${ingestEsc(p.query || '分析查询')}</div>
      </div>`
    ).join('') || '<div style="padding:20px;text-align:center;color:var(--text-muted);">没有匹配的项目</div>';
  }
}
async function loadPipeline() {
  if (!state.currentProject) return;
  const status = await apiCall(`/status/${state.currentProject}`);
  state.analysis状态 = status;
  if (status) updatePipelineUI(status);
}
function updatePipelineUI(status) {
  const steps = document.querySelectorAll('.pipeline-step');
  
  // Try to get current_step from status, or infer from logs
  let currentStep = status.current_step;
  let statusText = '等待启动...';
  
  if (currentStep === undefined || currentStep === null) {
    // Infer step from logs
    const logs = status.logs || [];
    const actions = logs.map(l => l.action);
    
    if (actions.includes('run_finished')) {
      currentStep = steps.length; // All steps completed
      statusText = '分析已完成';
    } else if (actions.includes('interpret_candidates') || actions.includes('generate_report')) {
      currentStep = 5; // Interpretation done
      statusText = '解读 Agent 正在生成生物学解读...';
    } else if (actions.includes('collect_literature_evidence')) {
      currentStep = 4;
      statusText = '注释 Agent 正在收集文献证据...';
    } else if (actions.includes('run_enrichment')) {
      currentStep = 4;
      statusText = '注释 Agent 正在进行通路富集分析...';
    } else if (actions.includes('rank_candidates')) {
      currentStep = 3;
      statusText = '统计 Agent 正在排序候选事件...';
    } else if (actions.includes('filter_significant_events')) {
      currentStep = 3;
      statusText = '剪接检测 Agent 正在筛选显著事件...';
    } else if (actions.includes('summarize_dataset')) {
      currentStep = 2;
      statusText = '质控 Agent 正在进行质量检查...';
    } else if (actions.includes('understand_query')) {
      currentStep = 1;
      statusText = '数据 Agent 正在理解查询...';
    } else if (actions.includes('run_started')) {
      currentStep = 0;
      statusText = '分析已启动，准备中...';
    } else {
      currentStep = 0;
      statusText = '等待启动...';
    }
  } else {
    const stepNames = ['数据加载', '质量控制', '剪接检测', '统计分析', '功能注释', '生物学解读'];
    statusText = currentStep < stepNames.length ? `正在执行: ${stepNames[currentStep]}` : '处理中...';
  }
  
  document.getElementById('pipeline-status-text').textContent = statusText;
  
  const totalSteps = steps.length;
  const progress = Math.round((currentStep / totalSteps) * 100);
  document.getElementById('pipeline-progress').textContent = `${progress}%`;
  document.getElementById('progress-bar').style.width = `${progress}%`;
  
  steps.forEach((step, index) => {
    step.classList.remove('waiting', 'active', 'completed');
    if (index < currentStep) { 
      step.classList.add('completed'); 
      step.querySelector('.status').className = 'status status-completed'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>已完成'; 
    } else if (index === currentStep && currentStep < totalSteps) { 
      step.classList.add('active'); 
      step.querySelector('.status').className = 'status status-running'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>运行中'; 
    } else { 
      step.classList.add('waiting'); 
      step.querySelector('.status').className = 'status status-waiting'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>等待中'; 
    }
  });
}
async function loadExplorer() {
  if (!state.currentProject) return;
  const status = await apiCall(`/status/${state.currentProject}`);
  if (status && status.candidates) { 
    state.events = status.candidates; 
    renderEventsTable(state.events); 
  } else if (status && status.events) {
    // Fallback: try to get events from status
    state.events = [];
    renderEventsTable(state.events);
  }
}
function renderEventsTable(events) {
  const tbody = document.getElementById('events-table');
  if (!events || events.length === 0) { 
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">未找到匹配的事件</td></tr>'; 
    return; 
  }
  tbody.innerHTML = events.map(event => {
    const eventId = event.event_id || event.id || '-';
    const gene = event.gene_symbol || event.gene || event.gene_id || '-';
    const eventType = event.event_type || event.type || '-';
    const dpsi = (event.delta_psi !== null && event.delta_psi !== undefined) ? Number(event.delta_psi).toFixed(3) : '-';
    const fdr = (event.fdr !== null && event.fdr !== undefined) ? Number(event.fdr).toExponential(2) : '-';
    return `<tr>
      <td>${eventId}</td>
      <td><strong>${gene}</strong></td>
      <td>${eventType}</td>
      <td>${dpsi}</td>
      <td>${fdr}</td>
      <td><button class="btn btn-sm btn-secondary" onclick="viewEventDetails('${eventId}')">查看</button></td>
    </tr>`;
  }).join('');
}
function applyFilters() {
  const searchTerm = document.getElementById('search-input').value.toLowerCase();
  const selected类型s = Array.from(document.querySelectorAll('.checkbox-group input:checked')).map(cb => cb.value);
  const filterFDR = document.getElementById('filter-fdr').checked;
  const filterDPSI = document.getElementById('filter-dpsi').checked;
  let filtered = state.events || [];
  if (searchTerm) { filtered = filtered.filter(e => { const gene = e.gene_symbol || e.gene || ''; const id = e.event_id || e.id || ''; return gene.toLowerCase().includes(searchTerm) || id.toLowerCase().includes(searchTerm); }); }
  if (selected类型s.length > 0) { filtered = filtered.filter(e => selected类型s.includes(e.event_type || e.type)); }
  if (filterFDR) { filtered = filtered.filter(e => e.fdr !== null && e.fdr !== undefined && e.fdr < 0.05); }
  if (filterDPSI) { filtered = filtered.filter(e => e.delta_psi !== null && e.delta_psi !== undefined && Math.abs(e.delta_psi) > 0.1); }
  renderEventsTable(filtered);
}
function loadChart(chartType) {
  const container = document.getElementById('chart-display');
  if (!state.currentProject) { 
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; color: var(--text-muted);">
        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;">⚠️</div>
        <div style="font-size: 16px; font-weight: 600;">未选择项目</div>
        <div style="font-size: 14px; margin-top: 8px;">请先在仪表盘选择一个分析项目</div>
      </div>`; 
    return; 
  }
  
  const meta = {
    volcano: ['火山图 Volcano Plot', '以 ΔPSI 为横轴、-log10(FDR) 为纵轴展示全部剪接事件；虚线为 FDR=0.05 与 |ΔPSI|=0.1 阈值，橙色点为显著事件。'],
    dpsi_waterfall: ['ΔPSI 瀑布图 Waterfall', '按 |ΔPSI| 排序的 Top 25 候选事件；橙色为包含水平上调，蓝色为下调，直观展示效应量谱。'],
    dpsi_ecdf: ['ΔPSI 累积分布 ECDF', 'ΔPSI 的经验累积分布曲线，并标注 |ΔPSI|>0.1 的事件占比，用于评估整体效应量分布。'],
    fdr_scree: ['显著性碎石图 Scree Plot', '候选排名对 -log10(FDR) 曲线，配合 FDR=0.05 参考线定位显著性拐点（elbow）。'],
    event_type_counts: ['事件类型分布 Composition', 'SE / MXE / A5SS / A3SS / RI 五类可变剪接事件的检出计数。'],
    event_significance: ['类型 × 显著性堆叠图', '各事件类型中通过阈值（FDR<0.05 且 |ΔPSI|>0.1）的显著事件与非显著事件构成。'],
    event_schematic: ['剪接机制示意图 Schematic', '五类可变剪接事件的外显子-内含子结构模式图（methods 级示意图）。'],
    psi_heatmap: ['PSI 热图 Heatmap', 'Top |ΔPSI| 事件的逐样本 PSI 热图，列上方标注样本分组，用于观察聚类模式。'],
    psi_distribution: ['分组 PSI 箱线图 Box Plot', '按实验组拆分的 Top 事件 PSI 分布（箱线 + 散点），用于识别离群样本。'],
    sample_composition: ['队列构成图 Cohort QC', '样本分组占比（环图）与批次分布（条形），为质控必备图表。'],
    candidate_ranking: ['候选基因排名 Ranking', 'AI 智能体综合评分（显著性+效应+生物学+文献）Top 15 候选事件。'],
    score_components: ['评分分解堆叠图 Decomposition', 'Top 候选的四维评分贡献分解：显著性 / 效应量 / 生物学 / 文献证据。'],
    enrichment: ['功能富集点图 Dot Plot', 'GO/KEGG 富集结果：横轴为富集倍数，颜色为 -log10(FDR)，点大小为重叠基因数。']
  };
  const info = meta[chartType] || ['图表', ''];
  
  container.innerHTML = `
    <div style="padding: 24px;">
      <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6;">${info[1]}</div>
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 500px; background: var(--gray-100); border-radius: var(--radius);">
        <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <div style="margin-top: 20px; font-size: 14px; color: var(--text-secondary);">正在渲染图表（首次生成约需数秒）...</div>
      </div>
    </div>
  `;
  
  const img = document.createElement('img');
  img.src = '/api/figure/' + state.currentProject + '/' + chartType;
  img.style.width = '100%';
  img.style.borderRadius = 'var(--radius)';
  img.style.marginTop = '20px';
  img.style.boxShadow = 'var(--shadow)';
  
  img.onload = function() {
    container.innerHTML = `
      <div style="padding: 24px;">
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6;">${info[1]}</div>
      </div>
    `;
    container.appendChild(img);
  };
  
  img.onerror = function() { 
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; color: var(--text-muted);">
        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;">📊</div>
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">图表不可用</div>
        <div style="font-size: 14px;">该项目可能尚未生成此图表，请完成分析后重试</div>
      </div>
    `; 
  };
}
async function exploreGene() {
  const geneSymbol = document.getElementById('gene-search').value.trim();
  if (!geneSymbol) {
    alert('请输入基因符号');
    return;
  }
  
  const container = document.getElementById('gene-details');
  if (!state.currentProject) {
    container.innerHTML = `
      <div class="card">
        <div style="padding: 40px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;">⚠️</div>
          <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">请先选择项目</div>
          <div style="font-size: 14px;">在仪表盘选择一个分析项目后再探索基因</div>
        </div>
      </div>`;
    return;
  }
  
  // Show loading state
  container.innerHTML = `
    <div class="card">
      <div style="padding: 60px; text-align: center;">
        <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
        <div style="font-size: 16px; font-weight: 600;">正在加载 ${geneSymbol} 的信息...</div>
      </div>
    </div>`;
  
  const status = await apiCall(`/status/${state.currentProject}`);
  const candidates = (status && status.candidates) || [];
  const geneEvents = candidates.filter(e => (e.gene_symbol || '').toLowerCase() === geneSymbol.toLowerCase());
  
  if (geneEvents.length === 0) {
    container.innerHTML = `
      <div class="card">
        <div style="padding: 60px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 64px; margin-bottom: 16px; opacity: 0.3;">🔍</div>
          <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">未找到 ${geneSymbol} 的剪接事件</div>
          <div style="font-size: 14px;">该基因可能不在当前分析的候选列表中，或未达到显著性阈值</div>
          <button class="btn btn-secondary" style="margin-top: 20px;" onclick="navigateTo('explorer')">浏览所有事件</button>
        </div>
      </div>`;
    return;
  }
  
  // Sort events by significance
  geneEvents.sort((a, b) => (a.fdr || 1) - (b.fdr || 1));
  
  // Calculate summary statistics
  const significantEvents = geneEvents.filter(e => e.fdr < 0.05);
  const avgDeltaPSI = geneEvents.reduce((sum, e) => sum + Math.abs(parseFloat(e.delta_psi || 0)), 0) / geneEvents.length;
  const eventTypeCounts = {};
  geneEvents.forEach(e => {
    const type = e.event_type || 'Unknown';
    eventTypeCounts[type] = (eventTypeCounts[type] || 0) + 1;
  });
  
  // Build event types summary
  const eventTypeSummary = Object.entries(eventTypeCounts).map(([type, count]) => `${type}: ${count}`).join(', ');
  
  let eventsHtml = `
    <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
      <thead>
        <tr style="border-bottom: 2px solid var(--border);">
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">事件 ID</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">类型</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">Delta PSI</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">FDR</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">评分</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">操作</th>
        </tr>
      </thead>
      <tbody>
        ${geneEvents.map(e => {
          const dpsi = Number(e.delta_psi).toFixed(3);
          const fdr = Number(e.fdr).toExponential(2);
          const score = e.score !== undefined ? Number(e.score).toFixed(3) : '-';
          const sigLevel = e.fdr < 0.001 ? '***' : e.fdr < 0.01 ? '**' : e.fdr < 0.05 ? '*' : '';
          const sigColor = e.fdr < 0.001 ? '#dc2626' : e.fdr < 0.01 ? '#f59e0b' : e.fdr < 0.05 ? '#059669' : '#94a3b8';
          
          return `<tr style="border-bottom: 1px solid var(--border);">
            <td style="padding: 12px 16px; font-family: monospace;">${e.event_id || '-'}</td>
            <td style="padding: 12px 16px;"><span style="background: var(--bg); padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">${e.event_type || '-'}</span></td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600;">${dpsi}</td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600; color: ${sigColor};">${fdr} ${sigLevel}</td>
            <td style="padding: 12px 16px; font-family: monospace;">${score}</td>
            <td style="padding: 12px 16px;"><button class="btn btn-sm btn-secondary" onclick="viewEventDetails('${e.event_id || e.id}')">详情</button></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  `;
  
  // Process evidence
  let evidence = geneEvents.length > 0 ? (geneEvents[0].evidence_json || '') : '';
  if (evidence) {
    try {
      const parsed = typeof evidence === 'string' ? JSON.parse(evidence) : evidence;
      if (Array.isArray(parsed)) { 
        evidence = parsed.map(item => `<div style="margin-bottom: 10px; padding-left: 16px; border-left: 3px solid var(--accent);">• ${typeof item === 'string' ? item : JSON.stringify(item)}</div>`).join(''); 
      } else if (typeof parsed === 'object') { 
        evidence = Object.entries(parsed).map(([k, v]) => `<div style="margin-bottom: 10px;"><strong>${k}:</strong> ${v}</div>`).join(''); 
      }
    } catch (e) { 
      evidence = `<div>${evidence}</div>`; 
    }
  }
  
  container.innerHTML = `
    <div class="card" style="margin-bottom: 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div>
          <div style="font-size: 28px; font-weight: 800; background: var(--black); ">${geneSymbol}</div>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">基因剪接分析报告</div>
        </div>
        <button class="btn btn-secondary" onclick="navigateTo('explorer')">返回事件列表</button>
      </div>
      
      <div class="grid grid-3" style="margin-bottom: 28px;">
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #0e7490; font-weight: 700; margin-bottom: 8px;">总事件数</div>
          <div style="font-size: 32px; font-weight: 800; color: #0e7490;">${geneEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #065f46; font-weight: 700; margin-bottom: 8px;">显著事件</div>
          <div style="font-size: 32px; font-weight: 800; color: #065f46;">${significantEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #7c3aed; font-weight: 700; margin-bottom: 8px;">平均 |ΔPSI|</div>
          <div style="font-size: 32px; font-weight: 800; color: #7c3aed;">${avgDeltaPSI.toFixed(3)}</div>
        </div>
      </div>
      
      <div style="margin-bottom: 24px; padding: 16px; background: var(--bg); border-radius: var(--radius);">
        <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px;">事件类型分布</div>
        <div style="font-size: 14px; line-height: 1.6;">${eventTypeSummary}</div>
      </div>
      
      <div style="margin-bottom: 24px;">
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">剪接事件详情</div>
        ${eventsHtml}
      </div>
      
      ${evidence ? `
      <div>
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">文献证据</div>
        <div style="padding: 20px; background: var(--bg); border-radius: var(--radius); font-size: 14px; line-height: 1.8;">
          ${evidence}
        </div>
      </div>
      ` : ''}
    </div>
  `;
}
async function generateReport(format) {
  if (!state.currentProject) { 
    alert('请先选择一个项目'); 
    return; 
  }
  
  const output = document.getElementById('report-output');
  output.innerHTML = `
    <div style="padding: 40px; text-align: center;">
      <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
      <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">正在生成报告...</div>
      <div style="font-size: 13px; color: var(--text-secondary);">这可能需要几分钟时间，请耐心等待</div>
    </div>
  `;
  
  try {
    const reportUrl = `/api/report/${state.currentProject}?format=${format}`;
    const response = await fetch(reportUrl, { method: 'GET' });
    
    if (!response.ok) {
      throw new Error(`报告生成失败 (${response.status})`);
    }
    
    // Get blob and create download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.currentProject}_report.${format === 'html' ? 'html' : 'pdf'}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    output.innerHTML = `
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 24px;">✅</div>
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--success);">报告生成成功！</div>
            <div style="font-size: 13px; color: var(--text-secondary);">文件已自动下载</div>
          </div>
        </div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(5, 150, 105, 0.2);">
          <button class="btn btn-sm btn-primary" onclick="window.open('${reportUrl}', '_blank')">在新窗口中查看</button>
        </div>
      </div>
    `;
  } catch (error) { 
    console.error('Report generation error:', error);
    output.innerHTML = `
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 24px;">❌</div>
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--error);">报告生成失败</div>
            <div style="font-size: 13px; color: var(--text-secondary);">${error.message}</div>
          </div>
        </div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(220, 38, 38, 0.2);">
          <button class="btn btn-sm btn-secondary" onclick="generateReport('${format}')">重试</button>
        </div>
      </div>
    `; 
  }
}
function selectProject(projectId) { state.currentProject = projectId; localStorage.setItem('splicegaip.currentProject', projectId); loadDashboard(); }
function refreshData() { if (state.currentPage === 'dashboard') loadDashboard(); if (state.currentPage === 'pipeline') loadPipeline(); if (state.currentPage === 'explorer') loadExplorer(); }

// Upload Modal Functions
let selectedFiles = [];

function showUploadModal() {
  document.getElementById('upload-modal').style.display = 'flex';
  selectedFiles = [];
  updateFileList();
}

function closeUploadModal() {
  document.getElementById('upload-modal').style.display = 'none';
  document.getElementById('project-name').value = '';
  document.getElementById('analysis-query').value = '';
  selectedFiles = [];
  updateFileList();
}

function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--accent)';
  dropZone.style.background = '#eff6ff';
}

function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--border)';
  dropZone.style.background = '';
}

function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--border)';
  dropZone.style.background = '';
  
  const files = Array.from(event.dataTransfer.files);
  handleFiles(files);
}

function handleFileSelect(event) {
  console.log('handleFileSelect called');
  console.log('event.target:', event.target);
  console.log('event.target.files:', event.target.files);
  
  const files = Array.from(event.target.files);
  console.log('Converted files array:', files.length, files);
  
  handleFiles(files);
}

function handleFiles(files) {
  console.log('handleFiles called with', files.length, 'files');
  selectedFiles = [...selectedFiles, ...files];
  console.log('selectedFiles now:', selectedFiles.length, selectedFiles.map(f => f.name));
  updateFileList();
}

function updateFileList() {
  const fileListDiv = document.getElementById('file-list');
  const startBtn = document.getElementById('start-analysis-btn');
  
  if (selectedFiles.length === 0) {
    fileListDiv.innerHTML = '';
    startBtn.disabled = true;
  } else {
    fileListDiv.innerHTML = selectedFiles.map((file, index) => 
      `<div style="padding: 8px; background: var(--bg); border-radius: var(--radius); margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 13px;">${file.name}</span>
        <button onclick="removeFile(${index})" style="background: none; border: none; cursor: pointer; color: var(--error); font-size: 18px;">×</button>
      </div>`
    ).join('');
    startBtn.disabled = false;
  }
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  updateFileList();
}

async function startAnalysis() {
  const projectName = document.getElementById('project-name').value.trim();
  const analysisQuery = document.getElementById('analysis-query').value.trim();
  
  if (!projectName) {
    alert('请输入项目名称');
    return;
  }
  
  if (!analysisQuery) {
    alert('请输入分析查询');
    return;
  }
  
  if (selectedFiles.length === 0) {
    alert('请至少选择一个文件');
    return;
  }
  
  // Save files reference BEFORE closing modal (closeUploadModal clears selectedFiles)
  const filesToUpload = [...selectedFiles];
  
  // Close modal and show loading
  closeUploadModal();
  const statusDiv = document.getElementById('stat-status');
  statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>上传中...</span>';
  
  try {
    // Step 1: Upload files
    const formData = new FormData();
    
    console.log('Uploading files count:', filesToUpload.length);
    console.log('Files to upload:', filesToUpload.map(f => f.name));
    
    filesToUpload.forEach((file, index) => {
      console.log(`Adding file ${index}:`, file.name, file.type, file.size);
      formData.append('files', file, file.name);
    });
    
    // Verify FormData contents
    for (let [key, value] of formData.entries()) {
      console.log('FormData entry:', key, value.name, value.size);
    }
    
    const uploadResponse = await fetch('/api/upload', {
      method: 'POST',
      body: formData
      // Don't set Content-Type header - browser will set it with boundary
    });
    
    console.log('Upload response status:', uploadResponse.status);
    
    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      console.error('Upload error response:', errorText);
      throw new Error(`上传失败 (${uploadResponse.status}): ${errorText}`);
    }
    
    const uploadResult = await uploadResponse.json();
    const uploadDir = uploadResult.upload_dir;
    
    console.log('Files uploaded to:', uploadDir);
    
    // Step 2: let the ingestion agent read the table structure before analysis.
    statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>智能体正在理解数据结构...</span>';
    let preview = null;
    try {
      const previewResponse = await fetch('/api/ingest/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_dir: uploadDir, use_llm: true })
      });
      if (previewResponse.ok) {
        preview = await previewResponse.json();
      } else {
        console.warn('ingest preview rejected:', previewResponse.status, await previewResponse.text());
      }
    } catch (previewError) {
      console.warn('ingest preview unavailable:', previewError);
    }

    if (preview && preview.native && (!preview.validation || preview.validation.ok) && !(preview.sample_ids || []).length) {
      statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>已识别标准格式，开始分析...</span>';
      runAnalysisOnDir(analysisQuery, uploadDir, projectName, statusDiv);
      return;
    }
    if (preview) {
      statusDiv.dataset.ingestPending = '1';
      statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>等待确认数据映射...</span>';
      showIngestModal(preview, { uploadDir: uploadDir, projectName: projectName, analysisQuery: analysisQuery, statusDiv: statusDiv });
      return;
    }
    runAnalysisOnDir(analysisQuery, uploadDir, projectName, statusDiv);

  } catch (error) {
    console.error('Analysis error:', error);
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
    alert(`操作失败：${error.message}\n\n请检查：\n1. 文件格式是否正确\n2. 文件大小是否过大\n3. 网络连接是否正常`);
  }
}

function runAnalysisOnDir(analysisQuery, inputDir, projectName, statusDiv) {
  const prevLatest = (state.projects && state.projects[0] && state.projects[0].project_id) || null;
  statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>分析中（预计 3-6 分钟）...</span>';
  navigateTo('pipeline');

  const pollTimer = setInterval(async () => {
    try {
      const resp = await apiCall('/projects');
      const list = (resp && resp.projects) || [];
      if (list.length > 0 && list[0].project_id !== prevLatest && state.currentProject !== list[0].project_id) {
        state.currentProject = list[0].project_id;
        localStorage.setItem('splicegaip.currentProject', state.currentProject);
        document.getElementById('current-project').textContent = state.currentProject;
      }
      if (state.currentProject) loadPipeline();
    } catch (pollError) { console.warn('poll error:', pollError); }
  }, 4000);

  fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: analysisQuery, input_dir: inputDir, project_name: projectName })
  }).then(async analyzeResponse => {
    clearInterval(pollTimer);
    if (!analyzeResponse.ok) {
      const errorText = await analyzeResponse.text();
      statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
      alert(`分析失败 (${analyzeResponse.status}): ${errorText}`);
      return;
    }
    const analyzeResult = await analyzeResponse.json();
    if (analyzeResult && analyzeResult.project_id) {
      state.currentProject = analyzeResult.project_id;
      localStorage.setItem('splicegaip.currentProject', state.currentProject);
      document.getElementById('current-project').textContent = state.currentProject;
    }
    statusDiv.innerHTML = '<span class="status status-completed"><span class="status-dot"></span>已完成</span>';
    loadPipeline();
    loadDashboard();
    alert('分析完成！可在事件浏览器、可视化和报告页面查看结果。');
  }).catch(fetchError => {
    clearInterval(pollTimer);
    console.error('Analysis request error:', fetchError);
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
    alert(`分析请求失败：${fetchError.message}（分析可能仍在后台运行，请稍后刷新查看）`);
  });
}

// ---------------------------------------------------------------------------
// Smart ingestion review
// ---------------------------------------------------------------------------
let ingestState = null;

const INGEST_STEP_LABELS = {
  profile: ['文件画像', 'Profiling'],
  heuristic: ['规则映射', 'Rule mapping'],
  llm: ['模型映射', 'LLM mapping'],
  validate: ['标准化', 'Standardization'],
  preview: ['置信度', 'Confidence']
};

function ingestT(zh, en) { return cfgText(zh, en); }

function ingestEsc(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function ingestLevel(level) {
  if (level === 'high') return ingestT('高', 'high');
  if (level === 'medium') return ingestT('中', 'medium');
  return ingestT('低', 'low');
}

function ingestDelimiter(value) {
  if (value === String.fromCharCode(9)) return 'TAB';
  if (value === ',') return 'CSV';
  return value || '—';
}

function ingestFixed(value, digits) {
  const num = Number(value);
  if (value === null || value === undefined || value === '' || !isFinite(num)) return '—';
  return num.toFixed(digits);
}

function ingestSci(value) {
  const num = Number(value);
  if (value === null || value === undefined || value === '' || !isFinite(num)) return '—';
  if (num === 0) return '0';
  return num.toExponential(2);
}

function ingestTraceSteps(trace) {
  const order = [];
  const byName = {};
  (trace || []).forEach(function (step) {
    if (!step || !step.step) return;
    if (!byName[step.step]) order.push(step.step);
    byName[step.step] = step;
  });
  return order.map(function (name) { return byName[name]; });
}

function showIngestModal(data, context) {
  ingestState = {
    data: data,
    context: context,
    mapping: JSON.parse(JSON.stringify(data.mapping || {})),
    applying: false,
    groupLabels: []
  };
  if (!ingestState.mapping.columns) ingestState.mapping.columns = {};
  if (!ingestState.mapping.sample_groups) ingestState.mapping.sample_groups = {};
  const suggested = [...new Set(Object.values(ingestState.mapping.sample_groups).filter(Boolean))];
  ingestState.groupLabels = [suggested[0] || 'Control', suggested[1] || 'Treatment'];
  const modal = document.getElementById('ingest-modal');
  if (modal) modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  renderIngestModal();
  const confirmBtn = document.getElementById('ingest-confirm');
  if (confirmBtn && !confirmBtn.disabled) confirmBtn.focus();
}

function closeIngestModal() {
  if (ingestState && ingestState.applying) return;
  const statusDiv = ingestState && ingestState.context ? ingestState.context.statusDiv : null;
  const modal = document.getElementById('ingest-modal');
  if (modal) modal.classList.remove('open');
  document.body.style.overflow = '';
  if (statusDiv && statusDiv.dataset.ingestPending === '1') {
    delete statusDiv.dataset.ingestPending;
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
  }
  ingestState = null;
}

function renderIngestModal() {
  if (!ingestState) return;
  const data = ingestState.data || {};
  const preview = data.preview || {};
  const issues = data.issues || [];
  const native = !!data.native;
  const unmappable = data.status === 'unmappable';

  const title = document.getElementById('ingest-title');
  const sub = document.getElementById('ingest-sub');
  const body = document.getElementById('ingest-body');
  const confirmBtn = document.getElementById('ingest-confirm');
  const cancelBtn = document.getElementById('ingest-cancel');
  const errorDiv = document.getElementById('ingest-error');
  if (!body || !confirmBtn) return;

  let subText = ingestT('Agent 已读取数据结构。确认字段映射后，将标准化并进入原有分析流程。', 'The agent has read the data structure. Confirm the field mapping to standardize and continue to analysis.');
  if (native) subText = ingestT('请核对每个样本的分组，确认后开始分析。', 'Review each sample group before analysis.');
  if (unmappable) subText = ingestT('未能从这些文件中识别出可分析的剪接事件表。', 'No analyzable splicing event table could be recognized in these files.');
  if (title) title.textContent = ingestT('智能接入检查', 'Smart ingestion review');
  if (sub) sub.textContent = subText;
  if (errorDiv) errorDiv.textContent = '';

  const html = [];
  const steps = ingestTraceSteps(data.agent_trace);
  if (steps.length) {
    html.push('<div class="ingest-trace">' + steps.map(function (step) {
      const labels = INGEST_STEP_LABELS[step.step] || [step.step, step.step];
      const detail = ingestT(step.detail || '', step.detail_en || step.detail || '');
      return '<span class="ingest-step ' + ingestEsc(step.status || 'ok') + '" title="' + ingestEsc(detail) + '"><span class="dot"></span>' + ingestEsc(ingestT(labels[0], labels[1])) + '</span>';
    }).join('') + '</div>');
  }

  const sourceBits = [];
  if (native) {
    sourceBits.push(ingestT('原生格式：', 'Native format: ') + ingestEsc(data.native_format || 'standard'));
  } else {
    sourceBits.push(ingestT('映射来源：', 'Mapping source: ') + (data.mapping_source === 'llm+heuristic' ? ingestT('大模型 + 规则', 'LLM + rules') : ingestT('确定性规则', 'Deterministic rules')));
    const confidence = data.confidence || {};
    sourceBits.push(ingestT('置信度：', 'Confidence: ') + ingestLevel(confidence.level) + ' · ' + Math.round(Number(confidence.score || 0) * 100) + '%');
  }
  if (data.elapsed_ms !== undefined && data.elapsed_ms !== null) sourceBits.push(ingestT('用时 ', 'took ') + Number(data.elapsed_ms) + ' ms');
  html.push('<div class="ingest-source">' + sourceBits.join(' · ') + '</div>');

  const validEvents = preview.valid_events !== undefined ? preview.valid_events : ((data.summary && data.summary.event_count) || 0);
  const sampleCount = preview.sample_count !== undefined ? preview.sample_count : ((data.summary && data.summary.sample_count) || 0);
  const fdrCoverage = preview.fdr_coverage !== undefined ? preview.fdr_coverage : 0;
  const deltaCoverage = preview.delta_coverage !== undefined ? preview.delta_coverage : 0;
  html.push('<div class="ingest-stats">' +
    '<div class="ingest-stat"><div class="v">' + ingestEsc(validEvents) + '</div><div class="k">' + ingestEsc(ingestT('有效事件', 'Valid events')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + ingestEsc(sampleCount) + '</div><div class="k">' + ingestEsc(ingestT('样本', 'Samples')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + Math.round(Number(fdrCoverage) * 100) + '%</div><div class="k">' + ingestEsc(ingestT('FDR 覆盖', 'FDR coverage')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + Math.round(Number(deltaCoverage) * 100) + '%</div><div class="k">' + ingestEsc(ingestT('ΔPSI 覆盖', 'ΔPSI coverage')) + '</div></div>' +
    '</div>');

  if (!native && data.event_file) {
    const eventFile = data.event_file;
    const metaFile = data.metadata_file;
    const rows = Number(eventFile.row_count || 0);
    const line = ingestT('事件表', 'Event table') + ' <code>' + ingestEsc(eventFile.name) + '</code> · ' + ingestDelimiter(eventFile.delimiter) + ' · ' + ingestT('表头第 ', 'header row ') + (Number(eventFile.header_row || 0) + 1) + ' · ' + rows + ingestT(' 行', ' rows');
    const metaLine = ingestT('样本表', 'Sample table') + ' <code>' + ingestEsc(metaFile ? metaFile.name : '—') + '</code>' + (metaFile ? '' : ' ' + ingestT('（未提供，已根据样本名推断分组）', '(not provided; groups inferred from sample names)'));
    const typeCounts = preview.event_types || {};
    const typeText = Object.keys(typeCounts).map(function (key) { return key + ' ' + typeCounts[key]; }).join(' · ');
    html.push('<div class="ingest-files"><div>' + line + '</div><div>' + metaLine + '</div>' + (typeText ? '<div>' + ingestEsc(ingestT('事件类型：', 'Event types: ') + typeText) + '</div>' : '') + '</div>');
  }

  if (unmappable && Array.isArray(data.files) && data.files.length) {
    const fileLines = data.files.map(function (file) {
      const suffix = file.supported ? ingestT('可解析', 'parseable') : ingestT('不可解析', 'not parseable');
      return '<div><code>' + ingestEsc(file.name) + '</code> · ' + suffix + (file.error ? ' · ' + ingestEsc(file.error) : '') + '</div>';
    });
    html.push('<div class="ingest-files">' + fileLines.join('') + '</div>');
  }

  if (!native && Array.isArray(data.mapping_fields) && data.mapping_fields.length && data.event_file) {
    const headers = data.event_file.headers || [];
    const columns = (data.mapping && data.mapping.columns) || {};
    const rows = data.mapping_fields.map(function (field) {
      const current = columns[field.field] || '';
      const label = ingestT(field.label_zh || field.field, field.label_en || field.field) + (field.required ? ' *' : '');
      let options = '<option value="">' + ingestEsc(ingestT('— 未映射 —', '— unmapped —')) + '</option>';
      let found = false;
      headers.forEach(function (header) {
        if (header === current) found = true;
        options += '<option value="' + ingestEsc(header) + '"' + (header === current ? ' selected' : '') + '>' + ingestEsc(header) + '</option>';
      });
      if (current && !found) options += '<option value="' + ingestEsc(current) + '" selected>' + ingestEsc(current) + '</option>';
      const missing = field.required && !current ? ' missing' : '';
      return '<div class="ingest-map-row"><label>' + ingestEsc(label) + '</label><select data-field="' + ingestEsc(field.field) + '"' + (field.required ? ' data-required="1"' : '') + ' onchange="ingestSelectChanged(this)"' + (missing ? ' class="missing"' : '') + '>' + options + '</select></div>';
    });
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('字段映射', 'Field mapping')) + '</div><div class="ingest-map-grid">' + rows.join('') + '</div></div>');
  }

  const sampleIds = data.sample_ids || [];
  if (sampleIds.length) {
    const labels = ingestState.groupLabels;
    const assignments = ingestState.mapping.sample_groups;
    const assignedCount = sampleIds.filter(id => !!assignments[id]).length;
    const source = data.group_suggestion_source;
    const sourceText = source === 'previous_metadata'
      ? ingestT('已从相同事件文件的历史样本表恢复分组建议。', 'Group suggestions were restored from a previous sample sheet for the identical event file.')
      : source === 'metadata'
        ? ingestT('已读取上传的样本表。', 'Groups were read from the uploaded sample sheet.')
        : source === 'llm' || data.mapping_source === 'llm+heuristic'
          ? ingestT('大模型已提出分组建议，请核对。', 'The model suggested sample groups; please review them.')
          : ingestT('尚无可靠的完整分组建议，可修改分组名称并批量分配。', 'No complete reliable grouping was found; you can edit group names and assign samples in batches.');
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('样本分组确认', 'Confirm sample groups')) + '</div>' +
      '<div style="margin:8px 0;color:var(--text-secondary)">' + ingestEsc(sourceText) + ' ' + assignedCount + '/' + sampleIds.length + '</div>' +
      '<div style="display:flex;gap:8px;margin:8px 0"><input data-group-label="0" value="' + ingestEsc(labels[0]) + '" oninput="ingestGroupLabelChanged(this)" aria-label="Group 1" placeholder="Group 1" style="width:48%;padding:8px"><input data-group-label="1" value="' + ingestEsc(labels[1]) + '" oninput="ingestGroupLabelChanged(this)" aria-label="Group 2" placeholder="Group 2" style="width:48%;padding:8px"></div>' +
      '<div style="display:flex;gap:8px;margin:8px 0"><button type="button" class="btn btn-sm btn-secondary" onclick="ingestAssignUnassigned(0)">' + ingestEsc(ingestT('未分配项 → 第一组', 'Unassigned → group 1')) + '</button><button type="button" class="btn btn-sm btn-secondary" onclick="ingestAssignUnassigned(1)">' + ingestEsc(ingestT('未分配项 → 第二组', 'Unassigned → group 2')) + '</button></div>' +
      '<details' + (assignedCount < sampleIds.length ? ' open' : '') + '><summary style="cursor:pointer;margin:8px 0">' + ingestEsc(ingestT('查看或调整逐样本分组', 'Review or edit individual samples')) + '</summary><div class="ingest-map-grid">' + sampleIds.map(function (sampleId) {
        const current = assignments[sampleId] || '';
        return '<div class="ingest-map-row"><label>' + ingestEsc(sampleId) + '</label><select data-sample-id="' + ingestEsc(sampleId) + '" onchange="ingestGroupChanged(this)"><option value="">' + ingestEsc(ingestT('— 请选择 —', '— Select —')) + '</option><option value="0"' + (current === labels[0] ? ' selected' : '') + '>' + ingestEsc(labels[0]) + '</option><option value="1"' + (current === labels[1] ? ' selected' : '') + '>' + ingestEsc(labels[1]) + '</option></select></div>';
      }).join('') + '</div></details></div>');
  } else {
    html.push('<div class="ingest-issue warning">' + ingestEsc(ingestT('没有每样本 PSI 数据，无法生成真实的样本箱线图或热图。', 'No per-sample PSI data: sample box plots and heatmaps cannot be generated.')) + '</div>');
  }

  if (issues.length) {
    const items = issues.map(function (issue) {
      const severity = issue.severity === 'error' ? 'error' : (issue.severity === 'warning' ? 'warning' : 'info');
      const tag = severity === 'error' ? ingestT('错误', 'ERROR') : (severity === 'warning' ? ingestT('提示', 'WARN') : ingestT('信息', 'INFO'));
      const message = ingestT(issue.message || '', issue.message_en || issue.message || '');
      return '<div class="ingest-issue ' + severity + '"><span class="tag">' + ingestEsc(tag) + '</span><span>' + ingestEsc(message) + '</span></div>';
    });
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('检查结果', 'Checks')) + '</div><div class="ingest-issues">' + items.join('') + '</div></div>');
  }

  const sampleEvents = preview.events || [];
  if (sampleEvents.length) {
    const head = ingestT('事件 ID', 'Event ID') + '</th><th>' + ingestT('基因', 'Gene') + '</th><th>' + ingestT('类型', 'Type') + '</th><th>ΔPSI</th><th>FDR</th><th>' + ingestT('坐标', 'Coordinates');
    const rows = sampleEvents.map(function (event) {
      return '<tr><td>' + ingestEsc(event.event_id) + '</td><td>' + ingestEsc(event.gene) + '</td><td>' + ingestEsc(event.event_type) + '</td><td>' + ingestFixed(event.delta_psi, 3) + '</td><td>' + ingestSci(event.fdr) + '</td><td>' + ingestEsc(event.coordinates) + '</td></tr>';
    }).join('');
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('标准化预览（前 5 行）', 'Standardized preview (first 5 rows)')) + '</div><div class="ingest-preview-table"><table><thead><tr><th>' + head + '</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>');
  }

  const privacy = ingestT(data.privacy || '', data.privacy_en || data.privacy || '');
  if (privacy && !native) html.push('<div class="ingest-privacy">' + ingestEsc(privacy) + '</div>');

  body.innerHTML = html.join('');

  if (cancelBtn) cancelBtn.textContent = ingestT('取消', 'Cancel');
  if (!ingestState.applying) {
    if (unmappable || (native && data.validation && !data.validation.ok)) {
      confirmBtn.disabled = true;
      confirmBtn.textContent = unmappable
        ? ingestT('无法自动标准化', 'Cannot standardize')
        : ingestT('数据校验未通过', 'Validation failed');
    } else {
      updateIngestConfirmState();
    }
  }
}

function ingestSelectChanged(select) {
  if (!ingestState) return;
  if (!ingestState.mapping.columns) ingestState.mapping.columns = {};
  const field = select.getAttribute('data-field');
  if (!field) return;
  if (select.value) ingestState.mapping.columns[field] = select.value;
  else delete ingestState.mapping.columns[field];
  if (select.getAttribute('data-required') === '1') select.classList.toggle('missing', !select.value);
  updateIngestConfirmState();
}

function ingestGroupChanged(select) {
  if (!ingestState) return;
  const sampleId = select.getAttribute('data-sample-id');
  ingestState.mapping.sample_groups[sampleId] = select.value === '' ? '' : ingestState.groupLabels[Number(select.value)];
  updateIngestConfirmState();
}

function ingestAssignUnassigned(index) {
  if (!ingestState) return;
  const label = ingestState.groupLabels[index];
  (ingestState.data.sample_ids || []).forEach(function (id) {
    if (!ingestState.mapping.sample_groups[id]) ingestState.mapping.sample_groups[id] = label;
  });
  renderIngestModal();
}

function ingestGroupLabelChanged(input) {
  if (!ingestState) return;
  const index = Number(input.getAttribute('data-group-label'));
  const oldLabel = ingestState.groupLabels[index];
  const newLabel = input.value.trim();
  ingestState.groupLabels[index] = newLabel;
  Object.keys(ingestState.mapping.sample_groups).forEach(function (id) {
    if (ingestState.mapping.sample_groups[id] === oldLabel) ingestState.mapping.sample_groups[id] = newLabel;
  });
  document.querySelectorAll('#ingest-body select[data-sample-id]').forEach(function (select) {
    select.options[index + 1].textContent = newLabel;
  });
  updateIngestConfirmState();
}

function updateIngestConfirmState() {
  if (!ingestState) return;
  const data = ingestState.data || {};
  if (data.status === 'unmappable') return;
  const confirmBtn = document.getElementById('ingest-confirm');
  if (!confirmBtn || ingestState.applying) return;
  const columns = {};
  document.querySelectorAll('#ingest-body select[data-field]').forEach(function (select) {
    if (select.value) columns[select.getAttribute('data-field')] = select.value;
  });
  const preview = data.preview || {};
  const validation = preview.validation || data.validation || {};
  const sampleIds = data.sample_ids || [];
  const groupLabels = ingestState.groupLabels || [];
  const groupsReady = !sampleIds.length || (groupLabels[0] && groupLabels[1] && groupLabels[0] !== groupLabels[1] && sampleIds.every(id => groupLabels.includes(ingestState.mapping.sample_groups[id])) && new Set(sampleIds.map(id => ingestState.mapping.sample_groups[id])).size === 2);
  const missingGene = !columns.gene_symbol && !columns.gene_id;
  const hasDelta = !!columns.delta_PSI || (!!columns.mean_PSI_group1 && !!columns.mean_PSI_group2) || Number(preview.sample_psi_columns || 0) > 0;
  const hasSignificance = !!columns.FDR || !!columns.p_value;
  const ready = groupsReady && (data.native ? Number(validation.error_count || 0) === 0 : (!missingGene && hasDelta && hasSignificance));
  confirmBtn.disabled = !ready;
  confirmBtn.textContent = ready ? ingestT('确认映射并分析', 'Confirm & analyze') : ingestT('请先补全映射', 'Complete the mapping');
}

async function confirmIngest() {
  if (!ingestState || ingestState.applying) return;
  const data = ingestState.data || {};
  const ctx = ingestState.context || {};
  const errorDiv = document.getElementById('ingest-error');
  const confirmBtn = document.getElementById('ingest-confirm');
  if (errorDiv) errorDiv.textContent = '';

  if (data.native) {
    const sampleIds = data.sample_ids || [];
    const groups = ingestState.mapping.sample_groups || {};
    if (sampleIds.length && (sampleIds.some(id => !groups[id]) || new Set(sampleIds.map(id => groups[id])).size !== 2)) {
      if (errorDiv) errorDiv.textContent = ingestT('请为每个样本选择分组，并确保两组都有样本。', 'Assign every sample and include both groups.');
      return;
    }
    if (!sampleIds.length) { closeIngestModal(); runAnalysisOnDir(ctx.analysisQuery, ctx.uploadDir, ctx.projectName, ctx.statusDiv); return; }
    ingestState.applying = true;
    if (confirmBtn) confirmBtn.disabled = true;
    try {
      const response = await fetch('/api/ingest/groups', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({input_dir:ctx.uploadDir,sample_groups:groups})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'HTTP ' + response.status);
      ingestState.applying = false;
      closeIngestModal();
      runAnalysisOnDir(ctx.analysisQuery, result.path, ctx.projectName, ctx.statusDiv);
    } catch (error) {
      ingestState.applying = false;
      if (errorDiv) errorDiv.textContent = error.message;
      updateIngestConfirmState();
    }
    return;
  }

  const columns = {};
  const selects = document.querySelectorAll('#ingest-body select[data-field]');
  for (let i = 0; i < selects.length; i++) {
    const field = selects[i].getAttribute('data-field');
    if (field && selects[i].value) columns[field] = selects[i].value;
  }
  const mappedFields = {};
  (data.mapping_fields || []).forEach(function (field) { mappedFields[field.field] = true; });
  const originalColumns = (data.mapping && data.mapping.columns) || {};
  Object.keys(originalColumns).forEach(function (key) {
    if (!mappedFields[key]) columns[key] = originalColumns[key];
  });

  if (!columns.gene_symbol && !columns.gene_id) {
    if (errorDiv) errorDiv.textContent = ingestT('请至少映射基因符号或基因 ID。', 'Map at least a gene symbol or gene ID column.');
    return;
  }
  const preview = data.preview || {};
  const hasDelta = !!columns.delta_PSI || (!!columns.mean_PSI_group1 && !!columns.mean_PSI_group2) || Number(preview.sample_psi_columns || 0) > 0;
  if (!hasDelta) {
    if (errorDiv) errorDiv.textContent = ingestT('请映射 ΔPSI，或同时映射两组平均 PSI。', 'Map delta PSI, or both group mean PSI columns.');
    return;
  }
  if (!columns.FDR && !columns.p_value) {
    if (errorDiv) errorDiv.textContent = ingestT('请映射 FDR 或 p 值，否则无法筛选显著事件。', 'Map an FDR or p-value column so significant events can be selected.');
    return;
  }

  const mapping = JSON.parse(JSON.stringify(data.mapping || {}));
  mapping.columns = columns;
  mapping.sample_groups = ingestState.mapping.sample_groups;
  mapping.sample_groups_confirmed = (data.sample_ids || []).length > 0;
  if (data.event_file && data.event_file.name) mapping.event_file = data.event_file.name;

  ingestState.applying = true;
  if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = ingestT('标准化中…', 'Standardizing…'); }
  try {
    const response = await fetch('/api/ingest/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_dir: ctx.uploadDir, mapping: mapping })
    });
    let result = {};
    try { result = await response.json(); } catch (parseError) { result = {}; }
    if (!response.ok) {
      const detail = result && result.detail;
      const message = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : 'HTTP ' + response.status);
      throw new Error(message);
    }
    const statusDiv = ctx.statusDiv || document.getElementById('stat-status');
    ingestState.applying = false;
    closeIngestModal();
    statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>标准化完成，开始分析...</span>';
    runAnalysisOnDir(ctx.analysisQuery, result.path, ctx.projectName, statusDiv);
  } catch (error) {
    ingestState.applying = false;
    if (errorDiv) errorDiv.textContent = ingestT('标准化失败：', 'Standardization failed: ') + error.message;
    if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = ingestT('确认映射并分析', 'Confirm & analyze'); }
  }
}

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && ingestState) closeIngestModal();
});

document.addEventListener('splicegaip:language', function () {
  if (ingestState) renderIngestModal();
});

function viewEventDetails(eventId) { 
  const event = state.events.find(e => (e.event_id || e.id) === eventId);
  if (!event) { alert('事件未找到'); return; }
  
  const gene = event.gene_symbol || event.gene || 'Unknown';
  const eventType = event.event_type || event.type || 'Unknown';
  const dpsi = event.delta_psi !== null && event.delta_psi !== undefined ? Number(event.delta_psi).toFixed(4) : 'N/A';
  const fdr = event.fdr !== null && event.fdr !== undefined ? Number(event.fdr).toExponential(3) : 'N/A';
  const pValue = event.p_value !== null && event.p_value !== undefined ? Number(event.p_value).toExponential(3) : 'N/A';
  const score = event.score !== null && event.score !== undefined ? Number(event.score).toFixed(3) : 'N/A';
  
  // Determine significance level
  let sigLevel = 'ns';
  let sigColor = '#94a3b8';
  if (fdr !== 'N/A') {
    const fdrNum = parseFloat(fdr);
    if (fdrNum < 0.001) { sigLevel = '***'; sigColor = '#dc2626'; }
    else if (fdrNum < 0.01) { sigLevel = '**'; sigColor = '#f59e0b'; }
    else if (fdrNum < 0.05) { sigLevel = '*'; sigColor = '#059669'; }
  }
  
  // Biological interpretation based on delta PSI
  let biologicalImpact = '';
  let impactColor = '';
  const dpsiAbs = Math.abs(parseFloat(dpsi));
  if (dpsi !== 'N/A') {
    if (dpsiAbs > 0.3) { biologicalImpact = '强效应 - 可能导致蛋白质功能重大改变'; impactColor = '#dc2626'; }
    else if (dpsiAbs > 0.15) { biologicalImpact = '中等效应 - 可能影响蛋白质结构域'; impactColor = '#f59e0b'; }
    else if (dpsiAbs > 0.05) { biologicalImpact = '弱效应 - 可能对功能有轻微影响'; impactColor = '#059669'; }
    else { biologicalImpact = '微小效应 - 可能无显著生物学影响'; impactColor = '#94a3b8'; }
  }
  
  // Event type descriptions
  const eventDescriptions = {
    'SE': '外显子跳跃 (Skipped Exon): 最常见的外显子类型，可能导致蛋白质结构域缺失',
    'MXE': '互斥外显子 (Mutually Exclusive Exons): 两个相邻外显子中只保留一个',
    'A3SS': "可变3'剪接位点 (Alternative 3' Splice Site): 影响外显子3'端边界",
    'A5SS': "可变5'剪接位点 (Alternative 5' Splice Site): 影响外显子5'端边界",
    'RI': '内含子保留 (Retained Intron): 内含子未被正确移除'
  };
  
  const eventDesc = eventDescriptions[eventType] || '未知剪接事件类型';
  
  // Create modal HTML
  const modalHTML = `
    <div id="event-detail-modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--white); z-index: 2000; display: flex; align-items: center; justify-content: center;">
      <div style="background: var(--white); border: 1px solid var(--gray-300); border-radius: var(--radius); padding: 0; max-width: 900px; width: 95%; max-height: 90vh; overflow-y: auto;">
        <!-- Header -->
        <div style="background: var(--black); padding: 32px; color: white; position: relative;">
          <button onclick="closeEventModal()" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border: none; width: 36px; height: 36px; border-radius: 50%; color: white; font-size: 24px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">×</button>
          <div style="font-size: 28px; font-weight: 600; margin-bottom: 8px;">${gene}</div>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 500;">${eventType}</span>
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 500;">FDR ${fdr} ${sigLevel}</span>
          </div>
        </div>
        
        <!-- Content -->
        <div style="padding: 32px;">
          <!-- Key Metrics -->
          <div class="grid grid-3" style="margin-bottom: 28px;">
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">Delta PSI</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${dpsi}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">FDR</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${fdr}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">评分</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${score}</div>
            </div>
          </div>
          
          <!-- Biological Impact -->
          <div style="background: var(--gray-100); border-left: 2px solid var(--gray-700); padding: 20px; border-radius: var(--radius); margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-900); margin-bottom: 8px;">生物学影响评估</div>
            <div style="font-size: 14px; line-height: 1.7; color: var(--gray-900);">${biologicalImpact}</div>
          </div>
          
          <!-- Event Description -->
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">事件类型说明</div>
            <div style="font-size: 14px; line-height: 1.7; color: var(--gray-900); padding: 16px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius);">${eventDesc}</div>
          </div>
          
          <!-- Statistical Details -->
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">统计详情</div>
            <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700); width: 40%;">P值</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${pValue}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">Delta PSI</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${dpsi}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">FDR校正值</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${fdr}</td>
              </tr>
              <tr>
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">综合评分</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${score}</td>
              </tr>
            </table>
          </div>
          
          <!-- Literature Evidence -->
          ${event.evidence_json ? `
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">文献证据</div>
            <div style="padding: 20px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; line-height: 1.7; color: var(--gray-900);" id="evidence-content">加载中...</div>
          </div>
          ` : '<div style="padding: 20px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; color: var(--gray-500); text-align: center; margin-bottom: 24px;">暂无文献证据</div>'}
          
          <!-- Action Buttons -->
          <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 28px; padding-top: 24px; border-top: 1px solid var(--border);">
            <button class="btn btn-secondary" onclick="closeEventModal()">关闭</button>
            <button class="btn btn-primary" onclick="viewGeneInBrowser('${gene}')">查看基因详情</button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHTML);
  
  // Load evidence if available
  if (event.evidence_json) {
    setTimeout(() => {
      try {
        const evidence = typeof event.evidence_json === 'string' ? JSON.parse(event.evidence_json) : event.evidence_json;
        const evidenceDiv = document.getElementById('evidence-content');
        if (Array.isArray(evidence)) {
          evidenceDiv.innerHTML = evidence.map(item => `<div style="margin-bottom: 8px;">• ${item}</div>`).join('');
        } else if (typeof evidence === 'object') {
          evidenceDiv.innerHTML = Object.entries(evidence).map(([k, v]) => `<div style="margin-bottom: 8px;"><strong>${k}:</strong> ${v}</div>`).join('');
        } else {
          evidenceDiv.textContent = evidence;
        }
      } catch (e) {
        document.getElementById('evidence-content').textContent = event.evidence_json;
      }
    }, 100);
  }
}

function closeEventModal() {
  const modal = document.getElementById('event-detail-modal');
  if (modal) {
    modal.style.animation = 'fadeOut 0.3s';
    setTimeout(() => modal.remove(), 300);
  }
}

function viewGeneInBrowser(geneSymbol) {
  closeEventModal();
  navigateTo('gene');
  document.getElementById('gene-search').value = geneSymbol;
  exploreGene();
}

// ==================== AI Assistant Functions ====================

// ==================== MCP Tool Console ====================
const mcpState = { servers: {}, configPath: '', selectedServer: '', tools: [], loading: false };

function mcpStatusBadge(text, kind) {
  const badge = document.getElementById('mcp-status');
  if (!badge) return;
  badge.textContent = text;
  badge.className = 'mcp-badge' + (kind ? ' ' + kind : '');
}

async function loadMcpServers(force) {
  if (mcpState.loading) return;
  mcpState.loading = true;
  mcpStatusBadge('连接中…', '');
  document.getElementById('mcp-server-hint').textContent = '正在连接 MCP 服务器…';
  try {
    const response = await fetch('/api/mcp/servers' + (force ? '?refresh=1' : ''));
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    mcpState.servers = data.servers || {};
    mcpState.configPath = data.config_path || '';
    renderMcpServers();
  } catch (error) {
    mcpStatusBadge('连接失败', 'err');
    document.getElementById('mcp-server-hint').textContent = String(error);
    document.getElementById('mcp-server-select').innerHTML = '<option value="">无法读取 MCP 配置</option>';
    document.getElementById('mcp-tool-select').innerHTML = '<option value="">—</option>';
  } finally {
    mcpState.loading = false;
  }
}

function renderMcpServers() {
  const select = document.getElementById('mcp-server-select');
  const names = Object.keys(mcpState.servers);
  const connected = names.filter(function (name) { return mcpState.servers[name].status === 'connected'; });
  if (!names.length) {
    mcpStatusBadge('未配置', 'err');
    select.innerHTML = '<option value="">未配置 MCP 服务器</option>';
    document.getElementById('mcp-server-hint').textContent = '在 ' + (mcpState.configPath || '~/.splicegaip/mcp/servers.json') + ' 中添加服务器';
    return;
  }
  const previous = mcpState.selectedServer;
  select.innerHTML = '';
  names.forEach(function (name) {
    const server = mcpState.servers[name];
    const option = document.createElement('option');
    const toolCount = (server.tools || []).length;
    const tag = server.builtin ? '内置' : (server.via || server.transport || 'MCP');
    option.value = name;
    option.textContent = name + ' · ' + tag + ' · ' + toolCount + ' 工具' + (server.status === 'connected' ? '' : '（未连接）');
    option.disabled = server.status !== 'connected';
    select.appendChild(option);
  });
  const preferred = (connected.indexOf(previous) >= 0 ? previous : connected[0]) || '';
  select.value = preferred;
  mcpState.selectedServer = preferred;
  if (connected.length) {
    mcpStatusBadge(connected.length + ' / ' + names.length + ' 已连接', 'ok');
  } else {
    mcpStatusBadge('未连接', 'err');
  }
  onMcpServerChange();
}

function onMcpServerChange() {
  const name = document.getElementById('mcp-server-select').value;
  mcpState.selectedServer = name;
  const server = mcpState.servers[name];
  const toolSelect = document.getElementById('mcp-tool-select');
  const hint = document.getElementById('mcp-server-hint');
  if (!server || server.status !== 'connected') {
    toolSelect.innerHTML = '<option value="">无可用工具</option>';
    hint.textContent = server ? ('状态：' + server.status + (server.error ? ' · ' + server.error : '')) : '';
    onMcpToolChange();
    return;
  }
  mcpState.tools = server.tools || [];
  toolSelect.innerHTML = '';
  mcpState.tools.forEach(function (tool) {
    const option = document.createElement('option');
    option.value = tool.name;
    option.textContent = tool.name;
    toolSelect.appendChild(option);
  });
  const parts = ['连接方式：' + (server.via || server.transport || 'MCP')];
  if (server.url) parts.push(server.url);
  hint.textContent = parts.join(' · ');
  onMcpToolChange();
}

function onMcpToolChange() {
  const toolName = document.getElementById('mcp-tool-select').value;
  const tool = mcpState.tools.find(function (item) { return item.name === toolName; });
  const desc = document.getElementById('mcp-tool-desc');
  const args = document.getElementById('mcp-args');
  if (!tool) {
    desc.textContent = '选择服务器与工具后调用';
    args.value = '{}';
    return;
  }
  desc.textContent = tool.description || '（无描述）';
  args.value = JSON.stringify(buildMcpExample(tool), null, 2);
}

function buildMcpExample(tool) {
  const schema = tool.input_schema || {};
  const properties = schema.properties || {};
  const example = {};
  Object.keys(properties).forEach(function (key) {
    const spec = properties[key] || {};
    if (spec.default !== undefined) {
      example[key] = spec.default;
    } else if (key === 'project_id' && state.currentProject) {
      example[key] = state.currentProject;
    } else if (spec.type === 'integer' || spec.type === 'number') {
      example[key] = spec.minimum !== undefined ? spec.minimum : 0;
    } else if (spec.type === 'boolean') {
      example[key] = false;
    } else if (spec.enum && spec.enum.length) {
      example[key] = spec.enum[0];
    } else {
      example[key] = '';
    }
  });
  return example;
}

function extractMcpPayload(result) {
  if (result === null || result === undefined) return result;
  if (typeof result !== 'object') return result;
  const structured = result.structuredContent !== undefined ? result.structuredContent : result.structured_content;
  if (structured !== undefined) {
    if (structured && typeof structured === 'object' && !Array.isArray(structured) && Object.keys(structured).length === 1 && typeof structured.result === 'string') {
      try { return JSON.parse(structured.result); } catch (error) { return structured.result; }
    }
    return structured;
  }
  if (Array.isArray(result.content)) {
    const texts = result.content.filter(function (item) {
      return item && item.type === 'text';
    }).map(function (item) { return item.text; });
    const text = texts.join(String.fromCharCode(10));
    if (text) {
      try { return JSON.parse(text); } catch (error) { return text; }
    }
  }
  return result;
}

async function callMcpTool() {
  const serverName = document.getElementById('mcp-server-select').value;
  const toolName = document.getElementById('mcp-tool-select').value;
  const resultEl = document.getElementById('mcp-result');
  const statusEl = document.getElementById('mcp-call-status');
  const button = document.getElementById('mcp-call-btn');
  if (!serverName || !toolName) {
    statusEl.textContent = '请选择可用的服务器与工具';
    return;
  }
  let args = {};
  const raw = document.getElementById('mcp-args').value.trim();
  if (raw) {
    try {
      args = JSON.parse(raw);
    } catch (error) {
      resultEl.className = 'mcp-result err';
      resultEl.textContent = '参数不是合法 JSON：' + error.message;
      return;
    }
  }
  if (!args || typeof args !== 'object' || Array.isArray(args)) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = '参数必须是 JSON 对象，例如 {"project_id": "SPN-XXXX"}';
    return;
  }
  button.disabled = true;
  statusEl.textContent = '调用中…';
  resultEl.className = 'mcp-result';
  resultEl.textContent = '正在通过 MCP 调用 ' + serverName + ' / ' + toolName + ' …';
  const started = performance.now();
  try {
    const response = await fetch('/api/mcp/call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ server_name: serverName, tool_name: toolName, arguments: args })
    });
    const data = await response.json();
    const elapsed = Math.round(performance.now() - started);
    if (!response.ok || !data.success) {
      const message = data.error || (data.detail ? JSON.stringify(data.detail) : ('HTTP ' + response.status));
      resultEl.className = 'mcp-result err';
      resultEl.textContent = '调用失败：' + message;
      statusEl.textContent = elapsed + ' ms · 失败';
      return;
    }
    const payload = extractMcpPayload(data.result);
    resultEl.className = 'mcp-result';
    resultEl.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    statusEl.textContent = elapsed + ' ms · ' + serverName + ' / ' + toolName;
  } catch (error) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = '调用异常：' + error.message;
    statusEl.textContent = '失败';
  } finally {
    button.disabled = false;
  }
}

async function runMcpAgent() {
  const question = document.getElementById('mcp-agent-question').value.trim();
  const statusEl = document.getElementById('mcp-agent-status');
  const resultEl = document.getElementById('mcp-result');
  const button = document.getElementById('mcp-agent-btn');
  if (!question) {
    statusEl.textContent = '请输入自然语言指令';
    return;
  }
  button.disabled = true;
  statusEl.textContent = '模型正在选择工具…';
  resultEl.className = 'mcp-result';
  resultEl.textContent = 'Agent 正在规划 MCP 工具调用…';
  const started = performance.now();
  try {
    const response = await fetch('/api/mcp/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, project_id: state.currentProject || '' })
    });
    const data = await response.json();
    const elapsed = Math.round(performance.now() - started);
    if (!response.ok) {
      resultEl.className = 'mcp-result err';
      resultEl.textContent = 'Agent 调用失败：' + (data.detail || ('HTTP ' + response.status));
      statusEl.textContent = elapsed + ' ms · 失败';
      return;
    }
    const plan = data.plan || {};
    const axis = data.source === 'llm' ? 'LLM 规划' : '规则回退';
    const header = [
      'Agent 规划（' + axis + '）：' + (plan.server || '?') + ' / ' + (plan.tool || '?'),
      plan.reason ? '理由：' + plan.reason : '',
      '─'.repeat(34)
    ].filter(Boolean).join(String.fromCharCode(10));
    const payload = extractMcpPayload(data.result);
    const body = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    resultEl.className = data.success ? 'mcp-result' : 'mcp-result err';
    resultEl.textContent = header + String.fromCharCode(10) + (data.success ? body : ('调用失败：' + (data.error || body)));
    statusEl.textContent = elapsed + ' ms · ' + axis + ' · ' + (data.success ? '成功' : '失败');
    if (plan.server && mcpState.servers[plan.server]) {
      document.getElementById('mcp-server-select').value = plan.server;
      onMcpServerChange();
      if (plan.tool) {
        document.getElementById('mcp-tool-select').value = plan.tool;
        onMcpToolChange();
        document.getElementById('mcp-args').value = JSON.stringify(plan.arguments || {}, null, 2);
      }
    }
    if (data.llm_errors && data.llm_errors.length) {
      statusEl.textContent += ' · 模型回退';
    }
  } catch (error) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = 'Agent 调用异常：' + error.message;
    statusEl.textContent = '失败';
  } finally {
    button.disabled = false;
  }
}

async function loadSkill(skillName) {
  const skillNames = {
    'gene_annotation': '基因注释',
    'literature_search': '文献搜索',
    'pathway_enrichment': '通路富集',
    'splice_interpretation': '剪接解读'
  };
  
  const skillDescriptions = {
    'gene_annotation': '查询基因的详细信息，包括外显子结构、剪接位点、保守性评分和临床变异。',
    'literature_search': '搜索 PubMed、Europe PMC 等数据库中的科学文献，查找与基因或疾病相关的剪接研究。',
    'pathway_enrichment': '对候选基因列表进行 GO、KEGG、Reactome 通路富集分析，识别显著的功能类别。',
    'splice_interpretation': '解读特定剪接事件的生物学和临床意义，包括致病性预测和治疗靶点分析。'
  };
  
  // Add user message to chat
  addChatMessage('user', `我想使用 ${skillNames[skillName]} 技能`);
  
  // Show skill description
  addChatMessage('assistant', `${skillNames[skillName]}\n\n${skillDescriptions[skillName]}\n\n请提供必要的参数（如基因名称、事件类型等），我将为你执行分析。`);
  
  // Store current skill for parameter input
  window.currentSkill = skillName;
  
  // Focus input for parameters
  document.getElementById('chat-input').focus();
  document.getElementById('chat-input').placeholder = `请输入 ${skillNames[skillName]} 的参数...`;
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Add user message to chat
  addChatMessage('user', message);
  input.value = '';
  
  // If we have a current skill, try to execute it with the message as parameters
  if (window.currentSkill) {
    await executeSkillWithParams(window.currentSkill, message);
    window.currentSkill = null;
    document.getElementById('chat-input').placeholder = '输入问题或选择上方技能...';
  } else {
    // General question - provide guidance
    addChatMessage('assistant', '我理解你的问题。请选择上方的技能按钮开始专业分析，或者告诉我你想分析哪个基因/事件。');
  }
}

function addChatMessage(role, content) {
  const messagesDiv = document.getElementById('chat-messages');
  const isUser = role === 'user';
  
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message ' + (isUser ? 'user-message' : 'assistant-message');
  
  const titleDiv = document.createElement('div');
  titleDiv.className = 'message-author';
  titleDiv.style.cssText = 'font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 4px;';
  titleDiv.textContent = isUser ? '👤 你' : '🤖 SpliceGAIP';
  
  const contentDiv = document.createElement('div');
  contentDiv.style.cssText = 'font-size: 14px; line-height: 1.6; white-space: pre-wrap; color: var(--text);';
  var newlineRegex = new RegExp('\\n', 'g');
  contentDiv.innerHTML = content.replace(newlineRegex, '<br>');
  
  msgDiv.appendChild(titleDiv);
  msgDiv.appendChild(contentDiv);
  messagesDiv.appendChild(msgDiv);
  
  // Scroll to bottom
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function cfgText(zh, en) {
  var i18n = window.__splicegaipI18n;
  return i18n && i18n.getLang && i18n.getLang() === 'en' ? en : zh;
}

async function loadModelConfig(force) {
  const base = document.getElementById('cfg-base');
  if (!base) return;
  try {
    const response = await fetch('/api/llm/status');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    const values = (data.config && data.config.values) || {};
    if (force || !base.dataset.loaded) {
      base.value = values.MODEL_API_BASE_URL || '';
      document.getElementById('cfg-model').value = values.MODEL_NAME || '';
      const key = document.getElementById('cfg-key');
      key.value = '';
      key.placeholder = values.MODEL_API_KEY
        ? cfgText('当前密钥 ' + values.MODEL_API_KEY + '，留空保持不变', 'Current key ' + values.MODEL_API_KEY + ' — leave blank to keep it')
        : cfgText('粘贴你的 API Key', 'Paste your API key');
      base.dataset.loaded = '1';
    }
    const badge = document.getElementById('cfg-status');
    const statusText = document.getElementById('cfg-status-text');
    if (data.configured && data.enabled) {
      badge.className = 'status status-completed';
      statusText.textContent = cfgText('已配置 · ' + (data.model || 'LLM'), 'Configured · ' + (data.model || 'LLM'));
    } else {
      badge.className = 'status status-waiting';
      statusText.textContent = data.enabled ? cfgText('未配置 Key', 'No API key') : cfgText('模型已关闭', 'Model disabled');
    }
    const button = document.getElementById('cfg-save');
    if (button && !button.disabled) button.textContent = cfgText('保存并启用', 'Save & enable');
  } catch (error) {
    const badge = document.getElementById('cfg-status');
    if (badge) {
      badge.className = 'status status-waiting';
      document.getElementById('cfg-status-text').textContent = cfgText('状态不可用', 'Status unavailable');
    }
    console.error('loadModelConfig', error);
  }
}

async function saveModelConfig() {
  const button = document.getElementById('cfg-save');
  const message = document.getElementById('cfg-msg');
  if (!button || button.disabled) return;
  const base = document.getElementById('cfg-base').value.trim();
  const model = document.getElementById('cfg-model').value.trim();
  const key = document.getElementById('cfg-key').value.trim();
  if (!base || !model) {
    message.className = 'cfg-msg err';
    message.textContent = cfgText('请填写 Base URL 和模型名', 'Base URL and model name are required');
    return;
  }
  const values = { MODEL_API_BASE_URL: base, MODEL_NAME: model };
  if (key) values.MODEL_API_KEY = key;
  button.disabled = true;
  button.textContent = cfgText('保存中…', 'Saving…');
  message.className = 'cfg-msg';
  message.textContent = '';
  try {
    const response = await fetch('/api/llm/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ values }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    message.className = 'cfg-msg ok';
    message.textContent = key
      ? cfgText('配置已保存并即时生效', 'Saved — active immediately')
      : cfgText('配置已保存（保留原 Key）', 'Saved (existing key kept)');
    document.getElementById('cfg-key').value = '';
    document.getElementById('cfg-base').dataset.loaded = '';
    await loadModelConfig(true);
  } catch (error) {
    message.className = 'cfg-msg err';
    message.textContent = cfgText('保存失败: ', 'Save failed: ') + error.message;
  } finally {
    button.disabled = false;
    button.textContent = cfgText('保存并启用', 'Save & enable');
  }
}

document.addEventListener('splicegaip:language', function () {
  if (!document.getElementById('cfg-status-text')) return;
  const message = document.getElementById('cfg-msg');
  if (message) {
    message.className = 'cfg-msg';
    message.textContent = '';
  }
  loadModelConfig(true);
});

async function executeSkillWithParams(skillName, paramText) {
  try {
    // Parse parameters from text (simple key=value parsing)
    const params = parseParameters(paramText);
    
    // Build request based on skill
    let requestBody = { skill_name: skillName, parameters: {} };
    
    if (skillName === 'gene_annotation') {
      requestBody.parameters.gene_symbol = params.gene || params.gene_symbol || extractGeneFromText(paramText);
      requestBody.parameters.include_splicing = true;
      requestBody.parameters.include_clinical = true;
    } else if (skillName === 'literature_search') {
      requestBody.parameters.query = params.query || paramText;
      requestBody.parameters.max_results = parseInt(params.max_results) || 10;
      requestBody.parameters.sources = ['pubmed'];
    } else if (skillName === 'pathway_enrichment') {
      // Extract gene list from text
      const genes = extractGenesFromText(paramText);
      requestBody.parameters.genes = genes;
      requestBody.parameters.ontologies = ['GO', 'KEGG'];
    } else if (skillName === 'splice_interpretation') {
      requestBody.parameters.gene_symbol = params.gene || extractGeneFromText(paramText);
      requestBody.parameters.event_type = params.event_type || 'SE';
    }
    
    // Call API
    addChatMessage('assistant', '正在执行分析，请稍候...');
    
    const response = await fetch('/api/skills/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`API 错误: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Display results
    displaySkillResults(result);
    
    // Add success message to chat
    if (result.success) {
      addChatMessage('assistant', '✅ 分析完成！结果已显示在右侧面板中。');
    } else {
      addChatMessage('assistant', `❌ 分析失败: ${result.error || '未知错误'}`);
    }
    
  } catch (error) {
    addChatMessage('assistant', `❌ 执行出错: ${error.message}`);
  }
}

function parseParameters(text) {
  const params = {};
  const pairs = text.split(/\s+/);
  
  for (const pair of pairs) {
    const [key, ...valueParts] = pair.split('=');
    if (valueParts.length > 0) {
      params[key.toLowerCase()] = valueParts.join('=');
    }
  }
  
  return params;
}

function extractGeneFromText(text) {
  // Simple extraction - look for common gene patterns
  const match = text.match(/([A-Z][A-Z0-9]+[0-9]?)/);
  return match ? match[1] : text.split(/\s+/)[0];
}

function extractGenesFromText(text) {
  // Split by comma, space, or semicolon and filter
  const candidates = text.split(/[,\s;]+/).filter(s => s.length > 1 && /^[A-Z]/.test(s));
  return candidates.slice(0, 20); // Limit to 20 genes
}

function displaySkillResults(result) {
  const resultsDiv = document.getElementById('skill-results');
  
  if (!result.success) {
    resultsDiv.innerHTML = `
      <div style="padding: 20px; background: #fee2e2; border-left: 4px solid #dc2626; border-radius: var(--radius);">
        <div style="font-size: 16px; font-weight: 700; color: #dc2626; margin-bottom: 8px;">❌ 分析失败</div>
        <div style="font-size: 14px; color: #7f1d1d;">${result.error || '未知错误'}</div>
      </div>
    `;
    return;
  }
  
  const skillName = result.skill_name;
  const data = result.data;
  
  let html = `<div style="padding: 20px; background: var(--gray-100); border-left: 2px solid var(--black); border-radius: var(--radius); margin-bottom: 20px;">
    <div style="font-size: 16px; font-weight: 700; color: var(--accent); margin-bottom: 4px;">✅ 分析完成</div>
    <div style="font-size: 13px; color: var(--text);">${getSkillDisplayName(skillName)}</div>
  </div>`;
  
  if (skillName === 'gene_annotation') {
    html += renderGeneAnnotationResults(data);
  } else if (skillName === 'literature_search') {
    html += renderLiteratureSearchResults(data);
  } else if (skillName === 'pathway_enrichment') {
    html += renderPathwayEnrichmentResults(data);
  } else if (skillName === 'splice_interpretation') {
    html += renderSpliceInterpretationResults(data);
  }
  
  resultsDiv.innerHTML = html;
}

function getSkillDisplayName(skillName) {
  const names = {
    'gene_annotation': '基因注释分析',
    'literature_search': '文献搜索结果',
    'pathway_enrichment': '通路富集分析',
    'splice_interpretation': '剪接事件解读'
  };
  return names[skillName] || skillName;
}

function renderGeneAnnotationResults(data) {
  let html = '<div class="card" style="margin-bottom: 16px;">';
  html += '<div style="font-size: 16px; font-weight: 700; margin-bottom: 16px;">🧬 基因基本信息</div>';
  
  if (data.basic_info) {
    const info = data.basic_info;
    html += `<div style="font-size: 14px; line-height: 1.8;">
      <div><strong>基因符号:</strong> ${info.symbol || '-'}</div>
      <div><strong>基因名称:</strong> ${info.name || '-'}</div>
      <div><strong>Ensembl ID:</strong> ${info.ensembl_gene || '-'}</div>
      <div><strong>基因类型:</strong> ${info.gene_type || '-'}</div>
    </div>`;
    if (info.summary) {
      html += `<div style="margin-top: 12px; padding: 12px; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; color: var(--text);">${info.summary}</div>`;
    }
  }
  
  if (data.gene_structure) {
    const struct = data.gene_structure;
    html += '<div style="margin-top: 20px; font-size: 16px; font-weight: 700;">📐 基因结构</div>';
    html += `<div style="font-size: 14px; line-height: 1.8; margin-top: 8px;">
      <div><strong>染色体:</strong> ${struct.chromosome || '-'}</div>
      <div><strong>位置:</strong> ${struct.start || '-'} - ${struct.end || '-'}</div>
      <div><strong>链方向:</strong> ${struct.strand === 1 ? '+' : (struct.strand === -1 ? '-' : '-')}</div>
      <div><strong>生物类型:</strong> ${struct.biotype || '-'}</div>
    </div>`;
  }
  
  html += '</div>';
  return html;
}

function renderLiteratureSearchResults(data) {
  let html = '<div class="card" style="margin-bottom: 16px;">';
  html += `<div style="font-size: 16px; font-weight: 700; margin-bottom: 16px;">📚 文献搜索结果</div>`;
  html += `<div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">共找到 ${data.total_found || 0} 篇相关文献</div>`;
  
  if (data.results && Array.isArray(data.results)) {
    data.results.forEach((paper, idx) => {
      html += `<div style="padding: 16px; margin-bottom: 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius);">
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 8px; color: var(--accent);">${idx + 1}. ${paper.title || '无标题'}</div>
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">
          ${paper.authors || ''} | ${paper.journal || ''} | ${paper.year || ''}
        </div>
        ${paper.citation_count ? `<div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">被引次数: ${paper.citation_count}</div>` : ''}
        ${paper.abstract ? `<div style="font-size: 13px; line-height: 1.6; color: var(--text); margin-top: 8px; padding: 12px; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--radius);">${paper.abstract.substring(0, 300)}...</div>` : ''}
        ${paper.url ? `<a href="${paper.url}" target="_blank" style="display: inline-block; margin-top: 8px; font-size: 13px; color: var(--accent); text-decoration: none;">查看原文 →</a>` : ''}
      </div>`;
    });
  }
  
  html += '</div>';
  return html;
}

function renderPathwayEnrichmentResults(data) {
  let html = '<div class="card" style="margin-bottom: 16px;">';
  html += `<div style="font-size: 16px; font-weight: 700; margin-bottom: 16px;">🔬 通路富集分析结果</div>`;
  html += `<div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">输入基因数: ${data.total_genes || 0} | 显著条目数: ${data.total_significant || 0}</div>`;
  
  if (data.enriched_terms && Array.isArray(data.enriched_terms)) {
    html += '<div style="overflow-x: auto;">';
    html += '<table style="width: 100%; font-size: 13px; border-collapse: collapse;">';
    html += '<thead><tr style="background: var(--surface-2); border-bottom: 2px solid var(--border);">';
    html += '<th style="padding: 12px; text-align: left; font-weight: 700;">数据库</th>';
    html += '<th style="padding: 12px; text-align: left; font-weight: 700;">术语/通路</th>';
    html += '<th style="padding: 12px; text-align: center; font-weight: 700;">基因数</th>';
    html += '<th style="padding: 12px; text-align: right; font-weight: 700;">FDR</th>';
    html += '</tr></thead><tbody>';
    
    data.enriched_terms.forEach((term, idx) => {
      const sigColor = term.fdr < 0.05 ? '#059669' : (term.fdr < 0.1 ? '#d97706' : '#dc2626');
      html += `<tr style="border-bottom: 1px solid var(--border);">
        <td style="padding: 12px;"><span style="display: inline-block; padding: 4px 8px; background: rgba(94,234,212,.12); color: var(--accent); border: 1px solid rgba(94,234,212,.3); border-radius: 4px; font-size: 11px; font-weight: 600;">${term.ontology || '-'}</span></td>
        <td style="padding: 12px; font-weight: 600;">${term.term_name || '-'}</td>
        <td style="padding: 12px; text-align: center;">${term.gene_count || 0}</td>
        <td style="padding: 12px; text-align: right; color: ${sigColor}; font-weight: 700;">${term.fdr ? term.fdr.toExponential(2) : '-'}</td>
      </tr>`;
    });
    
    html += '</tbody></table></div>';
  }
  
  html += '</div>';
  return html;
}

function renderSpliceInterpretationResults(data) {
  let html = '<div class="card" style="margin-bottom: 16px;">';
  html += `<div style="font-size: 16px; font-weight: 700; margin-bottom: 16px;">⚕️ 剪接事件解读</div>`;
  
  if (data.interpretation) {
    const interp = data.interpretation;
    
    if (interp.summary) {
      html += `<div style="padding: 16px; background: rgba(243,189,114,.1); border-left: 2px solid var(--warning); border-radius: var(--radius); margin-bottom: 20px;">
        <div style="font-size: 14px; font-weight: 700; color: var(--warning); margin-bottom: 8px;">📋 总结</div>
        <div style="font-size: 14px; line-height: 1.8; color: var(--text);">${interp.summary}</div>
      </div>`;
    }
    
    if (interp.protein_impact) {
      const impact = interp.protein_impact;
      html += '<div style="margin-bottom: 20px;">';
      html += '<div style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--accent);">🎯 蛋白功能影响</div>';
      html += `<div style="font-size: 14px; line-height: 1.8;">${impact.functional_consequence || '-'}</div>`;
      
      if (impact.affected_domains && impact.affected_domains.length > 0) {
        html += '<div style="margin-top: 12px; font-size: 13px; font-weight: 700;">受影响的蛋白结构域:</div>';
        impact.affected_domains.forEach(domain => {
          html += `<div style="padding: 8px 12px; margin-top: 6px; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; color: var(--text);">
            • ${domain.name || '-'} (位置: ${domain.start || '-'}-${domain.end || '-'})
          </div>`;
        });
      }
      html += '</div>';
    }
    
    if (interp.therapeutic_opportunities) {
      const thermo = interp.therapeutic_opportunities;
      html += '<div style="margin-bottom: 20px;">';
      html += '<div style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--accent);">💊 治疗机会</div>';
      
      if (thermo.targeting_strategies && thermo.targeting_strategies.length > 0) {
        thermo.targeting_strategies.forEach(strategy => {
          html += `<div style="padding: 12px; margin-bottom: 8px; background: rgba(94,234,212,.08); border-left: 3px solid var(--accent); border-radius: var(--radius);">
            <div style="font-size: 14px; font-weight: 700; color: var(--accent); margin-bottom: 4px;">${strategy.strategy || '-'}</div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 4px;">机制: ${strategy.mechanism || '-'}</div>
            ${strategy.example ? `<div style="font-size: 12px; color: var(--text-secondary);">示例: ${strategy.example}</div>` : ''}
          </div>`;
        });
      }
      
      if (thermo.clinical_trials && thermo.clinical_trials.length > 0) {
        html += '<div style="margin-top: 12px; font-size: 13px; font-weight: 700;">相关临床试验:</div>';
        thermo.clinical_trials.forEach(trial => {
          html += `<div style="padding: 8px 12px; margin-top: 6px; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--radius); font-size: 13px; color: var(--text);">
            • ${trial.title || trial.nct_id || '-'} (${trial.status || '进行中'})
          </div>`;
        });
      }
      html += '</div>';
    }
  }
  
  html += '</div>';
  return html;
}

document.addEventListener('DOMContentLoaded', () => { loadDashboard(); loadModelConfig(); setInterval(() => { if (state.currentPage === 'pipeline' && state.currentProject) { loadPipeline(); } }, 5000); });
</script>
<script src="/assets/opencc-cn2t.js"></script>
<script>
(function () {
  "use strict";
  var toTraditional = window.OpenCC.Converter({ from: "cn", to: "t" });
  var DICT = {
    "仪表盘": "Dashboard",
    "AI 流水线": "AI Pipeline",
    "事件浏览器": "Event Explorer",
    "可视化": "Visualization",
    "基因浏览器": "Gene Browser",
    "报告": "Report",
    "AI 助手": "AI Assistant",
    "🤖 AI 助手": "🤖 AI Assistant",
    "👤 你": "👤 You",
    "主菜单": "Main Menu",
    "分析工具": "Analysis Tools",
    "智能助手": "Assistant",
    "刷新": "Refresh",
    "+ 新建分析": "+ New Analysis",
    "未加载项目": "No project loaded",
    "AI 智能分析平台": "AI Analysis Platform",
    "SpliceGAIP - AI 智能分析平台": "SpliceGAIP - AI Analysis Platform",
    "从剪接事件，到可复现的生物学证据。": "From splicing events to reproducible biological evidence.",
    "让 Agent 整理数据、追踪分析状态，并把每一个结论连接到可验证的结果。": "Let agents organize data, track analysis status, and connect every conclusion to verifiable results.",
    "总样本数": "Total Samples",
    "RNA-seq 样本": "RNA-seq samples",
    "剪接事件": "Splicing Events",
    "检测到的事件总数": "Total detected events",
    "显著事件": "Significant Events",
    "系统状态": "System Status",
    "空闲": "Idle",
    "分析中": "Running",
    "当前运行 Agent": "Current Running Agent",
    "暂无运行中的分析": "No analysis running",
    "启动新分析": "Start New Analysis",
    "最近项目": "Recent Projects",
    "暂无项目": "No projects",
    "分析进度": "Analysis Progress",
    "等待启动...": "Waiting to start...",
    "Agent 工作流": "Agent Workflow",
    "📊 数据 Agent": "📊 Data Agent",
    "加载并验证输入数据，检查文件格式和完整性": "Load and validate input data, checking file format and integrity",
    "✅ 质控 Agent": "✅ QC Agent",
    "执行质量控制检查，过滤低质量样本": "Run quality-control checks and filter low-quality samples",
    "🔬 剪接检测 Agent": "🔬 Splicing Detection Agent",
    "使用统计模型检测可变剪接事件": "Detect alternative splicing events with statistical models",
    "📈 统计 Agent": "📈 Statistics Agent",
    "计算显著性（FDR）和效应量（Delta PSI）": "Compute significance (FDR) and effect size (Delta PSI)",
    "🧬 注释 Agent": "🧬 Annotation Agent",
    "功能注释、通路富集和文献证据收集": "Functional annotation, pathway enrichment, and literature evidence collection",
    "🤖 解读 Agent": "🤖 Interpretation Agent",
    "生成生物学解读和专业分析报告": "Generate biological interpretation and a professional analysis report",
    "等待中": "Waiting",
    "运行中": "Running",
    "已完成": "Completed",
    "数据加载": "Data Loading",
    "质量控制": "Quality Control",
    "剪接检测": "Splicing Detection",
    "统计分析": "Statistical Analysis",
    "功能注释": "Functional Annotation",
    "生物学解读": "Biological Interpretation",
    "未加载事件数据": "No event data loaded",
    "等待分析结果": "Waiting for analysis results",
    "请完成分析后查看结果": "Complete an analysis to view results",
    "准备生成报告": "Ready to generate report",
    "事件 ID": "Event ID",
    "类型": "Type",
    "基因": "Gene",
    "评分": "Score",
    "操作": "Actions",
    "详情": "Details",
    "事件类型": "Event Type",
    "查看": "View",
    "筛选条件": "Filters",
    "统计阈值": "Statistical Thresholds",
    "🔍 应用筛选": "🔍 Apply Filters",
    "🔍 探索": "🔍 Explore",
    "搜索基因名称、事件ID或染色体位置...": "Search gene name, event ID, or chromosome position...",
    "选择图表类型": "Select chart type",
    "左侧共 13 张专业科研图，点击即可渲染": "13 publication-ready figures on the left; click to render",
    "📊 核心统计图": "📊 Core Statistics",
    "🔬 样本与质控": "🔬 Samples and QC",
    "🧬 事件组成与机制": "🧬 Event Composition and Mechanisms",
    "🤖 AI 排序与功能富集": "🤖 AI Ranking and Functional Enrichment",
    "🌋 火山图 Volcano": "🌋 Volcano Plot",
    "📈 ΔPSI 累积分布 ECDF": "📈 ΔPSI ECDF",
    "🪜 显著性碎石图 Scree": "🪜 Significance Scree Plot",
    "🎯 类型×显著性堆叠图": "🎯 Type × Significance Stacked Plot",
    "🧩 剪接机制示意图 Schematic": "🧩 Splicing Mechanism Schematic",
    "🌡️ PSI 热图 Heatmap": "🌡️ PSI Heatmap",
    "📦 分组 PSI 箱线图": "📦 Grouped PSI Box Plot",
    "🥧 队列构成图": "🥧 Cohort Composition",
    "🏆 候选基因排名": "🏆 Candidate Gene Ranking",
    "🧮 评分分解堆叠图": "🧮 Score Decomposition Stacked Plot",
    "🕸️ 功能富集点图": "🕸️ Functional Enrichment Dot Plot",
    "差异剪接的显著性与效应量": "Significance and effect size of differential splicing",
    "ΔPSI vs -log10(FDR)，标注显著性阈值": "ΔPSI vs -log10(FDR) with significance thresholds",
    "💧 ΔPSI 瀑布图 Waterfall": "💧 ΔPSI Waterfall",
    "Top 25 效应量排序，区分包含上调/下调": "Top 25 by effect size, separating inclusion up/down",
    "SE/MXE/A5SS/A3SS/RI 五类事件计数": "Counts of the five event classes: SE/MXE/A5SS/A3SS/RI",
    "五类可变剪接的外显子-内含子结构模式图": "Exon-intron schematic of the five alternative splicing classes",
    "分组占比与批次分布（QC 必备）": "Group proportions and batch distribution (essential for QC)",
    "效应量经验累积分布与阈值占比": "Empirical effect-size CDF and threshold proportions",
    "候选排名 vs -log10(FDR)，定位显著性拐点": "Candidate rank vs -log10(FDR) to locate the significance elbow",
    "各类型中显著与非显著事件构成": "Significant vs non-significant events within each class",
    "剪接事件类型构成与分子机制": "Splicing event composition and molecular mechanisms",
    "Top 事件逐样本 PSI 聚类热图": "Per-sample PSI clustering heatmap for top events",
    "各组 PSI 分布与离群样本检测": "PSI distribution by group and outlier detection",
    "队列构成与样本水平 PSI 模式": "Cohort composition and sample-level PSI patterns",
    "综合评分 Top 15 候选事件条形图": "Bar chart of the top 15 candidates by composite score",
    "显著性/效应/生物学/文献四维贡献": "Four-dimensional contribution: significance / effect / biology / literature",
    "GO/KEGG 富集倍数 vs FDR 气泡图": "GO/KEGG enrichment fold vs FDR bubble plot",
    "智能体候选评分与通路注释": "Agent-based candidate scoring and pathway annotation",
    "📊 事件类型分布": "📊 Event Type Distribution",
    "📊 分析结果": "📊 Analysis Results",
    "SE (外显子跳跃)": "SE (skipped exon)",
    "MXE (互斥外显子)": "MXE (mutually exclusive exons)",
    "A5SS (可变5'剪接)": "A5SS (alternative 5' splice site)",
    "A3SS (可变3'剪接)": "A3SS (alternative 3' splice site)",
    "RI (内含子保留)": "RI (intron retention)",
    "基因注释": "Gene Annotation",
    "文献搜索": "Literature Search",
    "通路富集": "Pathway Enrichment",
    "剪接解读": "Splice Interpretation",
    "支持基因注释、文献搜索、通路富集和剪接事件解读等专业技能": "Professional skills including gene annotation, literature search, pathway enrichment, and splice event interpretation",
    "⚙️ 模型配置": "⚙️ Model configuration",
    "模型配置": "Model configuration",
    "检查中…": "Checking…",
    "模型名": "Model",
    "留空则保持当前密钥": "Leave blank to keep the current key",
    "保存并启用": "Save & enable",
    "保存中…": "Saving…",
    "密钥仅保存在本机 .env / 配置大模型.env，不会写入报告或日志；保存后即时生效。": "The key is stored only in the local .env / 配置大模型.env file; it is never written to reports or logs and applies immediately.",
    "未配置 Key": "No API key",
    "模型已关闭": "Model disabled",
    "状态不可用": "Status unavailable",
    "请填写 Base URL 和模型名": "Base URL and model name are required",
    "配置已保存并即时生效": "Saved — active immediately",
    "配置已保存（保留原 Key）": "Saved (existing key kept)",
    "选择左侧的技能按钮执行专业分析": "Choose a skill on the left to run a professional analysis",
    "请选择上方的技能按钮开始，或直接输入你的问题。": "Choose a skill above to start, or type your question.",
    "你好！我是 SpliceGAIP 智能助手，可以帮助你：": "Hello! I am the SpliceGAIP assistant. I can help you:",
    "🤖 SpliceGAIP 智能助手": "🤖 SpliceGAIP Assistant",
    "• 项目概览与样本统计": "• Project overview and sample statistics",
    "• 显著剪接事件列表（FDR": "• Significant splicing event list (FDR",
    "• 显著剪接事件列表（FDR < 0.05）": "• Significant splicing event list (FDR < 0.05)",
    "• 关键基因的功能注释与通路富集": "• Functional annotation and pathway enrichment for key genes",
    "• 可视化图表（火山图、热图、分布图）": "• Visualizations (volcano, heatmap, distribution)",
    "• AI 生成的生物学解读与建议": "• AI-generated biological interpretation and recommendations",
    "• 搜索相关科学文献": "• Search relevant scientific literature",
    "• 执行通路富集分析": "• Run pathway enrichment analysis",
    "• 解读剪接事件的临床意义": "• Interpret the clinical significance of splicing events",
    "• 查询基因注释和剪接位点信息": "• Query gene annotation and splice-site information",
    "🔌 MCP 工具": "🔌 MCP Tools",
    "Model Context Protocol · 运行时外部工具调用": "Model Context Protocol · runtime external tool calls",
    "未加载": "Not loaded",
    "自然语言指令": "Natural-language instruction",
    "AI 调用": "AI Call",
    "模型选择 MCP 工具 → 本地校验 → 执行并返回结果": "Model selects an MCP tool → local validation → execute and return results",
    "例如：查一下 CD44 有哪些显著剪接事件": "e.g. Show significant splicing events for CD44",
    "MCP 服务器": "MCP Server",
    "正在读取服务器配置…": "Reading server configuration…",
    "工具": "Tool",
    "选择服务器与工具后调用": "Select a server and tool to call",
    "参数（JSON）": "Arguments (JSON)",
    "调用工具": "Call Tool",
    "尚未调用": "Not called yet",
    "请输入自然语言指令": "Enter a natural-language instruction",
    "请选择可用的服务器与工具": "Select an available server and tool",
    "请输入问题或选择上方技能...": "Type a question or choose a skill above...",
    "输入问题或选择上方技能...": "Type a question or choose a skill above...",
    "发送": "Send",
    "我理解你的问题。请选择上方的技能按钮开始专业分析，或者告诉我你想分析哪个基因/事件。": "I understand your question. Choose a skill above to start a professional analysis, or tell me which gene or event you want to analyze.",
    "查询基因的详细信息，包括外显子结构、剪接位点、保守性评分和临床变异。": "Detailed gene information including exon structure, splice sites, conservation scores, and clinical variants.",
    "搜索 PubMed、Europe PMC 等数据库中的科学文献，查找与基因或疾病相关的剪接研究。": "Search PubMed, Europe PMC, and other databases for splicing studies related to a gene or disease.",
    "对候选基因列表进行 GO、KEGG、Reactome 通路富集分析，识别显著的功能类别。": "Run GO, KEGG, and Reactome pathway enrichment on candidate genes to identify significant functional categories.",
    "解读特定剪接事件的生物学和临床意义，包括致病性预测和治疗靶点分析。": "Interpret the biological and clinical significance of a specific splicing event, including pathogenicity prediction and therapeutic targets.",
    "请提供必要的参数（如基因名称、事件类型等），我将为你执行分析。": "Please provide the required parameters (e.g., gene name, event type) and I will run the analysis.",
    "探索基因剪接模式": "Explore Gene Splicing Patterns",
    "输入基因符号（如 TP53、BRCA1、MYC）...": "Enter a gene symbol (e.g., TP53, BRCA1, MYC)...",
    "输入基因符号查看该基因的所有剪接事件、统计信息和文献证据。支持热门基因如 TP53、BRCA1、MYC、EGFR 等。": "Enter a gene symbol to view all splicing events, statistics, and literature evidence. Popular genes: TP53, BRCA1, MYC, EGFR.",
    "在上方输入基因符号以探索其剪接事件和生物学功能": "Enter a gene symbol above to explore its splicing events and biological function",
    "基因剪接分析报告": "Gene Splicing Analysis Report",
    "返回事件列表": "Back to Event List",
    "总事件数": "Total Events",
    "平均 |ΔPSI|": "Mean |ΔPSI|",
    "事件类型分布": "Event Type Distribution",
    "剪接事件详情": "Splicing Event Details",
    "该基因可能不在当前分析的候选列表中，或未达到显著性阈值": "This gene may not be in the current candidate list or did not pass the significance threshold",
    "浏览所有事件": "Browse All Events",
    "未选择项目": "No project selected",
    "请先在仪表盘选择一个分析项目": "Select an analysis project on the dashboard first",
    "请先选择项目": "Select a project first",
    "在仪表盘选择一个分析项目后再探索基因": "Select an analysis project on the dashboard before exploring genes",
    "图表不可用": "Figure unavailable",
    "该项目可能尚未生成此图表，请完成分析后重试": "This figure may not exist yet. Complete the analysis and try again.",
    "正在渲染图表（首次生成约需数秒）...": "Rendering figure (the first render may take a few seconds)...",
    "报告生成成功！": "Report generated successfully!",
    "文件已自动下载": "The file has been downloaded automatically",
    "在新窗口中查看": "Open in New Window",
    "报告生成失败": "Report generation failed",
    "重试": "Retry",
    "正在生成报告...": "Generating report...",
    "这可能需要几分钟时间，请耐心等待": "This may take a few minutes. Please wait.",
    "✅ 分析完成": "✅ Analysis complete",
    "❌ 分析失败": "❌ Analysis failed",
    "未知错误": "Unknown error",
    "🔬 通路富集分析结果": "🔬 Pathway Enrichment Results",
    "📚 文献搜索结果": "📚 Literature Search Results",
    "⚕️ 剪接事件解读": "⚕️ Splice Event Interpretation",
    "📋 总结": "📋 Summary",
    "无标题": "Untitled",
    "查看原文 →": "View source →",
    "被引次数:": "Citations:",
    "机制:": "Mechanism:",
    "示例:": "Example:",
    "相关临床试验:": "Related clinical trials:",
    "进行中": "Ongoing",
    "位置:": "Location:",
    "染色体:": "Chromosome:",
    "链方向:": "Strand:",
    "生物类型:": "Biotype:",
    "基因符号:": "Gene symbol:",
    "基因名称:": "Gene name:",
    "基因类型:": "Gene type:",
    "未找到匹配的事件": "No matching events found",
    "暂无文献证据": "No literature evidence",
    "关闭": "Close",
    "查看基因详情": "View Gene Details",
    "生物学影响评估": "Biological Impact Assessment",
    "强效应 - 可能导致蛋白质功能重大改变": "Strong effect - may substantially alter protein function",
    "中等效应 - 可能影响蛋白质结构域": "Moderate effect - may affect a protein domain",
    "弱效应 - 可能对功能有轻微影响": "Weak effect - may have a minor functional impact",
    "微小效应 - 可能无显著生物学影响": "Minimal effect - likely no significant biological impact",
    "事件未找到": "Event not found",
    "事件类型说明": "Event Type Description",
    "统计详情": "Statistical Details",
    "P值": "P-value",
    "FDR校正值": "FDR-adjusted",
    "综合评分": "Composite Score",
    "文献证据": "Literature Evidence",
    "加载中...": "Loading...",
    "外显子跳跃 (Skipped Exon): 最常见的外显子类型，可能导致蛋白质结构域缺失": "Skipped exon (SE): the most common event type; may cause loss of a protein domain",
    "互斥外显子 (Mutually Exclusive Exons): 两个相邻外显子中只保留一个": "Mutually exclusive exons (MXE): only one of two adjacent exons is retained",
    "可变3'剪接位点 (Alternative 3' Splice Site): 影响外显子3'端边界": "Alternative 3' splice site (A3SS): affects the exon 3' boundary",
    "可变5'剪接位点 (Alternative 5' Splice Site): 影响外显子5'端边界": "Alternative 5' splice site (A5SS): affects the exon 5' boundary",
    "内含子保留 (Retained Intron): 内含子未被正确移除": "Retained intron (RI): the intron is not removed correctly",
    "未知剪接事件类型": "Unknown splicing event type",
    "以 ΔPSI 为横轴、-log10(FDR) 为纵轴展示全部剪接事件；虚线为 FDR=0.05 与 |ΔPSI|=0.1 阈值，橙色点为显著事件。": "ΔPSI on the x-axis and -log10(FDR) on the y-axis for all splicing events; dashed lines mark FDR=0.05 and |ΔPSI|=0.1; orange points are significant events.",
    "按 |ΔPSI| 排序的 Top 25 候选事件；橙色为包含水平上调，蓝色为下调，直观展示效应量谱。": "Top 25 candidates ranked by |ΔPSI|; orange indicates inclusion up, blue indicates inclusion down.",
    "ΔPSI 的经验累积分布曲线，并标注 |ΔPSI|>0.1 的事件占比，用于评估整体效应量分布。": "Empirical CDF of ΔPSI with the proportion of events above |ΔPSI|>0.1.",
    "候选排名对 -log10(FDR) 曲线，配合 FDR=0.05 参考线定位显著性拐点（elbow）。": "Candidate rank vs -log10(FDR) with an FDR=0.05 reference line to locate the significance elbow.",
    "SE / MXE / A5SS / A3SS / RI 五类可变剪接事件的检出计数。": "Detected counts for the five alternative splicing classes: SE / MXE / A5SS / A3SS / RI.",
    "各事件类型中通过阈值（FDR<0.05 且 |ΔPSI|>0.1）的显著事件与非显著事件构成。": "Significant vs non-significant events within each class using FDR<0.05 and |ΔPSI|>0.1.",
    "五类可变剪接事件的外显子-内含子结构模式图（methods 级示意图）。": "Exon-intron schematic of the five alternative splicing classes (methods-level figure).",
    "Top |ΔPSI| 事件的逐样本 PSI 热图，列上方标注样本分组，用于观察聚类模式。": "Per-sample PSI heatmap for top |ΔPSI| events with sample groups annotated above the columns.",
    "按实验组拆分的 Top 事件 PSI 分布（箱线 + 散点），用于识别离群样本。": "PSI distribution of top events by experimental group (box + scatter) to identify outliers.",
    "样本分组占比（环图）与批次分布（条形），为质控必备图表。": "Sample group proportions (donut) and batch distribution (bars) for QC.",
    "AI 智能体综合评分（显著性+效应+生物学+文献）Top 15 候选事件。": "Top 15 candidates by the agent composite score (significance + effect + biology + literature).",
    "Top 候选的四维评分贡献分解：显著性 / 效应量 / 生物学 / 文献证据。": "Four-dimensional score decomposition for top candidates: significance / effect size / biology / literature evidence.",
    "GO/KEGG 富集结果：横轴为富集倍数，颜色为 -log10(FDR)，点大小为重叠基因数。": "GO/KEGG enrichment: fold enrichment on the x-axis, color is -log10(FDR), dot size is overlapping gene count.",
    "新建分析项目": "New Analysis Project",
    "项目名称": "Project Name",
    "分析查询": "Analysis Query",
    "输入项目名称（如 My_RNA_Study）": "Enter a project name (e.g., My_RNA_Study)",
    "输入分析查询（如 compare treatment vs control）": "Enter an analysis query (e.g., compare treatment vs control)",
    "上传文件": "Upload Files",
    "拖拽文件到此处，或点击选择文件": "Drag files here, or click to choose files",
    "支持 CSV、TSV、TXT 表格（Excel 请另存为 CSV），可同时上传样本分组表": "CSV, TSV or TXT tables (save Excel as CSV); a sample-group table can be uploaded too",
    "取消": "Cancel",
    "开始分析": "Start Analysis",
    "请至少选择一个文件": "Please select at least one file",
    "请先选择一个项目": "Please select a project first",
    "请输入基因符号": "Please enter a gene symbol",
    "请输入分析查询": "Please enter an analysis query",
    "请输入项目名称": "Please enter a project name",
    "处理中...": "Processing...",
    "分析已完成": "Analysis complete",
    "分析已启动，准备中...": "Analysis started, preparing...",
    "上传中...": "Uploading...",
    "分析中（预计 3-6 分钟）...": "Running (estimated 3-6 minutes)...",
    "数据 Agent 正在理解查询...": "Data Agent is interpreting the query...",
    "质控 Agent 正在进行质量检查...": "QC Agent is running quality checks...",
    "剪接检测 Agent 正在筛选显著事件...": "Splicing Detection Agent is filtering significant events...",
    "统计 Agent 正在排序候选事件...": "Statistics Agent is ranking candidate events...",
    "注释 Agent 正在收集文献证据...": "Annotation Agent is collecting literature evidence...",
    "注释 Agent 正在进行通路富集分析...": "Annotation Agent is running pathway enrichment...",
    "解读 Agent 正在生成生物学解读...": "Interpretation Agent is generating biological interpretation...",
    "生成分析报告": "Generate Analysis Report",
    "基于当前分析结果生成专业报告": "Generate a professional report from the current analysis",
    "💡 报告内容": "💡 Report Contents",
    "📄 HTML 报告": "📄 HTML Report",
    "📑 PDF 报告": "📑 PDF Report",
    "完成分析后可生成包含统计结果、可视化和生物学解读的专业报告": "Generate a professional report with statistics, visualizations, and biological interpretation after analysis",
    "💡 提示": "💡 Tip"
  };

  var RULES = [
    function (s) {
      var p = "执行中: ";
      if (s.indexOf(p) === 0) return "Running: " + translateOne(s.slice(p.length));
      return null;
    },
    function (s) {
      var p = "请输入 ", q = " 的参数...";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Enter parameters for " + translateOne(s.slice(p.length, s.length - q.length)) + "...";
      }
      return null;
    },
    function (s) {
      var p = "我想使用 ", q = " 技能";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "I want to use the " + translateOne(s.slice(p.length, s.length - q.length)) + " skill";
      }
      return null;
    },
    function (s) {
      var p = "共找到 ", q = " 篇相关文献";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return s.slice(p.length, s.length - q.length) + " papers found";
      }
      return null;
    },
    function (s) {
      var p = "输入基因数: ", q = " | 显著条目数: ";
      var i = s.indexOf(p), j = s.indexOf(q);
      if (i === 0 && j > 0) {
        return "Input genes: " + s.slice(p.length, j) + " | Significant terms: " + s.slice(j + q.length);
      }
      return null;
    },
    function (s) {
      var p = "正在加载 ", q = " 的信息...";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Loading information for " + s.slice(p.length, s.length - q.length) + "...";
      }
      return null;
    },
    function (s) {
      var p = "未找到 ", q = " 的剪接事件";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "No splicing events found for " + s.slice(p.length, s.length - q.length);
      }
      return null;
    },
    function (s) {
      var p = "报告生成失败 (", q = ")";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Report generation failed (" + s.slice(p.length, s.length - q.length) + ")";
      }
      return null;
    },
    function (s) {
      var p = "API 错误: ";
      if (s.indexOf(p) === 0) return "API error: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "上传失败 (";
      if (s.indexOf(p) === 0) return "Upload failed (" + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "分析失败 (";
      if (s.indexOf(p) === 0) return "Analysis failed (" + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "❌ 分析失败: ";
      if (s.indexOf(p) === 0) return "❌ Analysis failed: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "❌ 执行出错: ";
      if (s.indexOf(p) === 0) return "❌ Execution error: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "操作失败：";
      if (s.indexOf(p) !== 0) return null;
      var out = "Operation failed: " + s.slice(p.length);
      return out
        .split("请检查：").join("Please check: ")
        .split("文件格式是否正确").join("whether the file format is correct")
        .split("文件大小是否过大").join("whether the file is too large")
        .split("网络连接是否正常").join("whether the network connection is working");
    },
    function (s) {
      var p = "分析请求失败：";
      if (s.indexOf(p) !== 0) return null;
      var out = "Analysis request failed: " + s.slice(p.length);
      var q = "（分析可能仍在后台运行，请稍后刷新查看）";
      if (out.slice(-q.length) === q) {
        out = out.slice(0, out.length - q.length) + " (the analysis may still be running in the background; refresh later)";
      }
      return out;
    }
  ];

  var ATTRS = ["placeholder", "title"];
  var NL2 = String.fromCharCode(10, 10);
  var originalText = new WeakMap();
  var originalAttrs = new WeakMap();
  var lang = "zh";
  try {
    var saved = localStorage.getItem("splicegaip_lang");
    if (saved === "en" || saved === "zh" || saved === "zh-Hant") lang = saved;
  } catch (e) {}

  function replaceTrimmed(text, out) {
    var trimmed = text.trim();
    var i = text.indexOf(trimmed);
    if (i < 0) return text;
    return text.slice(0, i) + out + text.slice(i + trimmed.length);
  }

  function translateOne(text) {
    if (lang === "zh-Hant") return toTraditional(text);
    var trimmed = text.trim();
    if (!trimmed) return text;
    if (Object.prototype.hasOwnProperty.call(DICT, trimmed)) {
      return replaceTrimmed(text, DICT[trimmed]);
    }
    for (var i = 0; i < RULES.length; i++) {
      var out = RULES[i](trimmed);
      if (out) return replaceTrimmed(text, out);
    }
    return text;
  }

  function translateText(text) {
    if (lang === "zh-Hant") return toTraditional(text);
    if (text.indexOf(NL2) === -1) return translateOne(text);
    return text.split(NL2).map(translateOne).join(NL2);
  }

  function translateTextNode(node) {
    var parent = node.parentElement;
    if (!parent || parent.closest("script,style,[data-no-i18n]")) return;
    var original = originalText.get(node);
    if (original === undefined) {
      original = node.nodeValue;
      originalText.set(node, original);
    }
    var target = lang === "zh" ? original : translateText(original);
    if (node.nodeValue !== target) node.nodeValue = target;
  }

  function translateAttrs(el) {
    if (el.closest("script,style,[data-no-i18n]")) return;
    var store = originalAttrs.get(el);
    if (!store) {
      store = {};
      originalAttrs.set(el, store);
    }
    for (var i = 0; i < ATTRS.length; i++) {
      var name = ATTRS[i];
      if (!el.hasAttribute(name)) continue;
      if (!Object.prototype.hasOwnProperty.call(store, name)) {
        store[name] = el.getAttribute(name);
      }
      el.setAttribute(name, lang === "zh" ? store[name] : translateOne(store[name]));
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) {
      translateTextNode(root);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) translateAttrs(root);
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
    var node = walker.nextNode();
    while (node) {
      if (node.nodeType === 3) translateTextNode(node);
      else translateAttrs(node);
      node = walker.nextNode();
    }
  }

  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var m = mutations[i];
      if (m.type === "characterData") {
        var node = m.target;
        var stored = originalText.get(node);
        var expected = stored === undefined ? undefined : (lang === "zh" ? stored : translateText(stored));
        if (node.nodeValue === expected) continue;
        originalText.set(node, node.nodeValue);
        translateTextNode(node);
      } else if (m.type === "attributes") {
        var el = m.target;
        if (!el || el.nodeType !== 1) continue;
        var store = originalAttrs.get(el);
        if (!store) {
          store = {};
          originalAttrs.set(el, store);
        }
        var name = m.attributeName;
        var current = el.getAttribute(name);
        var wanted = store[name] === undefined ? undefined : (lang === "zh" ? store[name] : translateOne(store[name]));
        if (current === wanted) continue;
        store[name] = current;
        translateAttrs(el);
      } else {
        for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
      }
    }
  });

  function translateTitle() {
    var el = document.querySelector("title");
    if (!el) return;
    if (!el.dataset.zh) el.dataset.zh = el.textContent;
    el.textContent = lang === "zh" ? el.dataset.zh : translateOne(el.dataset.zh);
  }

  function applyLanguage(next) {
    lang = next === "en" || next === "zh-Hant" ? next : "zh";
    document.documentElement.lang = lang === "en" ? "en" : (lang === "zh-Hant" ? "zh-Hant" : "zh-CN");
    try {
      localStorage.setItem("splicegaip_lang", lang);
      document.cookie = "splicegaip_lang=" + lang + "; path=/; max-age=31536000; SameSite=Lax";
    } catch (e) {}
    var buttons = document.querySelectorAll(".lang-toggle button");
    for (var i = 0; i < buttons.length; i++) {
      var active = buttons[i].getAttribute("data-lang") === lang;
      buttons[i].classList.toggle("active", active);
      buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
    walk(document.body);
    translateTitle();
    try {
      document.dispatchEvent(new CustomEvent("splicegaip:language", { detail: { lang: lang } }));
    } catch (e) {}
  }

  window.alert = function (message) {
    var notice = document.createElement("div");
    notice.setAttribute("role", "status");
    notice.textContent = lang === "zh" ? String(message) : translateText(String(message));
    notice.style.cssText = "position:fixed;right:24px;bottom:24px;z-index:99999;max-width:520px;padding:16px 20px;border-radius:12px;background:#12313b;color:#fff;box-shadow:0 12px 36px #0008;white-space:pre-line;font-size:14px;cursor:pointer";
    notice.onclick = function () { notice.remove(); };
    document.body.appendChild(notice);
    setTimeout(function () { notice.remove(); }, 8000);
  };
  var nativeConfirm = window.confirm.bind(window);
  window.confirm = function (message) {
    return nativeConfirm(lang === "zh" ? String(message) : translateText(String(message)));
  };

  window.__splicegaipI18n = {
    apply: applyLanguage,
    translate: translateOne,
    getLang: function () { return lang; }
  };

  function init() {
    var buttons = document.querySelectorAll(".lang-toggle button");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function () {
        applyLanguage(this.getAttribute("data-lang"));
      });
    }
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRS
    });
    applyLanguage(lang);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>
</body>
</html>"""


def render(title: str = "SpliceGAIP") -> HTMLResponse:
    """Render the modern SpliceGAIP web UI."""
    return HTMLResponse(content=_HTML.replace("__TITLE__", title))
