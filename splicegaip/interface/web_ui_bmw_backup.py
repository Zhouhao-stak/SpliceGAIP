"""SpliceGAIP web UI — BMW-corporate design dialect, served by the FastAPI app.

Design tokens come from the BMW corporate design system
(``design-md/bmw/DESIGN.md``):

* canvas ``#ffffff``, dark-navy hero band ``#1a2129``, soft footer ``#f7f7f7``
* BMW Blue ``#1c69d4`` is the single action colour; press → ``#0653b6``
* BMW Type Next Latin substitute: Inter / Segoe UI, weight 700 display
  against weight 300 body
* ``border-radius: 0`` on every button, card, input and chip
* no drop shadows — depth comes from light/dark colour-block contrast
* 64px nav, 48px buttons and inputs, 24px card padding, 80px section rhythm
* the M tricolor stripe (``#0066b1`` → ``#1c69d4`` → ``#e22718``) is used
  only as a 4px accent divider, never as a fill

Everything rendered here maps onto a real engine field: the payload is
``AnalysisOutcome.summary()`` plus ``/api/projects`` and ``/api/status/{id}``.
No placeholder or decorative-only data is invented.

Kept as a single HTML string on purpose: no template files to ship, so the
PyInstaller bundle needs no extra data files and ``/`` always renders.
"""

from __future__ import annotations

from fastapi.responses import HTMLResponse

# Placeholders replaced by render(): __TITLE__ is the app name/version line.
_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpliceGAIP · AI 驱动可变剪接分析平台</title>
<style>
:root{
  --primary:#1c69d4; --primary-active:#0653b6; --primary-disabled:#d6d6d6;
  --ink:#262626; --body:#3c3c3c; --body-strong:#1a1a1a;
  --muted:#6b6b6b; --muted-soft:#9a9a9a;
  --hairline:#e6e6e6; --hairline-strong:#cccccc;
  --canvas:#ffffff; --surface-soft:#f7f7f7; --surface-card:#fafafa;
  --surface-strong:#ebebeb; --dark:#1a2129; --dark-elevated:#262e38;
  --on-dark:#ffffff; --on-dark-soft:#bbbbbb;
  --success:#22c55e; --warning:#f59e0b; --error:#dc2626;
  --m-blue-light:#0066b1; --m-blue-dark:#1c69d4; --m-red:#e22718;
  --font:"Inter","Segoe UI","Microsoft YaHei",system-ui,-apple-system,Roboto,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--canvas);color:var(--body);font-family:var(--font);
     font-weight:300;font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer;border:0;background:none;border-radius:0}
input,textarea,select{font-family:inherit;font-size:16px;font-weight:300;border-radius:0}

/* ---------- primitives ---------- */
.m-stripe{height:4px;display:flex}
.m-stripe i{flex:1}
.m-stripe i:nth-child(1){background:var(--m-blue-light)}
.m-stripe i:nth-child(2){background:var(--m-blue-dark)}
.m-stripe i:nth-child(3){background:var(--m-red)}

.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;
     height:48px;padding:0 32px;background:var(--primary);color:#fff;
     font-size:14px;font-weight:700;letter-spacing:.5px;border-radius:0;
     transition:background .18s ease}
.btn:hover{background:var(--primary-active)}
.btn[disabled]{background:var(--primary-disabled);color:var(--muted);cursor:not-allowed}
.btn-secondary{background:var(--canvas);color:var(--ink);border:1px solid var(--hairline-strong)}
.btn-secondary:hover{background:var(--surface-soft)}
.btn-secondary[disabled]{color:var(--muted-soft);border-color:var(--hairline);cursor:not-allowed}
.btn-ghost{height:40px;padding:0 18px;background:transparent;color:var(--ink);
           border:1px solid var(--hairline-strong);font-size:13px;font-weight:700;letter-spacing:1px}
.btn-ghost:hover{background:var(--surface-soft)}

.label-up{font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
.display-xl{font-size:64px;font-weight:700;line-height:1.05}
.display-lg{font-size:44px;font-weight:700;line-height:1.1}
.display-md{font-size:32px;font-weight:700;line-height:1.15}
.title-md{font-size:18px;font-weight:700;line-height:1.4}
.caption{font-size:12px;font-weight:400;letter-spacing:.5px;color:var(--muted)}
.mono{font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace}

.wrap{max-width:1320px;margin:0 auto;padding:0 32px}
.section{padding:80px 0}

/* ---------- nav ---------- */
.nav{position:sticky;top:0;z-index:60;background:var(--canvas);
     border-bottom:1px solid var(--hairline);height:64px}
.nav-in{display:flex;align-items:center;justify-content:space-between;height:64px}
.brand{display:flex;align-items:center;gap:14px}
.brand-mark{width:36px;height:36px;background:var(--dark);color:#fff;display:flex;
            align-items:center;justify-content:center;font-weight:700;font-size:15px;letter-spacing:.5px}
.brand-name{font-size:18px;font-weight:700;letter-spacing:1.2px;color:var(--ink)}
.brand-sub{font-size:11px;font-weight:400;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase}
.nav-links{display:flex;align-items:center;gap:28px}
.nav-link{font-size:14px;font-weight:400;letter-spacing:.3px;color:var(--body);
          padding:20px 0;border-bottom:2px solid transparent;background:none}
.nav-link:hover{color:var(--ink)}
.nav-link.active{color:var(--ink);font-weight:700;border-bottom-color:var(--ink)}
.badge{display:inline-flex;align-items:center;gap:7px;height:28px;padding:0 12px;
       background:var(--surface-soft);border:1px solid var(--hairline);
       font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.badge .dot{width:7px;height:7px;border-radius:50%;background:var(--success)}
.badge.off .dot{background:var(--muted-soft)}

/* ---------- hero ---------- */
.hero{background:var(--dark);color:var(--on-dark);padding:80px 0 72px}
.hero-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:64px;align-items:end}
.hero h1{color:var(--on-dark)}
.hero .lede{margin-top:22px;font-size:18px;font-weight:300;line-height:1.6;color:var(--on-dark-soft);max-width:52ch}
.hero-actions{margin-top:36px;display:flex;gap:14px;flex-wrap:wrap}
.hero-facts{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:rgba(255,255,255,.14)}
.hero-facts div{background:var(--dark-elevated);padding:20px 22px}
.hero-facts b{display:block;font-size:24px;font-weight:700;line-height:1.25;color:var(--on-dark)}
.hero-facts span{display:block;margin-top:6px;font-size:12px;font-weight:400;letter-spacing:1.2px;
                 text-transform:uppercase;color:var(--on-dark-soft)}

/* ---------- workflow steps ---------- */
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--hairline);
       border:1px solid var(--hairline)}
.step{background:var(--canvas);padding:24px}
.step-no{font-size:13px;font-weight:700;letter-spacing:1.5px;color:var(--primary)}
.step h3{margin:10px 0 8px;font-size:18px;font-weight:700;color:var(--ink);line-height:1.4}
.step p{font-size:14px;font-weight:300;color:var(--body)}

/* ---------- form ---------- */
.card{background:var(--canvas);border:1px solid var(--hairline);padding:24px}
.field{margin-bottom:20px}
.field:last-child{margin-bottom:0}
.field > label{display:block;margin-bottom:8px;font-size:13px;font-weight:700;
               letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
textarea,input[type=text],input[type=number],input[type=password],select{width:100%;background:var(--canvas);
  color:var(--ink);border:1px solid var(--hairline);padding:14px 16px;height:48px;outline:none;
  transition:border-color .15s ease}
select{-webkit-appearance:none;appearance:none;
  background-image:linear-gradient(45deg,transparent 50%,#6a6a6a 50%),linear-gradient(135deg,#6a6a6a 50%,transparent 50%);
  background-position:calc(100% - 20px) 21px,calc(100% - 14px) 21px;
  background-size:6px 6px,6px 6px;background-repeat:no-repeat}
textarea{height:auto;min-height:96px;resize:vertical;line-height:1.55}
textarea:focus,input:focus{border-color:var(--ink)}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}

.drop{border:1px dashed var(--hairline-strong);background:var(--surface-card);
      padding:32px 24px;text-align:center;transition:background .18s ease,border-color .18s ease}
.drop.over{background:var(--surface-soft);border-color:var(--primary)}
.drop .icon{font-size:26px;font-weight:700;color:var(--primary);line-height:1}
.drop .txt{margin-top:12px;font-size:16px;font-weight:300;color:var(--body)}
.drop .txt b{font-weight:700;color:var(--ink)}
.drop .sub{margin-top:6px;font-size:12px;color:var(--muted-soft)}
input[type=file]{display:none}
.file-btn{display:inline-block;margin-top:18px;height:48px;line-height:46px;padding:0 32px;
          background:var(--canvas);color:var(--ink);border:1px solid var(--hairline-strong);
          font-size:14px;font-weight:700;letter-spacing:.5px;cursor:pointer}
.file-btn:hover{background:var(--surface-soft)}

.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.chip{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;background:var(--canvas);
      border:1px solid var(--hairline-strong);font-size:12px;font-weight:400;color:var(--ink)}
.chip.ok{border-left:3px solid var(--success)}
.chip .x{color:var(--muted);font-weight:700;font-size:13px;cursor:pointer}
.chip .x:hover{color:var(--error)}

.presets{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.preset{padding:8px 14px;background:var(--canvas);border:1px solid var(--hairline-strong);
        font-size:13px;font-weight:300;color:var(--ink)}
.preset:hover{background:var(--surface-soft)}
.preset.on{background:var(--ink);color:var(--on-dark);border-color:var(--ink)}

details.adv{margin-top:24px;border:1px solid var(--hairline);background:var(--surface-card)}
details.adv summary{padding:16px 24px;cursor:pointer;font-size:13px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);list-style:none}
details.adv summary::-webkit-details-marker{display:none}
details.adv summary::after{content:"+";float:right;color:var(--ink);font-size:16px}
details.adv[open] summary::after{content:"–"}
details.adv .body{padding:0 24px 24px}
details.adv .note{font-size:12px;color:var(--muted-soft);margin-top:14px}

.runbar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;margin-top:32px;
        padding-top:32px;border-top:1px solid var(--hairline)}
