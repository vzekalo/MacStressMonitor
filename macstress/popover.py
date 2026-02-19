"""Popover HTML — compact metrics views for the status bar popover."""

POPOVER_HTML = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MacStressMonitor Popover</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#1a1a2e;--bg2:#16162a;--card:#12121a;--border:rgba(255,255,255,.08);
  --muted:#555;--text:#e0e0e0;--accent:#48dbfb;
  --red:#ff6b6b;--cyan:#48dbfb;--purple:#a29bfe;--orange:#ffa502;--green:#2ed573}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text',Helvetica,sans-serif;
  background:var(--bg);color:var(--text);width:320px;overflow-x:hidden;-webkit-font-smoothing:antialiased}

/* ── Header Bar ── */
.header{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;
  background:rgba(0,0,0,.35);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);position:relative;z-index:100}
.header-btn{width:28px;height:28px;border-radius:6px;border:none;background:rgba(255,255,255,.06);
  color:#888;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:all .2s}
.header-btn:hover{background:rgba(255,255,255,.12);color:#fff}
.header-title{font-size:11px;font-weight:600;color:#666;letter-spacing:.5px}

/* ── Settings Dropdown ── */
.settings-overlay{position:absolute;top:40px;right:6px;width:200px;background:rgba(20,20,40,.96);
  border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:4px;z-index:200;
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  box-shadow:0 8px 32px rgba(0,0,0,.5);opacity:0;transform:translateY(-8px);
  pointer-events:none;transition:all .2s ease}
.settings-overlay.open{opacity:1;transform:translateY(0);pointer-events:auto}
.settings-item{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:7px;
  font-size:12px;color:#ccc;cursor:pointer;transition:background .15s}
.settings-item:hover{background:rgba(255,255,255,.08)}
.settings-item .si-icon{width:20px;text-align:center;font-size:13px}
.settings-sep{height:1px;background:var(--border);margin:3px 6px}
.settings-item.danger{color:var(--red)}
.settings-item.danger:hover{background:rgba(255,107,107,.1)}

/* ── Tabs ── */
.tabs{display:flex;border-bottom:1px solid var(--border);background:rgba(0,0,0,.15)}
.tab{flex:1;padding:9px 0;text-align:center;font-size:10px;font-weight:600;color:var(--muted);
  cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;letter-spacing:.6px;
  text-transform:uppercase}
.tab:hover{color:#999;background:rgba(255,255,255,.02)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab.cpu.active{color:var(--red);border-bottom-color:var(--red)}
.tab.ram.active{color:var(--cyan);border-bottom-color:var(--cyan)}
.tab.disk.active{color:var(--purple);border-bottom-color:var(--purple)}
.tab.pwr.active{color:var(--orange);border-bottom-color:var(--orange)}

/* ── Panels ── */
.panel{display:none;padding:12px 14px;animation:fadeIn .2s ease}
.panel.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}

.section{margin-bottom:10px}
.section-title{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:5px}
.metric-row{display:flex;justify-content:space-between;padding:4px 0;font-size:12px}
.metric-label{color:#777}
.metric-value{color:#ddd;font-weight:600;font-variant-numeric:tabular-nums}
.gauge-row{display:flex;gap:10px;margin-bottom:8px}
.gauge{flex:1;text-align:center}
.gauge-val{font-size:28px;font-weight:700;line-height:1.2}
.gauge-sub{font-size:18px;font-weight:600;line-height:1.2}
.gauge-label{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-top:2px}

.bar-bg{height:4px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:2px;transition:width .5s ease}
.sparkline{width:100%;height:50px;margin:4px 0;border-radius:6px}

/* ── Process Rows ── */
.proc-row{display:flex;align-items:center;padding:3px 0;font-size:11px;
  border-bottom:1px solid rgba(255,255,255,.03);position:relative}
.proc-row:last-child{border:none}
.proc-name{color:#999;max-width:175px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  flex:1;z-index:1}
.proc-val{color:#ddd;font-weight:500;font-variant-numeric:tabular-nums;z-index:1;min-width:55px;text-align:right}
.proc-bar{position:absolute;left:0;top:0;bottom:0;border-radius:3px;opacity:.08;z-index:0}

/* ── SMART Badge ── */
.smart-badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:4px;
  font-size:11px;font-weight:600}
.smart-ok{background:rgba(46,213,115,.1);color:var(--green)}
.smart-warn{background:rgba(255,107,107,.1);color:var(--red)}

/* ── Auth Button ── */
.auth-prompt{text-align:center;padding:16px 12px}
.auth-prompt p{font-size:11px;color:var(--muted);margin-bottom:10px}
.auth-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;
  border:1px solid rgba(255,165,2,.3);background:rgba(255,165,2,.08);color:var(--orange);
  font-size:12px;font-weight:600;cursor:pointer;transition:all .2s}
.auth-btn:hover{background:rgba(255,165,2,.16);border-color:rgba(255,165,2,.5)}
.auth-btn:active{transform:scale(.97)}

/* ── Confirm Modal ── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(6px);
  -webkit-backdrop-filter:blur(6px);z-index:500;display:none;align-items:center;
  justify-content:center;animation:fadeIn .15s ease}
.modal-overlay.open{display:flex}
.modal-box{background:rgba(25,25,50,.95);border:1px solid rgba(255,255,255,.1);
  border-radius:12px;padding:20px;width:260px;text-align:center;
  box-shadow:0 12px 40px rgba(0,0,0,.6)}
.modal-box p{font-size:13px;color:#ddd;margin-bottom:6px}
.modal-box .modal-sub{font-size:11px;color:var(--muted);margin-bottom:14px}
.modal-btns{display:flex;gap:8px}
.modal-btns button{flex:1;padding:8px;border-radius:8px;border:none;font-size:12px;
  font-weight:600;cursor:pointer;transition:all .15s}
.modal-cancel{background:rgba(255,255,255,.08);color:#999}
.modal-cancel:hover{background:rgba(255,255,255,.14)}
.modal-confirm{background:rgba(255,107,107,.15);color:var(--red)}
.modal-confirm:hover{background:rgba(255,107,107,.25)}

/* ── Toast ── */
.toast{position:fixed;bottom:40px;left:50%;transform:translateX(-50%);padding:8px 16px;
  background:rgba(30,30,60,.95);border:1px solid rgba(255,255,255,.1);border-radius:8px;
  font-size:11px;color:#ddd;z-index:600;opacity:0;transition:opacity .3s;pointer-events:none}
.toast.show{opacity:1}

/* ── Footer ── */
.uptime{font-size:10px;color:var(--muted);text-align:center;padding:6px 0;
  border-top:1px solid var(--border)}
</style></head><body>

<!-- Header Bar -->
<div class="header">
  <button class="header-btn" onclick="doAction('dashboard')" title="Open Dashboard">📊</button>
  <span class="header-title">MacStressMonitor</span>
  <button class="header-btn" id="gearBtn" onclick="toggleSettings()" title="Settings">⚙️</button>
</div>

<!-- Settings Dropdown -->
<div class="settings-overlay" id="settingsMenu">
  <div class="settings-item" onclick="doAction('start')"><span class="si-icon">▶️</span>Start Stress Tests</div>
  <div class="settings-item" onclick="doAction('stop')"><span class="si-icon">⏹</span>Stop Stress Tests</div>
  <div class="settings-sep"></div>
  <div class="settings-item" onclick="doAction('update')"><span class="si-icon">🔄</span>Check for Updates</div>
  <div class="settings-item" onclick="doAction('dock')"><span class="si-icon">📌</span>Pin to Dock</div>
  <div class="settings-item" id="launchd-item" onclick="doAction('launchd')"><span class="si-icon">🚀</span>Start at Login <span id="launchd-badge" style="margin-left:auto;font-size:10px;opacity:.6"></span></div>
  <div class="settings-sep"></div>
  <div class="settings-item danger" onclick="doAction('quit')"><span class="si-icon">✕</span>Close App</div>
</div>

<!-- Tabs -->
<div class="tabs">
  <div class="tab cpu active" data-tab="cpu" onclick="switchTab('cpu')">CPU</div>
  <div class="tab ram" data-tab="ram" onclick="switchTab('ram')">RAM</div>
  <div class="tab disk" data-tab="disk" onclick="switchTab('disk')">DISK</div>
  <div class="tab pwr" data-tab="pwr" onclick="switchTab('pwr')">POWER</div>
</div>

<!-- CPU Panel -->
<div class="panel active" id="panel-cpu">
  <div class="section">
    <div class="gauge-row">
      <div class="gauge"><div class="gauge-val" id="pop-cpu-pct" style="color:var(--red)">—</div><div class="gauge-label">Usage</div></div>
      <div class="gauge"><div class="gauge-val" id="pop-cpu-temp" style="color:#ff4757">—</div><div class="gauge-label">Temp</div></div>
      <div class="gauge"><div class="gauge-sub" id="pop-load-avg" style="color:var(--orange)">—</div><div class="gauge-label">Load Avg</div></div>
    </div>
    <canvas class="sparkline" id="pop-cpu-spark"></canvas>
  </div>
  <div class="section">
    <div class="section-title">Breakdown</div>
    <div class="metric-row"><span class="metric-label">User</span><span class="metric-value" id="pop-cpu-user">—</span></div>
    <div class="metric-row"><span class="metric-label">System</span><span class="metric-value" id="pop-cpu-sys">—</span></div>
    <div class="metric-row"><span class="metric-label">Idle</span><span class="metric-value" id="pop-cpu-idle">—</span></div>
    <div class="metric-row"><span class="metric-label">Frequency</span><span class="metric-value" id="pop-cpu-freq">—</span></div>
  </div>
  <div class="section">
    <div class="section-title">Top Processes</div>
    <div id="pop-cpu-procs"></div>
  </div>
</div>

<!-- RAM Panel -->
<div class="panel" id="panel-ram">
  <div class="section">
    <div class="gauge-row">
      <div class="gauge">
        <div class="gauge-val" id="pop-ram-combo" style="color:var(--cyan)">—</div>
        <div class="gauge-label">Used / Total</div>
      </div>
      <div class="gauge">
        <div class="gauge-val" id="pop-ram-pct" style="color:var(--cyan);font-size:22px">—</div>
        <div class="gauge-label">Usage</div>
      </div>
    </div>
    <canvas class="sparkline" id="pop-ram-spark"></canvas>
  </div>
  <div class="section">
    <div class="section-title">Details</div>
    <div class="metric-row"><span class="metric-label">Swap Used</span><span class="metric-value" id="pop-ram-swap">—</span></div>
    <div class="metric-row"><span class="metric-label">Pressure</span><span class="metric-value" id="pop-ram-pressure">Normal</span></div>
  </div>
  <div class="section">
    <div class="section-title">Top Processes</div>
    <div id="pop-ram-procs"></div>
  </div>
</div>

<!-- Disk Panel -->
<div class="panel" id="panel-disk">
  <div class="section">
    <div class="gauge-row">
      <div class="gauge"><div class="gauge-sub" id="pop-disk-read" style="color:var(--cyan)">—</div><div class="gauge-label">Read MB/s</div></div>
      <div class="gauge"><div class="gauge-sub" id="pop-disk-write" style="color:var(--red)">—</div><div class="gauge-label">Write MB/s</div></div>
    </div>
    <canvas class="sparkline" id="pop-disk-spark"></canvas>
  </div>
  <div class="section">
    <div class="section-title">Storage</div>
    <div class="metric-row"><span class="metric-label">Used</span><span class="metric-value" id="pop-disk-used">—</span></div>
    <div class="metric-row"><span class="metric-label">Free</span><span class="metric-value" id="pop-disk-free">—</span></div>
    <div class="metric-row"><span class="metric-label">Total</span><span class="metric-value" id="pop-disk-total">—</span></div>
    <div class="bar-bg"><div class="bar-fill" id="pop-disk-bar" style="width:0;background:linear-gradient(90deg,var(--purple),#6c5ce7)"></div></div>
  </div>
  <div class="section" id="smart-section" style="display:none">
    <div class="section-title">Drive Health</div>
    <div class="metric-row"><span class="metric-label">SMART</span><span class="metric-value" id="pop-smart-status">—</span></div>
    <div class="metric-row"><span class="metric-label">Model</span><span class="metric-value" id="pop-smart-model" style="font-size:10px">—</span></div>
    <div class="metric-row"><span class="metric-label">TRIM</span><span class="metric-value" id="pop-smart-trim">—</span></div>
  </div>
</div>

<!-- Power Panel -->
<div class="panel" id="panel-pwr">
  <div class="section" id="pwr-data">
    <div class="gauge-row">
      <div class="gauge"><div class="gauge-val" id="pop-pwr-cpu" style="color:var(--orange)">—</div><div class="gauge-label">CPU W</div></div>
      <div class="gauge"><div class="gauge-val" id="pop-pwr-gpu" style="color:#f0932b">—</div><div class="gauge-label">GPU W</div></div>
      <div class="gauge"><div class="gauge-val" id="pop-pwr-total" style="color:var(--orange)">—</div><div class="gauge-label">Total W</div></div>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Details</div>
    <div class="metric-row"><span class="metric-label">Fan</span><span class="metric-value" id="pop-pwr-fan">—</span></div>
    <div class="metric-row"><span class="metric-label">Battery</span><span class="metric-value" id="pop-pwr-battery">—</span></div>
  </div>
  <div class="auth-prompt" id="pwr-auth" style="display:none">
    <p>🔒 Power metrics require admin privileges</p>
    <button class="auth-btn" onclick="requestSudo()">🔑 Enable Power Monitoring</button>
  </div>
</div>

<div class="uptime" id="pop-uptime">—</div>

<!-- Confirm Modal -->
<div class="modal-overlay" id="confirmModal">
  <div class="modal-box">
    <p id="confirmMsg">Are you sure?</p>
    <div class="modal-sub" id="confirmSub"></div>
    <div class="modal-btns">
      <button class="modal-cancel" onclick="closeModal()">Cancel</button>
      <button class="modal-confirm" id="confirmBtn" onclick="confirmAction()">Confirm</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
const $=id=>document.getElementById(id);
let cpuHist=[],ramHist=[],diskHist=[];
const MAX_H=60;
let settingsOpen=false;
let noPowerCount=0;

function _isNative(){return !!window.__MACSTRESS_NATIVE__;}

function switchTab(name){
  document.querySelectorAll('.tab').forEach(t=>{t.classList.toggle('active',t.dataset.tab===name)});
  document.querySelectorAll('.panel').forEach(p=>{p.classList.toggle('active',p.id==='panel-'+name)});
}

function toggleSettings(){
  settingsOpen=!settingsOpen;
  $('settingsMenu').classList.toggle('open',settingsOpen);
  if(settingsOpen){
    fetch('/api/launchd_status').then(r=>r.json()).then(d=>{
      let b=$('launchd-badge');if(b)b.textContent=d.installed?'ON':'OFF';
    }).catch(()=>{});
  }
}

// Close settings on click outside
document.addEventListener('click',e=>{
  if(settingsOpen && !e.target.closest('#settingsMenu') && !e.target.closest('#gearBtn')){
    settingsOpen=false;
    $('settingsMenu').classList.remove('open');
  }
});

function doAction(action){
  settingsOpen=false;
  $('settingsMenu').classList.remove('open');
  switch(action){
    case 'dashboard':
      fetch('/api/open_dashboard',{method:'POST'});
      window.open('/','_blank');
      break;
    case 'start':
      fetch('/api/toggle_stress?action=start',{method:'POST'});
      showToast('⚡ Stress tests starting...');
      break;
    case 'stop':
      fetch('/api/toggle_stress?action=stop',{method:'POST'});
      showToast('⏹ Stress tests stopping...');
      break;
    case 'update':
      fetch('/api/check_update').then(r=>r.json()).then(d=>{
        if(d.has_update) window.open('/','_blank');
        else showToast('✓ You are on the latest version');
      }).catch(()=>showToast('⚠ Could not check for updates'));
      break;
    case 'dock':
      fetch('/api/install_dock',{method:'POST'}).then(r=>r.json()).then(d=>{
        showToast(d.ok?'✓ App pinned to Dock!':'⚠ Error: '+(d.error||'unknown'));
      }).catch(()=>showToast('⚠ Failed to install'));
      break;
    case 'quit':
      if(_isNative()){
        // Native popover: fire-and-forget (popover will dismiss, can't show modal)
        fetch('/api/quit_app',{method:'POST'}).catch(()=>{});
      } else {
        showConfirm('Close MacStressMonitor?','This will stop all stress tests.',()=>{
          fetch('/api/quit_app',{method:'POST'}).catch(()=>{});
        });
      }
      break;
    case 'launchd':
      fetch('/api/toggle_launchd',{method:'POST'}).then(r=>r.json()).then(d=>{
        let badge=$('launchd-badge');
        if(badge)badge.textContent=d.enabled?'ON':'OFF';
        showToast(d.enabled?'✅ Start at Login enabled':'❌ Start at Login disabled');
      }).catch(()=>showToast('⚠ Failed to toggle'));
      break;
  }
}

function requestSudo(){
  fetch('/api/request_sudo',{method:'POST'}).then(()=>{
    let btn=$('pwr-auth');
    if(btn)btn.innerHTML='<p style="color:var(--orange)">⏳ Waiting for password dialog...</p>';
  }).catch(()=>showToast('⚠ Failed to request sudo'));
}

let _confirmCb=null;
function showConfirm(msg,sub,cb){
  $('confirmMsg').textContent=msg;
  $('confirmSub').textContent=sub||'';
  _confirmCb=cb;
  $('confirmModal').classList.add('open');
}
function closeModal(){$('confirmModal').classList.remove('open');_confirmCb=null;}
function confirmAction(){closeModal();if(_confirmCb)_confirmCb();}
function showToast(msg){
  let t=$('toast');t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2500);
}

function sparkline(canvasId,data,color,maxVal){
  let c=$(canvasId);if(!c)return;
  let x=c.getContext('2d'),W=c.width=c.offsetWidth*2,H=c.height=c.offsetHeight*2;
  x.clearRect(0,0,W,H);
  if(data.length<2)return;
  let g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,color+'30');g.addColorStop(1,color+'05');
  x.beginPath();let s=W/(MAX_H-1);
  for(let i=0;i<data.length;i++){let px=i*s,py=H-(data[i]/maxVal)*H;i===0?x.moveTo(px,py):x.lineTo(px,py);}
  x.strokeStyle=color;x.lineWidth=2;x.stroke();
  x.lineTo((data.length-1)*s,H);x.lineTo(0,H);x.closePath();x.fillStyle=g;x.fill();
}

function fmtUptime(sec){
  let d=Math.floor(sec/86400),h=Math.floor((sec%86400)/3600),m=Math.floor((sec%3600)/60);
  let parts=[];if(d)parts.push(d+'d');if(h)parts.push(h+'h');parts.push(m+'m');
  return 'Uptime: '+parts.join(' ');
}

function fv(v,u){return v!=null?v.toFixed(1)+u:'—';}

function procHtml(procs,valKey,valSuffix,color,maxVal){
  if(!procs||!procs.length) return '<div style="color:#444;font-size:11px">No data</div>';
  let mx=maxVal||Math.max(...procs.map(p=>p[valKey]),1);
  return procs.map(p=>{
    let v=p[valKey], pct=Math.min(v/mx*100,100);
    return '<div class="proc-row"><div class="proc-bar" style="width:'+pct.toFixed(0)+'%;background:'+color+'"></div>'+
      '<span class="proc-name">'+p.name+'</span><span class="proc-val" style="color:'+color+'">'+v+valSuffix+'</span></div>';
  }).join('');
}

function update(){
  fetch('/api/status').then(r=>r.json()).then(d=>{
    let m=d.metrics||{};
    // CPU
    $('pop-cpu-pct').textContent=fv(m.cpu_usage,'%');
    $('pop-cpu-temp').textContent=m.cpu_temp!=null?Math.round(m.cpu_temp)+'°':'—';
    $('pop-cpu-freq').textContent=m.cpu_freq_ghz!=null?m.cpu_freq_ghz.toFixed(2)+' GHz':'—';
    cpuHist.push(m.cpu_usage||0);if(cpuHist.length>MAX_H)cpuHist.shift();
    sparkline('pop-cpu-spark',cpuHist,'#ff6b6b',100);

    // RAM — used/total combo
    let usedGB=m.mem_used_gb!=null?m.mem_used_gb.toFixed(1):'?';
    let totalGB=m.mem_total_gb||'?';
    $('pop-ram-combo').textContent=usedGB+' / '+totalGB;
    $('pop-ram-pct').textContent=fv(m.mem_used_pct,'%');
    $('pop-ram-swap').textContent=fv(m.swap_used_gb,' GB');
    // Memory pressure estimate
    let pct=m.mem_used_pct||0;
    let pressure=pct>90?'Critical':pct>75?'High':pct>50?'Moderate':'Normal';
    let pColor=pct>90?'var(--red)':pct>75?'var(--orange)':pct>50?'#ccc':'var(--green)';
    $('pop-ram-pressure').textContent=pressure;
    $('pop-ram-pressure').style.color=pColor;
    ramHist.push(pct);if(ramHist.length>MAX_H)ramHist.shift();
    sparkline('pop-ram-spark',ramHist,'#48dbfb',100);

    // Disk
    $('pop-disk-read').textContent=fv(m.disk_read_mb,'');
    $('pop-disk-write').textContent=fv(m.disk_write_mb,'');
    diskHist.push((m.disk_read_mb||0)+(m.disk_write_mb||0));if(diskHist.length>MAX_H)diskHist.shift();
    sparkline('pop-disk-spark',diskHist,'#a29bfe',Math.max(...diskHist,0.1));

    // Power
    let hasPower=m.cpu_power_w!=null||m.gpu_power_w!=null||m.total_power_w!=null;
    $('pop-pwr-cpu').textContent=fv(m.cpu_power_w,'');
    $('pop-pwr-gpu').textContent=fv(m.gpu_power_w,'');
    $('pop-pwr-total').textContent=fv(m.total_power_w,'');
    $('pop-pwr-fan').textContent=m.fan_rpm!=null?m.fan_rpm+' RPM':'—';
    // Show/hide auth prompt
    if(!hasPower){noPowerCount++;} else {noPowerCount=0;}
    if(noPowerCount>=3){
      $('pwr-auth').style.display='block';
    } else if(hasPower){
      $('pwr-auth').style.display='none';
    }
  }).catch(()=>{});

  // Details endpoint
  fetch('/api/details').then(r=>r.json()).then(d=>{
    // CPU breakdown
    $('pop-cpu-user').textContent=fv(d.cpu_user_pct,'%');
    $('pop-cpu-sys').textContent=fv(d.cpu_sys_pct,'%');
    $('pop-cpu-idle').textContent=fv(d.cpu_idle_pct,'%');
    let la=d.load_avg||[0,0,0];
    $('pop-load-avg').textContent=la.map(v=>v.toFixed(1)).join(' · ');

    // Top processes with bars
    $('pop-cpu-procs').innerHTML=procHtml(d.top_cpu,'cpu_pct','%','var(--red)',100);
    $('pop-ram-procs').innerHTML=procHtml(d.top_mem,'mem_mb',' MB','var(--cyan)');

    // Disk storage
    let free=d.disk_free_gb||0, total=d.disk_total_gb||0, used=total-free;
    $('pop-disk-free').textContent=free+' GB';
    $('pop-disk-total').textContent=total+' GB';
    $('pop-disk-used').textContent=(used>0?used:0)+' GB';
    if(total>0){
      $('pop-disk-bar').style.width=(used/total*100).toFixed(0)+'%';
    }

    // SMART data
    if(d.smart_status){
      $('smart-section').style.display='block';
      let isOk=d.smart_status.toLowerCase()==='verified';
      $('pop-smart-status').innerHTML=isOk?
        '<span class="smart-badge smart-ok">✓ Verified</span>':
        '<span class="smart-badge smart-warn">⚠ '+d.smart_status+'</span>';
      $('pop-smart-model').textContent=d.smart_model||'—';
      $('pop-smart-trim').textContent=d.smart_trim||'—';
    }

    // Battery
    if(d.battery_pct!=null){
      $('pop-pwr-battery').textContent=d.battery_pct+'%'+(d.battery_charging?' ⚡':'');
    }

    // Uptime
    $('pop-uptime').textContent=fmtUptime(d.uptime_sec||0);
  }).catch(()=>{});
}

update();
setInterval(update,2000);
</script>
</body></html>'''
'''Popover HTML for status bar popover.'''