.runbar .grow{flex:1;min-width:240px;font-size:14px;color:var(--muted)}

/* ---------- progress ---------- */
.prog{background:var(--dark);color:var(--on-dark);padding:48px 0}
.prog-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap}
.prog-head .elapsed{font-size:32px;font-weight:700;color:var(--on-dark)}
.prog-track{margin-top:28px;height:4px;background:rgba(255,255,255,.16)}
.prog-track i{display:block;height:4px;background:var(--primary);width:0;transition:width .6s ease}
.stages{margin-top:28px;display:grid;grid-template-columns:repeat(6,1fr);gap:1px;
        background:rgba(255,255,255,.14)}
.stage{background:var(--dark-elevated);padding:16px 14px}
.stage .n{font-size:11px;font-weight:700;letter-spacing:1.2px;color:var(--on-dark-soft)}
.stage .t{margin-top:6px;font-size:13px;font-weight:700;color:var(--on-dark-soft);line-height:1.35}
.stage.done .t{color:var(--on-dark)}
.stage.now{background:var(--primary)}
.stage.now .t,.stage.now .n{color:#fff}
.stage .k{margin-top:8px;font-size:11px;color:var(--on-dark-soft)}

/* ---------- results ---------- */
.res-head{display:flex;align-items:flex-end;justify-content:space-between;gap:32px;flex-wrap:wrap}
.res-id{font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--primary)}
.tabs{display:flex;gap:32px;border-bottom:1px solid var(--hairline);margin-top:40px;overflow-x:auto}
.tab{padding:12px 0;font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
     color:var(--muted);border-bottom:2px solid transparent;white-space:nowrap}
.tab:hover{color:var(--ink)}
.tab.on{color:var(--ink);border-bottom-color:var(--ink)}
.tabpanes{padding-top:40px}
.pane{display:none}
.pane.on{display:block}

.specs{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--hairline);
       border:1px solid var(--hairline)}
.spec{background:var(--canvas);padding:24px}
.spec b{display:block;font-size:32px;font-weight:700;line-height:1.15;color:var(--ink)}
.spec span{display:block;margin-top:8px;font-size:12px;font-weight:700;letter-spacing:1.2px;
           text-transform:uppercase;color:var(--muted)}

.kv{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--hairline);
    border:1px solid var(--hairline)}
.kv div{background:var(--canvas);padding:16px 18px}
.kv span{display:block;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.kv b{display:block;margin-top:6px;font-size:16px;font-weight:700;color:var(--ink);word-break:break-word}

.lead{font-size:18px;font-weight:300;line-height:1.65;color:var(--body-strong);
      border-left:3px solid var(--primary);padding-left:20px}
.prose{font-size:16px;font-weight:300;line-height:1.75;color:var(--body)}
.prose p + p{margin-top:14px}

table{width:100%;border-collapse:collapse;font-size:14px}
thead th{text-align:left;padding:14px 12px;font-size:12px;font-weight:700;letter-spacing:1.2px;
         text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--hairline-strong)}
tbody td{padding:14px 12px;border-bottom:1px solid var(--hairline);vertical-align:middle}
tbody tr:hover{background:var(--surface-card)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.gene{font-size:16px;font-weight:700;color:var(--ink)}
.tag{display:inline-block;padding:3px 8px;background:var(--surface-strong);
     font-size:11px;font-weight:700;letter-spacing:.8px;color:var(--ink);text-transform:uppercase}
.rank{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;
      background:var(--ink);color:#fff;font-size:12px;font-weight:700}

.bar{position:relative;height:8px;background:var(--surface-strong);min-width:120px}
.bar i{position:absolute;top:0;bottom:0;background:var(--primary)}
.bar.zero i{background:var(--hairline-strong)}
.dpsi{display:flex;align-items:center;gap:10px}
.dpsi .v{font-size:14px;font-weight:700;color:var(--ink);min-width:64px;text-align:right;
         font-variant-numeric:tabular-nums}

.stack{display:flex;height:8px;background:var(--surface-strong);margin-top:6px;min-width:150px}
.stack i{height:8px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}
.legend span{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:var(--muted)}
.legend i{width:10px;height:10px;display:inline-block}

.enr{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--hairline);
     border:1px solid var(--hairline)}
.enr .cell{background:var(--canvas);padding:24px}
.enr .ont{font-size:11px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--primary)}
.enr .term{margin-top:8px;font-size:18px;font-weight:700;color:var(--ink);line-height:1.4}
.enr .nums{margin-top:16px;display:flex;gap:24px;flex-wrap:wrap}
.enr .nums div b{display:block;font-size:24px;font-weight:700;color:var(--ink);line-height:1.2}
.enr .nums div span{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.enr .genes{margin-top:14px;display:flex;flex-wrap:wrap;gap:6px}
.enr .genes em{font-style:normal;padding:3px 8px;background:var(--surface-strong);
               font-size:12px;font-weight:700;color:var(--ink)}

.figs{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--hairline);
      border:1px solid var(--hairline)}
.fig{background:var(--canvas);padding:16px}
.fig .plate{background:var(--surface-card);padding:12px;cursor:zoom-in}
.fig img{width:100%;background:#fff}
.fig .cap{margin-top:14px}
.fig .cap b{display:block;font-size:16px;font-weight:700;color:var(--ink)}
.fig .cap span{display:block;margin-top:6px;font-size:12px;color:var(--muted);line-height:1.5}

.evid{border:1px solid var(--hairline)}
.evid .row{display:grid;grid-template-columns:200px 1fr;gap:1px;background:var(--hairline)}
.evid .row + .row{border-top:1px solid var(--hairline)}
.evid .g{background:var(--surface-card);padding:18px 20px}
.evid .g b{font-size:18px;font-weight:700;color:var(--ink)}
.evid .g span{display:block;margin-top:4px;font-size:11px;font-weight:700;letter-spacing:1px;
              text-transform:uppercase;color:var(--muted)}
.evid .t{background:var(--canvas);padding:18px 20px}
.evid .t p{font-size:14px;font-weight:300;line-height:1.65;color:var(--body)}
.evid .t .src{margin-top:8px;font-size:12px;color:var(--muted)}

ul.plain{list-style:none}
ul.plain li{padding:14px 0;border-bottom:1px solid var(--hairline);font-size:15px;
            font-weight:300;line-height:1.65;color:var(--body)}
ul.plain li:last-child{border-bottom:0}
ul.bullets{list-style:none}
ul.bullets li{position:relative;padding:12px 0 12px 22px;font-size:15px;font-weight:300;
              line-height:1.6;color:var(--body);border-bottom:1px solid var(--hairline)}
ul.bullets li:last-child{border-bottom:0}
ul.bullets li::before{content:"";position:absolute;left:0;top:21px;width:8px;height:2px;background:var(--primary)}

.log{width:100%;font-size:13px}
.log td{padding:10px 12px;border-bottom:1px solid var(--hairline);vertical-align:top}
.log td.a{font-weight:700;color:var(--ink);white-space:nowrap}
.log .st{padding:2px 8px;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.log .st.ok{background:#e6f7ee;color:#0f7b3d}
.log .st.warn{background:#fdf3e3;color:#a35c07}
.log .st.err{background:#fdecea;color:#a5150c}

.dl{display:flex;gap:14px;flex-wrap:wrap;margin-top:32px;padding-top:32px;border-top:1px solid var(--hairline)}

.empty{padding:56px 24px;text-align:center;border:1px dashed var(--hairline-strong);
       background:var(--surface-card);font-size:15px;font-weight:300;color:var(--muted)}

/* ---------- AI (model enrichment) ---------- */
.ai-band{display:flex;align-items:center;gap:12px;padding:14px 18px;margin-top:16px;
         background:var(--surface-soft);border-left:4px solid var(--primary)}
.ai-band.off{background:var(--surface-card);border-left-color:var(--hairline-strong)}
.ai-band .t{font-size:15px;font-weight:700;color:var(--ink)}
.ai-band .s{font-size:12px;font-weight:400;color:var(--muted)}
.ai-dot{width:8px;height:8px;border-radius:50%;background:var(--success);flex:none}
.ai-dot.off{background:var(--muted-soft)}
.ai-block{padding:24px;background:var(--surface-card);border-left:4px solid var(--primary);margin-top:20px}
.ai-block .h{font-size:11px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--primary)}
.ai-block .b{margin-top:12px;font-size:15px;font-weight:300;line-height:1.72;color:var(--body)}
.ai-lead{font-size:19px;font-weight:700;line-height:1.55;color:var(--ink);margin-top:16px}
.ai-cards{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--hairline);
          border:1px solid var(--hairline);margin-top:20px}
.ai-card{background:var(--canvas);padding:24px}
.ai-card .g{font-size:17px;font-weight:700;color:var(--ink)}
.ai-card .n{margin-top:10px;font-size:14px;font-weight:300;line-height:1.65;color:var(--body)}
.ai-quote{margin-top:8px;font-size:13px;font-weight:700;letter-spacing:.6px;color:var(--muted)}
.ai-apply{margin-left:auto;padding:8px 16px;background:var(--primary);color:#fff;border:0;
          font-family:var(--font);font-size:12px;font-weight:700;letter-spacing:1px;
          text-transform:uppercase;cursor:pointer}
.ai-apply:hover{background:var(--primary-active)}
.ai-meta{margin-top:32px;padding-top:20px;border-top:1px solid var(--hairline);
         font-size:12px;font-weight:400;color:var(--muted);line-height:1.7}
.ai-cfg{border:1px solid var(--hairline);background:var(--surface-card);padding:24px;margin-bottom:24px}
.ai-cfg > summary{padding:0;cursor:pointer;list-style:none;font-size:13px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
.ai-cfg > summary::-webkit-details-marker{display:none}
.ai-cfg > summary::after{content:"+";float:right;color:var(--ink);font-size:16px}
.ai-cfg[open] > summary::after{content:"–"}
.ai-cfg .body{margin-top:20px}
.ai-cfg .row{margin-top:16px}
.ai-cfg .lbl{display:block;margin-bottom:6px;font-size:12px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.ai-cfg .hint{margin-top:8px;font-size:12px;font-weight:300;color:var(--muted-soft);line-height:1.6}
.ai-save{margin-top:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.ai-save button{height:48px;padding:0 32px;background:var(--ink);color:#fff;border:0;
  font-family:var(--font);font-size:13px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  cursor:pointer}
.ai-save button:hover{background:var(--primary)}
.ai-save button[disabled]{background:var(--muted-soft);cursor:default}
.ai-save .path{font-size:12px;color:var(--muted);word-break:break-all}

/* ---------- messages ---------- */
.msg{margin-top:20px;padding:16px 20px;border-left:3px solid;font-size:14px;font-weight:300;display:none}
.msg.on{display:block}
.msg.busy{background:#eef3fd;border-color:var(--primary);color:#14468f}
.msg.ok{background:#e6f7ee;border-color:var(--success);color:#0f7b3d}
.msg.err{background:#fdecea;border-color:var(--error);color:#a5150c}

/* ---------- history drawer ---------- */
.drawer{position:fixed;top:64px;right:0;bottom:0;width:420px;background:var(--canvas);
        border-left:1px solid var(--hairline);z-index:70;transform:translateX(100%);
        transition:transform .24s ease;overflow-y:auto}
.drawer.on{transform:translateX(0)}
.drawer-h{padding:24px;border-bottom:1px solid var(--hairline);display:flex;
          align-items:center;justify-content:space-between}
.drawer-b{padding:16px 24px 32px}
.hist{padding:16px 0;border-bottom:1px solid var(--hairline);cursor:pointer}
.hist:hover{background:var(--surface-card)}
.hist b{display:block;font-size:15px;font-weight:700;color:var(--ink)}
.hist span{display:block;margin-top:4px;font-size:12px;color:var(--muted)}
.hist .q{margin-top:8px;font-size:13px;font-weight:300;color:var(--body);
         display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

/* ---------- lightbox ---------- */
.lb{position:fixed;inset:0;background:rgba(26,33,41,.94);z-index:100;display:none;
    align-items:center;justify-content:center;padding:48px}
.lb.on{display:flex}
.lb img{max-width:100%;max-height:78vh;background:#fff}
.lb .meta{position:absolute;bottom:0;left:0;right:0;background:var(--dark-elevated);
          color:var(--on-dark);padding:20px 32px}
.lb .meta b{font-size:18px;font-weight:700}
.lb .meta span{display:block;margin-top:6px;font-size:13px;font-weight:300;color:var(--on-dark-soft)}
.lb .x{position:absolute;top:20px;right:24px;color:#fff;font-size:28px;font-weight:700;line-height:1}

/* ---------- footer ---------- */
footer{background:var(--surface-soft);padding:64px 0 32px;border-top:1px solid var(--hairline)}
.fcols{display:grid;grid-template-columns:repeat(4,1fr);gap:32px}
.fcols h4{font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
          color:var(--ink);margin-bottom:14px}
.fcols p,.fcols li{font-size:14px;font-weight:300;color:var(--body);line-height:1.7}
.fcols ul{list-style:none}
.fbottom{margin-top:48px;padding-top:24px;border-top:1px solid var(--hairline);
         display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;
         font-size:12px;color:var(--muted)}

@media (max-width:1180px){
  .hero-grid{grid-template-columns:1fr;gap:40px}
  .specs{grid-template-columns:repeat(3,1fr)}
  .enr{grid-template-columns:repeat(2,1fr)}
  .figs{grid-template-columns:repeat(2,1fr)}
  .grid-4{grid-template-columns:repeat(2,1fr)}
}
@media (max-width:860px){
  .wrap{padding:0 20px}
  .section{padding:56px 0}
  .display-xl{font-size:40px}
  .display-lg{font-size:32px}
  .steps,.stages{grid-template-columns:1fr}
  .specs,.kv,.enr,.figs,.grid-2,.grid-4,.fcols{grid-template-columns:1fr}
  .evid .row{grid-template-columns:1fr}
  .drawer{width:100%}
  .nav-links{gap:16px}
  .brand-sub{display:none}
}
</style>
</head>
<body>

<div class="m-stripe"><i></i><i></i><i></i></div>

<nav class="nav">
  <div class="wrap nav-in">
    <div class="brand">
      <div class="brand-mark">SG</div>
      <div>
        <div class="brand-name">SPLICEGAIP</div>
        <div class="brand-sub">Alternative Splicing Intelligence</div>
      </div>
    </div>
    <div class="nav-links">
      <a class="nav-link active" href="#work">分析工作台</a>
      <a class="nav-link" href="#results">结果</a>
      <button class="nav-link" id="histBtn">历史项目</button>
      <span class="badge off" id="modeBadge"><i class="dot"></i><span>检测中</span></span>
    </div>
  </div>
</nav>

<header class="hero">
  <div class="wrap hero-grid">
    <div>
      <div class="label-up" style="color:#8fb6ea">__TITLE__</div>
      <h1 class="display-xl" style="margin-top:18px">可变剪接<br>下游分析平台</h1>
      <p class="lede">上传 rMATS / SUPPA2 / MAJIQ / LeafCutter 或标准剪接事件表，
         多智能体流水线自动完成质控、显著性筛选、候选基因综合排序、
         功能富集与文献证据检索，并输出出版级图件与报告。</p>
      <div class="hero-actions">
        <button class="btn" id="heroRun">开始一次分析</button>
        <a class="btn btn-secondary" href="#results" id="heroRes" style="display:none">查看结果</a>
      </div>
    </div>
    <div class="hero-facts">
      <div><b>5 种</b><span>输入格式</span></div>
      <div><b>6 张</b><span>出版级图件</span></div>
      <div><b>4 项</b><span>排序评分维度</span></div>
      <div><b>2 种</b><span>报告格式</span></div>
    </div>
  </div>
</header>

<section class="section" style="padding-bottom:0">
  <div class="wrap">
    <div class="steps">
      <div class="step"><div class="step-no">01</div><h3>上传数据</h3>
        <p>支持 5 种剪接分析工具输出，可同时附带样本分组、基因注释与差异表达表。</p></div>
      <div class="step"><div class="step-no">02</div><h3>描述目标</h3>
        <p>用一句话说明你想回答的问题，或直接使用内置的分析目标模板。</p></div>
      <div class="step"><div class="step-no">03</div><h3>获取结果</h3>
        <p>查看候选基因排序、富集通路、六张图件与文献证据，下载 HTML / PDF 报告。</p></div>
    </div>
  </div>
</section>

<main class="section" id="work">
  <div class="wrap">
    <div class="label-up">分析工作台</div>
    <h2 class="display-lg" style="margin-top:12px;color:var(--ink)">配置一次分析</h2>

    <div class="card" style="margin-top:32px">
      <div id="aiBand"></div>
      <div class="field">
        <label>01 · 数据文件</label>
        <div class="drop" id="drop">
          <div class="icon">↑</div>
          <div class="txt">把文件拖到这里，或 <b>点击选择</b></div>
          <div class="sub">rMATS <span class="mono">*.MATS.JC.txt</span> · SUPPA2 <span class="mono">*.psi.tsv</span>
            · MAJIQ · LeafCutter · 标准表 <span class="mono">AS_event_master.tsv</span>
            · 差异结果 <span class="mono">*.csv</span></div>
          <label class="file-btn" for="files">选择文件</label>
          <input type="file" id="files" multiple>
        </div>
        <div class="chips" id="fileList"></div>
        <div class="caption" id="fmtHint" style="margin-top:12px"></div>
      </div>

      <div class="field" style="margin-top:28px">
        <label>02 · 分析目标</label>
        <textarea id="query" rows="3">分析RNA剪接变化：找出两组之间差异显著的剪接事件并排序候选基因</textarea>
        <div class="presets" id="presets"></div>
        <div id="aiUnderstand"></div>
      </div>

      <details class="adv">
        <summary>高级参数（可选）</summary>
        <div class="body">
          <div class="grid-4" style="margin-top:20px">
            <div><label class="caption" style="display:block;margin-bottom:6px">FDR 阈值</label>
              <input type="number" id="p_fdr" step="0.01" min="0" max="1" value="0.05"></div>
            <div><label class="caption" style="display:block;margin-bottom:6px">|ΔPSI| 阈值</label>
              <input type="number" id="p_dpsi" step="0.01" min="0" max="1" value="0.1"></div>
            <div><label class="caption" style="display:block;margin-bottom:6px">最少支持读数</label>
              <input type="number" id="p_reads" step="1" min="0" value="10"></div>
            <div><label class="caption" style="display:block;margin-bottom:6px">最少有效样本</label>
              <input type="number" id="p_samples" step="1" min="0" value="2"></div>
          </div>
          <div class="grid-2" style="margin-top:20px">
            <div><label class="caption" style="display:block;margin-bottom:6px">候选基因数量上限</label>
              <input type="number" id="p_top" step="1" min="1" value="20"></div>
            <div><label class="caption" style="display:block;margin-bottom:6px">富集显著性水平</label>
              <input type="number" id="p_alpha" step="0.01" min="0" max="1" value="0.05"></div>
          </div>
          <div class="note">留空或保持默认值即使用平台默认参数。修改后仅对本次分析生效。</div>
        </div>
      </details>

      <div class="runbar">
        <div class="grow" id="runState">尚未选择文件。</div>
        <button class="btn" id="runBtn" disabled>运行分析</button>
      </div>
      <div class="msg" id="msg"></div>
    </div>
  </div>
</main>

<section class="prog" id="progWrap" style="display:none">
  <div class="wrap">
    <div class="prog-head">
      <div>
        <div class="label-up" style="color:#8fb6ea">正在运行多智能体流水线</div>
        <div class="display-md" style="margin-top:10px;color:#fff" id="progTitle">解析与校验输入数据</div>
      </div>
      <div class="elapsed" id="elapsed">0.0s</div>
    </div>
    <div class="prog-track"><i id="progBar"></i></div>
    <div class="stages" id="stages"></div>
  </div>
</section>

<section class="section" id="results" style="display:none">
  <div class="wrap">
    <div class="res-head">
      <div>
        <div class="res-id" id="resId">—</div>
        <h2 class="display-lg" style="margin-top:10px;color:var(--ink)">分析结果</h2>
      </div>
      <div class="kv" style="width:520px;grid-template-columns:repeat(2,1fr)">
        <div><span>智能体模式</span><b id="resMode">—</b></div>
        <div><span>工具调用</span><b id="resCalls">—</b></div>
        <div><span>耗时</span><b id="resTime">—</b></div>
        <div><span>结束原因</span><b id="resStop">—</b></div>
      </div>
    </div>

    <div class="tabs" id="tabs">
      <button class="tab on" data-p="ov">概览</button>
      <button class="tab" data-p="ai">AI 解读</button>
      <button class="tab" data-p="cand">候选基因</button>
      <button class="tab" data-p="enr">富集通路</button>
      <button class="tab" data-p="fig">图件</button>
      <button class="tab" data-p="ev">文献证据</button>
      <button class="tab" data-p="lim">局限与参考</button>
      <button class="tab" data-p="log">运行日志</button>
    </div>

    <div class="tabpanes">
      <div class="pane on" id="p-ov"></div>
      <div class="pane" id="p-ai"><div id="aiConfig"></div><div id="aiReport"></div></div>
      <div class="pane" id="p-cand"></div>
      <div class="pane" id="p-enr"></div>
      <div class="pane" id="p-fig"></div>
      <div class="pane" id="p-ev"></div>
      <div class="pane" id="p-lim"></div>
      <div class="pane" id="p-log"></div>
    </div>

    <div class="dl">
      <a class="btn btn-secondary" id="dlHtml" target="_blank">下载 HTML 报告</a>
      <a class="btn btn-secondary" id="dlPdf" target="_blank">下载 PDF 报告</a>
      <button class="btn btn-secondary" id="newRun">再来一次分析</button>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <div class="fcols">
      <div>
        <h4>输入格式</h4>
        <ul>
          <li>rMATS <span class="mono">*.MATS.JC.txt</span></li>
          <li>SUPPA2 <span class="mono">*.psi.tsv</span></li>
          <li>MAJIQ / LeafCutter</li>
          <li>标准表 <span class="mono">AS_event_master.tsv</span></li>
          <li>差异结果 + PSI 矩阵 <span class="mono">*.csv</span>（如 <span class="mono">differential_splicing_results.csv</span> + <span class="mono">psi_matrix.csv</span>）</li>
        </ul>
      </div>
      <div>
        <h4>可选附加文件</h4>
        <ul>
          <li><span class="mono">sample_metadata.tsv / .csv</span> 样本分组</li>
          <li><span class="mono">gene_annotation.tsv</span> 功能注释</li>
          <li><span class="mono">differential_expression.tsv</span> 差异表达</li>
        </ul>
      </div>
      <div>
        <h4>排序评分</h4>
        <ul>
          <li>统计显著性 0.4</li>
          <li>效应量 0.3</li>
          <li>生物学相关性 0.2</li>
          <li>文献证据 0.1</li>
        </ul>
      </div>
      <div>
        <h4>交付物</h4>
        <ul>
          <li>6 张 PNG + SVG 图件</li>
          <li>自包含 HTML 报告</li>
          <li>PDF 报告</li>
          <li>可复现的项目存档</li>
        </ul>
      </div>
    </div>
    <div class="fbottom">
      <span>SpliceGAIP · AI 驱动可变剪接下游分析平台</span>
      <span>候选基因仅为假设生成，需实验验证后方可下生物学结论</span>
    </div>
  </div>
</footer>

<aside class="drawer" id="drawer">
  <div class="drawer-h">
    <div class="title-md" style="color:var(--ink)">历史项目</div>
    <button class="btn-ghost" id="drawerClose">关闭</button>
  </div>
  <div class="drawer-b" id="histList"><div class="caption">加载中…</div></div>
</aside>

<div class="lb" id="lb">
  <button class="x" id="lbX">×</button>
  <img id="lbImg" alt="">
  <div class="meta"><b id="lbT"></b><span id="lbC"></span></div>
</div>

<script>
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v === null || v === undefined ? '' : v).replace(/[&<>"']/g, (c) =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nf = (v, d) => (v === null || v === undefined || v === '') ? 'NA' : Number(v).toFixed(d === undefined ? 3 : d);
const sci = (v) => {
  if (v === null || v === undefined || v === '') return 'NA';
  const n = Number(v);
  if (!isFinite(n)) return 'NA';
  if (n === 0) return '0';
  return n < 0.001 ? n.toExponential(2) : n.toFixed(4);
};

let ST = { files: [], dir: '', result: null, busy: false };
let TIMER = null;

/* ---------------- model status ---------------- */
let LLM = { enabled: false, model: '', base_url: '', features: [], available_features: [] };

function renderAiBand() {
  const box = $('#aiBand');
  if (!box) return;
  const on = !!LLM.enabled;
  const detail = on
    ? '端点 ' + esc(LLM.base_url || '—') + ' · 本次可用能力：' + esc((LLM.features || []).join('、') || '—')
    : '到「AI 解读」页填写 API Key 即可启用 AI 目标理解、结果解读、候选基因注释、证据摘要、研究假设与自动审查；保存后无需重启。';
  box.innerHTML =
    '<div class="ai-band' + (on ? '' : ' off') + '">' +
      '<i class="ai-dot' + (on ? '' : ' off') + '"></i>' +
      '<div><div class="t">' + (on ? '已接入大模型 · ' + esc(LLM.model || '未命名模型') : '未接入大模型 · 离线确定性分析') + '</div>' +
      '<div class="s">' + detail + '</div></div>' +
    '</div>';
}

/* ---------------- query understanding ---------------- */
let UTIMER = null;
function scheduleUnderstand() {
  if (UTIMER) clearTimeout(UTIMER);
  UTIMER = setTimeout(understand, 800);
}
async function understand() {
  const box = $('#aiUnderstand');
  const query = $('#query').value.trim();
  if (!box) return;
  if (!query) { box.innerHTML = ''; return; }
  box.innerHTML = '<div class="caption" style="margin-top:14px">正在理解分析目标…</div>';
  try {
    const r = await fetch('/api/understand', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query }),
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const u = await r.json();
    const sug = u.suggested_thresholds || {};
    const hasSug = Object.keys(sug).length > 0;
    const val = (v, prefix) => (v === undefined || v === null ? '沿用默认' : prefix + v);
    let html = '<div class="ai-block">' +
      '<div class="h">AI 目标理解 · ' + (u.source === 'llm' ? '大模型解析' : '规则解析（未接入模型）') + '</div>' +
      '<div class="b">' + esc(u.goal || '') + '</div>' +
      '<div class="kv" style="margin-top:16px">' +
        '<div><span>分析类型</span><b>' + esc(u.analysis_type || 'NA') + '</b></div>' +
        '<div><span>建议 FDR</span><b>' + esc(val(sug.fdr, '< ')) + '</b></div>' +
        '<div><span>建议 |ΔPSI|</span><b>' + esc(val(sug.delta_psi, '> ')) + '</b></div>' +
        '<div><span>建议候选数</span><b>' + esc(val(sug.top_candidates, '')) + '</b></div>' +
      '</div>';
    if (u.assumptions && u.assumptions.length) {
      html += '<div class="caption" style="margin-top:14px">前提假设：' + u.assumptions.map(esc).join('；') + '</div>';
    }
    if (u.focus_genes && u.focus_genes.length) {
      html += '<div class="caption" style="margin-top:6px">用户指定关注基因：' + u.focus_genes.map(esc).join('、') + '</div>';
    }
    if (u.llm_errors && u.llm_errors.length) {
      const first = u.llm_errors[0] || {};
      html += '<div class="caption" style="margin-top:14px;color:var(--error)">' +
        '模型调用失败，已回退到规则解析：' + esc(String(first.error || '')).slice(0, 300) + '</div>';
    }
    if (hasSug) {
      html += '<div style="display:flex;align-items:center;margin-top:18px">' +
        '<span class="caption">建议参数可直接填入“高级参数”</span>' +
        '<button class="ai-apply" id="aiApply">应用建议参数</button></div>';
    }
    html += '</div>';
    box.innerHTML = html;
    const btn = $('#aiApply');
    if (btn) btn.addEventListener('click', () => {
      if (sug.fdr !== undefined) $('#p_fdr').value = sug.fdr;
      if (sug.delta_psi !== undefined) $('#p_dpsi').value = sug.delta_psi;
      if (sug.top_candidates !== undefined) $('#p_top').value = sug.top_candidates;
      say('已应用 AI 建议参数，仅对本次分析生效。', 'ok');
    });
  } catch (e) {
    box.innerHTML = '<div class="caption" style="margin-top:14px">目标理解不可用：' + esc(e.message) + '</div>';
  }
}

/* ---------------- health ---------------- */
async function health() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    const b = $('#modeBadge');
    b.className = 'badge' + (d.llm_configured ? '' : ' off');
    b.querySelector('span').textContent = d.llm_configured ? '智能体模式 · LLM' : '智能体模式 · 离线确定性';
  } catch (e) { /* server still starting */ }
  try {
    const r2 = await fetch('/api/llm/status');
    LLM = await r2.json();
  } catch (e) { /* keep defaults */ }
  renderAiBand();
  renderAiConfig();
  understand();
}

/* ---------------- model configuration (writes .env, no restart) -------- */
const PRESET_DEEPSEEK = 'deepseek-flash';

function renderAiConfig() {
  const host = $('#aiConfig');
  if (!host) return;
  const cfg = LLM.config || {};
  const v = cfg.values || {};
  const presets = cfg.presets || [];
  const on = !!LLM.enabled;
  const options = presets.map((p) =>
    '<option value="' + esc(p.id) + '">' + esc(p.label) + '</option>').join('');
  const input = (id, label, value, type, placeholder) =>
    '<div class="row"><label class="lbl" for="' + id + '">' + label + '</label>' +
    '<input id="' + id + '" type="' + type + '" value="' + esc(value || '') + '"' +
    (placeholder ? ' placeholder="' + esc(placeholder) + '" autocomplete="off"' : ' autocomplete="off"') +
    '></div>';
  const summary = on
    ? '模型配置 · 当前 ' + esc(LLM.model || '未命名模型')
    : '模型配置 · 未接入（填写后即时生效，无需重启）';
  const names = (cfg.file_names || ['.env']).map((n) => '「' + n + '」').join(' 或 ');
  const fileHint = '密钥保存在本机 ' + names + ' 中（保存时会同步更新这些文件），' +
    '不会被写进报告或日志。手动编辑文件后需要重启程序。';
  host.innerHTML =
    '<details class="ai-cfg"' + (on ? '' : ' open') + '>' +
      '<summary>' + summary + '</summary>' +
      '<div class="body">' +
        '<div class="row"><label class="lbl" for="llmPreset">服务商预设</label>' +
        '<select id="llmPreset"><option value="">自定义端点</option>' + options + '</select>' +
        '<div class="hint">选择预设会自动填好端点与模型名；DeepSeek 预设已按官方参数优化（工具调用时自动关闭推理模式，避免 400 错误）。</div></div>' +
        '<div class="grid-2" style="margin-top:16px">' +
          input('llmBase', '端点 Base URL', v.MODEL_API_BASE_URL, 'text', 'https://api.deepseek.com') +
          input('llmModel', '模型名', v.MODEL_NAME, 'text', 'deepseek-flash') +
        '</div>' +
        input('llmKey', 'API Key', v.MODEL_API_KEY, 'password', '粘贴你的密钥，仅保存在本机') +
        '<div class="ai-save">' +
          '<button id="llmSave">保存并启用</button>' +
          '<span class="path">' + esc(cfg.env_path || '.env') + '</span>' +
        '</div>' +
        '<div class="hint">' + (fileHint) + '</div>' +
        '<div class="hint" id="llmMsg">' + (on
          ? '密钥保存在本机上述 .env 文件中，不会写入报告、日志或任何联网内容。留空并保存即可关闭模型模式。'
          : '密钥只写入本机 .env，不会出现在报告里；保存成功后本页会立即切换为「已接入大模型」。') + '</div>' +
      '</div>' +
    '</details>';

  $('#llmPreset').addEventListener('change', (e) => {
    const id = e.target.value;
    if (!id) return;
    const picked = presets.find((p) => p.id === id);
    if (!picked) return;
    $('#llmBase').value = picked.values.MODEL_API_BASE_URL || '';
    $('#llmModel').value = picked.values.MODEL_NAME || '';
    if (id === PRESET_DEEPSEEK && !$('#llmKey').value.trim()) {
      $('#llmMsg').textContent = '已填入 DeepSeek V4.1-Flash 的官方端点与模型名，请粘贴 API Key 后保存。';
    }
  });
  $('#llmSave').addEventListener('click', saveAiConfig);
}

async function saveAiConfig() {
  const btn = $('#llmSave');
  const msg = $('#llmMsg');
  if (!btn || btn.disabled) return;
  const key = $('#llmKey').value.trim();
  const payload = {
    values: {
      MODEL_API_BASE_URL: $('#llmBase').value.trim(),
      MODEL_NAME: $('#llmModel').value.trim(),
    },
  };
  if (key && !/\*+$/.test(key) && key.indexOf('****') < 0) payload.values.MODEL_API_KEY = key;
  btn.disabled = true;
  btn.textContent = '保存中…';
  try {
    const r = await fetch('/api/llm/config', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) throw new Error((d && d.detail) || 'HTTP ' + r.status);
    LLM = d.status || LLM;
    LLM.config = d.config || LLM.config;
    renderAiBand();
    renderAiConfig();
    understand();
    const s = $('#llmMsg') || msg;
    if (s) {
      s.textContent = LLM.enabled
        ? '已保存并启用：' + (LLM.model || '') + ' ·  vendor=' + (LLM.provider || 'auto') +
          ' · 工具调用推理=' + (LLM.thinking_agent || 'n/a') + ' · 报告解读推理=' + (LLM.thinking_insight || 'n/a')
        : '已保存，但当前仍未启用（请检查端点与模型名是否完整）。';
    }
  } catch (e) {
    const s = $('#llmMsg');
    if (s) s.textContent = '保存失败：' + e.message + '（若文件只读，请手动编辑 .env）';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '保存并启用'; }
  }
}

/* ---------------- files ---------------- */
const MAIN_KINDS = ['rMATS JC 表', 'SUPPA2 PSI 表', 'MAJIQ 输出', 'LeafCutter 输出', '标准事件表', '差异剪接结果'];
const EXTRA_KINDS = ['样本分组', '基因注释', '差异表达', 'PSI 矩阵'];
const KNOWN = [
  [/\.MATS\.JC\.txt$/i, 'rMATS JC 表'],
  [/\.psi\.tsv$/i, 'SUPPA2 PSI 表'],
  [/MAJIQ|\.quant/i, 'MAJIQ 输出'],
  [/leafcutter|\.counts/i, 'LeafCutter 输出'],
  [/AS_event_master/i, '标准事件表'],
  [/differential_splicing|diff[_-]?splicing[_-]?results|splicing_results/i, '差异剪接结果'],
  [/psi[_-]?matrix/i, 'PSI 矩阵'],
  [/sample_metadata/i, '样本分组'],
  [/gene_annotation/i, '基因注释'],
  [/differential_expression/i, '差异表达'],
];
function kindOf(name) {
  for (let i = 0; i < KNOWN.length; i++) if (KNOWN[i][0].test(name)) return KNOWN[i][1];
  return '其他文件';
}
function renderFiles() {
  const box = $('#fileList');
  if (!ST.files.length) { box.innerHTML = ''; $('#fmtHint').textContent = ''; syncRun(); return; }
  box.innerHTML = ST.files.map((f, i) =>
    '<span class="chip' + (i === 0 ? ' ok' : '') + '">' + esc(f.name) +
    '<span class="caption">' + esc(kindOf(f.name)) + '</span>' +
    '<span class="x" data-i="' + i + '">×</span></span>').join('');
  box.querySelectorAll('.x').forEach((el) => el.addEventListener('click', () => {
    ST.files.splice(Number(el.dataset.i), 1);
    renderFiles();
  }));
  const kinds = ST.files.map((f) => kindOf(f.name));
  const mains = kinds.filter((k) => MAIN_KINDS.indexOf(k) >= 0);
  const extras = kinds.filter((k) => EXTRA_KINDS.indexOf(k) >= 0);
  let hint = '已选 ' + ST.files.length + ' 个文件。';
  if (mains.length) hint += ' 主输入识别为：' + mains.filter((v, i, a) => a.indexOf(v) === i).join('、') + '。';
  else hint += ' 未识别到已知主输入格式，将按标准表尝试解析。';
  if (extras.length) hint += ' 附加文件：' + extras.filter((v, i, a) => a.indexOf(v) === i).join('、') + '。';
  $('#fmtHint').textContent = hint;
  syncRun();
}
function syncRun() {
  const ok = ST.files.length > 0 && $('#query').value.trim().length > 0 && !ST.busy;
  $('#runBtn').disabled = !ok;
  if (ST.busy) return;
  $('#runState').textContent = ST.files.length === 0
    ? '尚未选择文件。'
    : (ST.files.length + ' 个文件已就绪，点击右侧按钮开始分析。');
}

/* ---------------- presets ---------------- */
const PRESETS = [
  '分析RNA剪接变化：找出两组之间差异显著的剪接事件并排序候选基因',
  '筛选肿瘤与癌旁之间显著的可变剪接事件，并解释其潜在生物学意义',
  '比较两组样本的外显子跳跃事件，找出 ΔPSI 最大的候选基因',
  '对差异剪接基因做功能富集分析，并检索相关文献证据',
];
$('#presets').innerHTML = PRESETS.map((p, i) =>
  '<button class="preset' + (i === 0 ? ' on' : '') + '" data-p="' + i + '">' + esc(p) + '</button>').join('');
$('#presets').querySelectorAll('.preset').forEach((el) => el.addEventListener('click', () => {
  $('#presets').querySelectorAll('.preset').forEach((o) => o.classList.remove('on'));
  el.classList.add('on');
  $('#query').value = PRESETS[Number(el.dataset.p)];
  syncRun();
  scheduleUnderstand();
}));

/* ---------------- drag & drop ---------------- */
const drop = $('#drop');
['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => {
  e.preventDefault(); drop.classList.add('over');
}));
['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => {
  e.preventDefault(); drop.classList.remove('over');
}));
drop.addEventListener('drop', (e) => {
  const list = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
  if (list.length) { ST.files = ST.files.concat(list); renderFiles(); }
});
$('#files').addEventListener('change', (e) => {
  ST.files = ST.files.concat(Array.from(e.target.files || []));
  e.target.value = '';
  renderFiles();
});
$('#query').addEventListener('input', () => { syncRun(); scheduleUnderstand(); });

/* ---------------- progress ---------------- */
const STAGES = [
  ['解析与校验输入数据', 8],
  ['筛选显著剪接事件', 12],
  ['候选基因综合排序', 12],
  ['功能富集分析', 12],
  ['检索文献证据', 16],
  ['生成图件与报告', 12],
];
$('#stages').innerHTML = STAGES.map((s, i) =>
  '<div class="stage" data-i="' + i + '"><div class="n">0' + (i + 1) + '</div>' +
  '<div class="t">' + esc(s[0]) + '</div><div class="k">' + s[1] + 's 预估</div></div>').join('');
function startProgress() {
  const t0 = Date.now();
  $('#progWrap').style.display = 'block';
  $('#results').style.display = 'none';
  const total = STAGES.reduce((a, s) => a + s[1], 0);
  TIMER = setInterval(() => {
    const el = (Date.now() - t0) / 1000;
    $('#elapsed').textContent = el.toFixed(1) + 's';
    let acc = 0, idx = STAGES.length - 1;
    for (let i = 0; i < STAGES.length; i++) {
      acc += STAGES[i][1];
      if (el <= acc) { idx = i; break; }
    }
    $('#progTitle').textContent = STAGES[idx][0];
    $('#progBar').style.width = Math.min(96, (el / total) * 100).toFixed(1) + '%';
    document.querySelectorAll('.stage').forEach((node) => {
      const i = Number(node.dataset.i);
      node.className = 'stage' + (i < idx ? ' done' : (i === idx ? ' now' : ''));
    });
  }, 200);
}
function stopProgress() {
  if (TIMER) { clearInterval(TIMER); TIMER = null; }
  $('#progBar').style.width = '100%';
  document.querySelectorAll('.stage').forEach((node) => { node.className = 'stage done'; });
  setTimeout(() => { $('#progWrap').style.display = 'none'; }, 600);
}

/* ---------------- messages ---------------- */
function say(text, kind) {
  const m = $('#msg');
  m.textContent = text;
  m.className = 'msg on ' + (kind || 'busy');
}

/* ---------------- run ---------------- */
function collectThresholds() {
  const num = (id) => {
    const v = $(id).value.trim();
    return v === '' ? null : Number(v);
  };
  return {
    fdr: num('#p_fdr'),
    delta_psi: num('#p_dpsi'),
    min_support_reads: num('#p_reads'),
    min_valid_samples: num('#p_samples'),
    top_candidates: num('#p_top'),
    enrichment_alpha: num('#p_alpha'),
  };
}
async function run() {
  if (!ST.files.length) { say('请先选择至少一个数据文件。', 'err'); return; }
  const query = $('#query').value.trim();
  if (!query) { say('请填写分析目标。', 'err'); return; }

  ST.busy = true;
  $('#runBtn').disabled = true;
  say('正在上传文件…', 'busy');
  try {
    const form = new FormData();
    ST.files.forEach((f) => form.append('files', f));
    const up = await fetch('/api/upload', { method: 'POST', body: form });
    if (!up.ok) throw new Error('上传失败（HTTP ' + up.status + '）');
    const upData = await up.json();
    ST.dir = upData.upload_dir;

    say('文件已上传，多智能体流水线开始运行…', 'busy');
    $('#runState').textContent = '分析进行中，请勿关闭页面…';
    startProgress();
    const an = await fetch('/api/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, input_dir: ST.dir, thresholds: collectThresholds() }),
    });
    if (!an.ok) {
      const err = await an.json().catch(() => ({}));
      throw new Error(err.detail || ('分析失败（HTTP ' + an.status + '）'));
    }
    ST.result = await an.json();
    stopProgress();
    render(ST.result);
    say('分析完成，项目号 ' + ST.result.project_id + '。', 'ok');
  } catch (e) {
    stopProgress();
    say('出错了：' + e.message, 'err');
  } finally {
    ST.busy = false;
    syncRun();
  }
}
$('#runBtn').addEventListener('click', run);
$('#heroRun').addEventListener('click', () => {
  document.getElementById('work').scrollIntoView({ behavior: 'smooth' });
  setTimeout(() => $('#files').click(), 400);
});
$('#newRun').addEventListener('click', () => {
  document.getElementById('work').scrollIntoView({ behavior: 'smooth' });
});

/* ---------------- tabs ---------------- */
$('#tabs').addEventListener('click', (e) => {
  const b = e.target.closest('.tab');
  if (!b) return;
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('on', t === b));
  document.querySelectorAll('.pane').forEach((p) => p.classList.toggle('on', p.id === 'p-' + b.dataset.p));
});

/* ---------------- render ---------------- */
function render(d) {
  $('#results').style.display = 'block';
  $('#heroRes').style.display = 'inline-flex';
  $('#resId').textContent = '项目 ' + d.project_id;
  $('#resMode').textContent = d.mode === 'llm' ? 'LLM 智能体' : '离线确定性策略';
  $('#resCalls').textContent = d.tool_calls + ' 次';
  $('#resTime').textContent = (d.elapsed_seconds || 0).toFixed(1) + ' s';
  $('#resStop').textContent = d.stopped_reason || '—';
  const pid = d.project_id;
  $('#dlHtml').href = '/api/report/' + pid + '?format=html';
  $('#dlPdf').href = '/api/report/' + pid + '?format=pdf';
  renderOverview(d);
  renderAI(d);
  renderCandidates(d);
  renderEnrichment(d);
  renderFigures(d, pid);
  renderEvidence(d);
  renderLimits(d);
  renderLog(d);
  loadHistory();
}

function renderOverview(d) {
  const c = d.counts || {};
  const ds = d.dataset || {};
  const groups = ds.groups || {};
  const v = d.validation || {};
  const th = d.thresholds || {};
  const issues = v.issues || [];
  const errs = issues.filter((i) => i.severity === 'error');
  const warns = issues.filter((i) => i.severity === 'warning');
  const spec = (k, val) => '<div class="spec"><b>' + (val === undefined || val === null ? 'NA' : val) +
    '</b><span>' + k + '</span></div>';
  const kvs = (pairs) => '<div class="kv" style="margin-top:16px">' + pairs.map(function (p) {
    return '<div><span>' + p[0] + '</span><b>' + esc(p[1] === undefined || p[1] === null ? 'NA' : p[1]) + '</b></div>';
  }).join('') + '</div>';

  let html = '<div class="specs">' +
    spec('事件总数', c.events) + spec('显著事件', c.significant) + spec('候选基因', c.candidates) +
    spec('富集条目', c.enrichment) + spec('图件', c.figures) + spec('样本', c.samples) +
    '</div>';

  const paras = (d.interpretation || '').split('\n\n').filter((p) => p.trim());
  if (paras.length) {
    html += '<div class="lead" style="margin-top:40px">' + esc(paras[0]) + '</div>';
    if (paras.length > 1) {
      html += '<div class="prose" style="margin-top:20px">' +
        paras.slice(1).map((p) => '<p>' + esc(p) + '</p>').join('') + '</div>';
    }
  }

  html += '<div class="label-up" style="margin-top:48px">数据概览</div>' + kvs([
    ['来源格式', ds.source_format], ['数据集', ds.name],
    ['样本分组', Object.keys(groups).length
      ? Object.keys(groups).map((g) => g + ' · ' + groups[g] + ' 个').join(' / ') : 'NA'],
    ['已注释基因', c.annotated_genes],
  ]);

  html += '<div class="label-up" style="margin-top:40px">事件类型分布</div>';
  const et = ds.event_types || {};
  html += Object.keys(et).length ? kvs(Object.keys(et).map((k) => [k, et[k] + ' 个']))
    : '<div class="empty" style="margin-top:16px">无事件类型统计。</div>';

  html += '<div class="label-up" style="margin-top:40px">质控与分析参数</div>' + kvs([
    ['校验结果', v.ok ? '通过' : '未通过'], ['错误', v.error_count], ['警告', v.warning_count],
    ['FDR 阈值', '< ' + th.fdr], ['|ΔPSI| 阈值', '> ' + th.delta_psi],
    ['最少支持读数', th.min_support_reads], ['最少有效样本', th.min_valid_samples],
    ['候选基因上限', th.top_candidates], ['富集显著性水平', th.enrichment_alpha],
  ]);

  if (errs.length || warns.length) {
    html += '<div class="label-up" style="margin-top:40px">质控提示</div><ul class="bullets" style="margin-top:16px">' +
      errs.map((i) => '<li><b>错误 · ' + esc(i.code) + '</b>：' + esc(i.message) + '</li>').join('') +
      warns.map((i) => '<li><b>警告 · ' + esc(i.code) + '</b>：' + esc(i.message) + '</li>').join('') +
      '</ul>';
  }
  $('#p-ov').innerHTML = html;
}

function renderAI(d) {
  const llm = d.llm || {};
  const box = $('#aiReport');
  if (!box) return;
  if (!llm.enabled) {
    box.innerHTML = '<div class="empty">本次运行未接入大模型。在上面的「模型配置」中填入 API Key 并保存，' +
      '即可获得 AI 目标理解、结果解读、候选基因注释、证据摘要、研究假设与自动审查；' +
      '不配置时结果与现在完全一致（不会报错、也不会少任何统计结果）。</div>';
    return;
  }
  const nar = llm.narrative || {};
  const hyp = llm.hypotheses || {};
  const cri = llm.critique || {};
  const notes = llm.gene_notes || {};
  const sums = llm.evidence_summaries || {};
  const bullets = (items) => '<ul class="bullets" style="margin-top:16px">' +
    items.map((i) => '<li>' + esc(i) + '</li>').join('') + '</ul>';
  const section = (title, body) => '<div class="label-up" style="margin-top:48px">' + title + '</div>' + body;

  let html = '<div class="ai-band"><i class="ai-dot"></i><div>' +
    '<div class="t">已接入大模型 · ' + esc(llm.model || '未命名模型') + '</div>' +
    '<div class="s">端点 ' + esc(llm.base_url || '—') + ' · 本次调用 ' + (llm.calls || 0) + ' 次 · ' +
    '输出语言 ' + (llm.language === 'zh' ? '中文' : '英文') + ' · 能力 ' +
    esc((llm.features || []).join('、') || '—') + '</div></div></div>';

  if (nar.source === 'llm') {
    let body = '';
    if (nar.lead) body += '<div class="ai-lead">' + esc(nar.lead) + '</div>';
    if ((nar.paragraphs || []).length) {
      body += '<div class="prose" style="margin-top:20px">' +
        nar.paragraphs.map((p) => '<p>' + esc(p) + '</p>').join('') + '</div>';
    }
    if ((nar.highlights || []).length) body += bullets(nar.highlights);
    html += section('AI 结论摘要', body);
  }

  const noteGenes = Object.keys(notes);
  const sumGenes = Object.keys(sums).filter((g) => !notes[g]);
  if (noteGenes.length || sumGenes.length) {
    const card = (g) => '<div class="ai-card"><div class="g">' + esc(g) + '</div>' +
      '<div class="n">' + esc(notes[g] || '—') + '</div>' +
      (sums[g] ? '<div class="ai-quote">证据摘要：' + esc(sums[g]) + '</div>' : '') + '</div>';
    html += section('候选基因 AI 注释 · ' + noteGenes.length + ' 个',
      '<div class="ai-cards">' + noteGenes.map(card).join('') + sumGenes.map(card).join('') + '</div>');
  }

  if (hyp.source === 'llm') {
    if ((hyp.hypotheses || []).length) html += section('研究假设（需实验验证）', bullets(hyp.hypotheses));
    if ((hyp.validations || []).length) html += section('建议验证实验', bullets(hyp.validations));
    if ((hyp.followups || []).length) html += section('后续分析建议', bullets(hyp.followups));
  }

  if (cri.source === 'llm') {
    html += section('自动审查（Critic）',
      '<div class="ai-block"><div class="h">模型自查</div>' +
      '<div class="b">' + esc(cri.verdict || '—') + '</div>' +
      ((cri.issues || []).length ? bullets(cri.issues)
        : '<div class="caption" style="margin-top:12px">未发现与统计结果不符的表述。</div>') +
      '</div>');
  }

  if (llm.errors && llm.errors.length) {
    html += section('模型调用告警',
      bullets(llm.errors.map((e) => (e.feature || '调用') + '：' + (e.error || ''))));
  }

  html += '<div class="ai-meta">统计结论由分析引擎计算；模型仅在其之上生成叙述、注释与假设。' +
    '机制性表述属于假设，需实验验证。HTML / PDF 报告的第 5.2、5.3、8、9 节包含同样内容。</div>';
  box.innerHTML = html;
}

function renderCandidates(d) {
  const rows = d.top_candidates || [];
  const notes = (d.llm && d.llm.gene_notes) || {};
  if (!rows.length) {
    $('#p-cand').innerHTML =
      '<div class="empty">没有事件通过当前显著性阈值。可在“高级参数”中放宽 FDR 或 |ΔPSI| 后重跑。</div>';
    return;
  }
  const maxAbs = Math.max(0.05, ...rows.map((r) => Math.abs(r.delta_PSI || 0)));
  const body = rows.map((r, i) => {
    const dp = r.delta_PSI;
    const w = (Math.abs(dp || 0) / maxAbs) * 50;
    const left = dp === null ? '50%' : (dp >= 0 ? '50%' : (50 - w).toFixed(1) + '%');
    const right = dp === null ? '50%' : (dp >= 0 ? (50 - w).toFixed(1) + '%' : '50%');
    const comps = [
      ['#0b4ea2', r.significance_component], ['#1c69d4', r.effect_component],
      ['#5aa0ee', r.biology_component], ['#a8caf6', r.literature_component],
    ];
    const total = comps.reduce((a, c) => a + (c[1] || 0), 0) || 1;
    return '<tr>' +
      '<td><span class="rank">' + (i + 1) + '</span></td>' +
      '<td><span class="gene">' + esc(r.gene_symbol || r.gene_id) + '</span> ' +
        '<span class="tag">' + esc(r.event_type) + '</span>' +
        '<div class="caption" style="margin-top:4px">' + esc(r.event_id) + '</div>' +
        (notes[r.gene_symbol || r.gene_id]
          ? '<div class="caption" style="margin-top:6px">AI：' + esc(notes[r.gene_symbol || r.gene_id]) + '</div>'
          : '') + '</td>' +
      '<td><div class="dpsi"><div class="bar' + (dp === null ? ' zero' : '') + '">' +
        '<i style="left:' + left + ';right:' + right + '"></i></div>' +
        '<span class="v">' + (dp === null ? 'NA' : (dp > 0 ? '+' : '') + nf(dp)) + '</span></div></td>' +
      '<td class="num mono">' + sci(r.FDR) + '</td>' +
      '<td class="num mono"><b>' + nf(r.score) + '</b></td>' +
      '<td><div class="stack">' + comps.map((c) =>
        '<i style="background:' + c[0] + ';width:' + ((c[1] || 0) / total * 100).toFixed(1) + '%"></i>').join('') +
        '</div></td>' +
      '</tr>';
  }).join('');
  $('#p-cand').innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px;flex-wrap:wrap">' +
      '<div><div class="label-up">共 ' + rows.length + ' 个候选事件 · 按综合评分降序</div>' +
      '<div class="caption" style="margin-top:6px">综合评分 = 0.4 显著性 + 0.3 效应量 + 0.2 生物学 + 0.1 文献</div></div>' +
      '<div class="legend">' +
        '<span><i style="background:#0b4ea2"></i>显著性</span>' +
        '<span><i style="background:#1c69d4"></i>效应量</span>' +
        '<span><i style="background:#5aa0ee"></i>生物学</span>' +
        '<span><i style="background:#a8caf6"></i>文献</span>' +
      '</div>' +
    '</div>' +
    '<table style="margin-top:20px"><thead><tr>' +
      '<th style="width:56px">排名</th><th>基因 / 事件</th><th>ΔPSI</th>' +
      '<th class="num">FDR</th><th class="num">评分</th><th style="width:220px">评分构成</th>' +
    '</tr></thead><tbody>' + body + '</tbody></table>';
}

function renderEnrichment(d) {
  const items = d.enrichment || [];
  if (!items.length) {
    $('#p-enr').innerHTML =
      '<div class="empty">未执行富集分析：通常是因为没有提供 gene_annotation.tsv，或没有基因通过显著性阈值。</div>';
    return;
  }
  $('#p-enr').innerHTML =
    '<div class="label-up">超几何过表征检验 · ' + items.length + ' 条显著条目</div>' +
    '<div class="enr" style="margin-top:20px">' +
    items.map((it) =>
      '<div class="cell">' +
        '<div class="ont">' + esc(it.ontology) + '</div>' +
        '<div class="term">' + esc(it.term) + '</div>' +
        '<div class="nums">' +
          '<div><b>' + nf(it.fold_enrichment, 2) + '×</b><span>富集倍数</span></div>' +
          '<div><b>' + it.gene_count + '</b><span>命中基因</span></div>' +
          '<div><b>' + sci(it.fdr) + '</b><span>FDR</span></div>' +
        '</div>' +
        (it.genes && it.genes.length
          ? '<div class="genes">' + it.genes.slice(0, 12).map((g) => '<em>' + esc(g) + '</em>').join('') +
            (it.genes.length > 12 ? '<em>+' + (it.genes.length - 12) + '</em>' : '') + '</div>'
          : '') +
      '</div>').join('') +
    '</div>';
}

function renderFigures(d, pid) {
  const figs = d.figure_details && d.figure_details.length
    ? d.figure_details
    : (d.figures || []).map((n) => ({ name: n, title: n, caption: '' }));
  if (!figs.length) { $('#p-fig').innerHTML = '<div class="empty">本次运行没有生成图件。</div>'; return; }
  $('#p-fig').innerHTML =
    '<div class="label-up">点击任意图件可放大查看 · 每张同时提供 PNG 与 SVG</div>' +
    '<div class="figs" style="margin-top:20px">' +
    figs.map((f) =>
      '<div class="fig"><div class="plate" data-n="' + esc(f.name) + '" data-t="' + esc(f.title) +
      '" data-c="' + esc(f.caption) + '">' +
      '<img loading="lazy" src="/api/figure/' + pid + '/' + encodeURIComponent(f.name) + '" alt="' + esc(f.title) + '">' +
      '</div><div class="cap"><b>' + esc(f.title) + '</b><span>' + esc(f.caption) + '</span></div></div>').join('') +
    '</div>';
  document.querySelectorAll('.fig .plate').forEach((el) => el.addEventListener('click', () => {
    $('#lbImg').src = '/api/figure/' + pid + '/' + encodeURIComponent(el.dataset.n);
    $('#lbT').textContent = el.dataset.t;
    $('#lbC').textContent = el.dataset.c;
    $('#lb').classList.add('on');
  }));
}
$('#lbX').addEventListener('click', () => $('#lb').classList.remove('on'));
$('#lb').addEventListener('click', (e) => { if (e.target.id === 'lb') $('#lb').classList.remove('on'); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('#lb').classList.remove('on'); });

function renderEvidence(d) {
  const ev = d.evidence || {};
  const genes = Object.keys(ev);
  if (!genes.length) {
    $('#p-ev').innerHTML =
      '<div class="empty">本次运行没有检索到候选基因的文献证据（知识库无匹配记录）。</div>';
    return;
  }
  $('#p-ev').innerHTML =
    '<div class="label-up">证据覆盖 ' + genes.length + ' 个基因 · 每条均标注来源</div>' +
    '<div class="evid" style="margin-top:20px">' +
    genes.map((g) =>
      '<div class="row"><div class="g"><b>' + esc(g) + '</b><span>' + ev[g].length + ' 条记录</span></div>' +
      '<div class="t">' + ev[g].slice(0, 3).map((e) =>
        '<p>' + esc(e.text) + '</p><div class="src">来源：' + esc(e.source) +
        (e.pmid ? ' · PMID ' + esc(e.pmid) : '') + '</div>').join('<div style="height:14px"></div>') +
      '</div></div>').join('') +
    '</div>';
}

function renderLimits(d) {
  const lim = d.limitations || [];
  const ref = d.references || [];
  $('#p-lim').innerHTML =
    '<div class="label-up">局限性</div>' +
    (lim.length
      ? '<ul class="bullets" style="margin-top:16px">' + lim.map((l) => '<li>' + esc(l) + '</li>').join('') + '</ul>'
      : '<div class="empty" style="margin-top:16px">本次运行没有记录局限性。</div>') +
    '<div class="label-up" style="margin-top:48px">参考文献</div>' +
    (ref.length
      ? '<ul class="plain" style="margin-top:16px">' +
        ref.map((r, i) => '<li><b>' + (i + 1) + '.</b> ' + esc(r) + '</li>').join('') + '</ul>'
      : '<div class="empty" style="margin-top:16px">未使用外部参考文献。</div>');
}

function renderLog(d) {
  const log = d.workflow || [];
  if (!log.length) { $('#p-log').innerHTML = '<div class="empty">没有工作流日志记录。</div>'; return; }
  $('#p-log').innerHTML =
    '<div class="label-up">智能体工作流 · ' + log.length + ' 条记录</div>' +
    '<table class="log" style="margin-top:16px"><thead><tr>' +
    '<th>智能体</th><th>动作</th><th>状态</th><th>详情</th></tr></thead><tbody>' +
    log.map((l) =>
      '<tr><td class="a">' + esc(l.agent) + '</td><td>' + esc(l.action) + '</td>' +
      '<td><span class="st ' + (l.status === 'ok' ? 'ok' : (l.status === 'warning' ? 'warn' : 'err')) + '">' +
      esc(l.status) + '</span></td>' +
      '<td class="mono" style="color:var(--muted)">' + esc(l.detail) + '</td></tr>').join('') +
    '</tbody></table>';
}

/* ---------------- history ---------------- */
async function loadHistory() {
  try {
    const r = await fetch('/api/projects');
    const d = await r.json();
    const list = d.projects || [];
    if (!list.length) { $('#histList').innerHTML = '<div class="caption">还没有历史项目。</div>'; return; }
    $('#histList').innerHTML = list.map((p) =>
      '<div class="hist" data-id="' + esc(p.project_id) + '"><b>' + esc(p.project_id) + '</b>' +
      '<span>' + esc(p.source_format || '') + ' · ' + esc((p.created_at || '').slice(0, 19).replace('T', ' ')) + '</span>' +
      '<div class="q">' + esc(p.query || '') + '</div></div>').join('');
    $('#histList').querySelectorAll('.hist').forEach((el) => el.addEventListener('click', async () => {
      const id = el.dataset.id;
      try {
        const r2 = await fetch('/api/status/' + encodeURIComponent(id));
        if (!r2.ok) throw new Error('HTTP ' + r2.status);
        const st = await r2.json();
        $('#drawer').classList.remove('on');
        showArchived(id, st);
      } catch (e) { say('无法载入项目 ' + id + '：' + e.message, 'err'); }
    }));
  } catch (e) {
    $('#histList').innerHTML = '<div class="caption">历史项目加载失败。</div>';
  }
}
function showArchived(id, st) {
  const p = st.project || {};
  const cands = st.candidates || [];
  const enr = st.enrichment || [];
  const arts = st.artifacts || [];
  const logs = st.logs || [];
  const has = (kind) => arts.some((a) => a.kind === 'report:' + kind);
  const kvs = (pairs) => '<div class="kv">' + pairs.map(function (x) {
    return '<div><span>' + x[0] + '</span><b>' + esc(x[1] === undefined || x[1] === null ? 'NA' : x[1]) + '</b></div>';
  }).join('') + '</div>';

  $('#results').style.display = 'block';
  $('#heroRes').style.display = 'inline-flex';
  $('#resId').textContent = '项目 ' + id + ' · 历史存档';
  $('#resMode').textContent = '—';
  $('#resCalls').textContent = '—';
  $('#resTime').textContent = '—';
  $('#resStop').textContent = '—';
  $('#dlHtml').href = has('html') ? '/api/report/' + id + '?format=html' : '#';
  $('#dlPdf').href = has('pdf') ? '/api/report/' + id + '?format=pdf' : '#';

  $('#p-ov').innerHTML = kvs([
    ['数据集', p.name], ['来源格式', p.source_format], ['分析目标', p.query],
    ['剪接事件', st.events], ['候选基因', cands.length], ['富集条目', enr.length],
  ]);
  $('#p-cand').innerHTML = cands.length
    ? '<table><thead><tr><th>基因</th><th>事件类型</th><th class="num">ΔPSI</th>' +
      '<th class="num">FDR</th><th class="num">评分</th></tr></thead><tbody>' +
      cands.map((c) => '<tr><td><span class="gene">' + esc(c.gene_symbol || c.gene_id) + '</span></td>' +
        '<td><span class="tag">' + esc(c.event_type) + '</span></td>' +
        '<td class="num mono">' + nf(c.delta_psi) + '</td>' +
        '<td class="num mono">' + sci(c.fdr) + '</td>' +
        '<td class="num mono"><b>' + nf(c.score) + '</b></td></tr>').join('') + '</tbody></table>'
    : '<div class="empty">该存档没有候选基因记录。</div>';
  $('#p-enr').innerHTML = enr.length
    ? '<div class="enr">' + enr.map((it) =>
        '<div class="cell"><div class="ont">' + esc(it.ontology || '') + '</div>' +
        '<div class="term">' + esc(it.term) + '</div>' +
        '<div class="nums"><div><b>' + nf(it.fold_enrichment, 2) + '×</b><span>富集倍数</span></div>' +
        '<div><b>' + (it.gene_count === undefined ? 'NA' : it.gene_count) + '</b><span>命中基因</span></div>' +
        '<div><b>' + sci(it.fdr) + '</b><span>FDR</span></div></div></div>').join('') + '</div>'
    : '<div class="empty">该存档没有富集记录。</div>';
  $('#aiReport').innerHTML = '<div class="empty">历史存档不保留 AI 解读明细，请下载下方报告查看（第 5.2、8、9 节）。</div>';
  $('#p-fig').innerHTML = '<div class="empty">存档图件请在项目目录 figures/ 查看，或直接下载下方报告。</div>';
  $('#p-ev').innerHTML = '<div class="empty">历史存档不保留文献证据明细，请查看报告文件。</div>';
  $('#p-lim').innerHTML = '<div class="empty">历史存档不保留局限性明细，请查看报告文件。</div>';
  $('#p-log').innerHTML = logs.length
    ? '<table class="log"><thead><tr><th>智能体</th><th>动作</th><th>状态</th><th>详情</th></tr></thead><tbody>' +
      logs.map((l) => '<tr><td class="a">' + esc(l.agent) + '</td><td>' + esc(l.action) + '</td>' +
        '<td><span class="st ' + (l.status === 'ok' ? 'ok' : 'warn') + '">' + esc(l.status) + '</span></td>' +
        '<td class="mono" style="color:var(--muted)">' + esc(l.detail) + '</td></tr>').join('') + '</tbody></table>'
    : '<div class="empty">该存档没有日志记录。</div>';

  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('on', t.dataset.p === 'ov'));
  document.querySelectorAll('.pane').forEach((pa) => pa.classList.toggle('on', pa.id === 'p-ov'));
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}
$('#histBtn').addEventListener('click', () => { $('#drawer').classList.add('on'); loadHistory(); });
$('#drawerClose').addEventListener('click', () => $('#drawer').classList.remove('on'));

/* ---------------- boot ---------------- */
health();
syncRun();
loadHistory();
</script>
</body>
</html>
"""


def render(title: str = "SpliceGAIP v0.1.0") -> HTMLResponse:
    """Return the web UI page."""
    return HTMLResponse(_HTML.replace("__TITLE__", title))
