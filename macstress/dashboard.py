"""Dashboard HTML — the main web UI."""

# This is the full dashboard HTML served at /
# Extracted verbatim from monolithic macstress.py

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MacStressMonitor Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--card:#12121a;--card2:#1a1a28;--border:rgba(255,255,255,.06);--muted:#666;--text:#e0e0e0}
body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Helvetica Neue',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.hdr{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.hdr h1{font-size:20px;font-weight:700;background:linear-gradient(90deg,#ff6b6b,#ffa500,#48dbfb);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.si{display:flex;gap:6px;flex-wrap:wrap}
.sb{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:4px 10px;font-size:11px;color:#999}
.sb b{color:#48dbfb}.sb.os b{color:#a29bfe}.sb.md b{color:#ffa500}
.ctrl{padding:8px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;justify-content:center}
.b{padding:7px 16px;border:1px solid var(--border);border-radius:10px;background:rgba(255,255,255,.04);color:#ccc;cursor:pointer;font-size:12px;font-weight:500;transition:.2s;display:flex;align-items:center;gap:5px;user-select:none}
.b:hover{background:rgba(255,255,255,.08);transform:translateY(-1px)}
.b.on{background:linear-gradient(135deg,#ff6b6b,#ee5a24);border-color:transparent;color:#fff;box-shadow:0 4px 15px rgba(255,107,107,.2)}
.b.go{background:linear-gradient(135deg,#2ed573,#26de81);border-color:transparent;color:#fff}
.b.bench{background:linear-gradient(135deg,#a29bfe,#6c5ce7);border-color:transparent;color:#fff}
.b.st{background:linear-gradient(135deg,#ff4757,#c0392b);border-color:transparent;color:#fff}
.d{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.d.y{background:#2ed573;box-shadow:0 0 6px rgba(46,213,115,.5);animation:pu 1.5s infinite}.d.n{background:#636e72}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.4}}
.timer{display:flex;align-items:center;gap:6px}
.timer select{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:8px;color:#ccc;padding:6px 10px;font-size:12px;cursor:pointer;outline:none;-webkit-appearance:none}
.timer select:hover{background:rgba(255,255,255,.1)}
.timer select option{background:#1a1a2e;color:#ccc}
.timer label{font-size:11px;color:#777}
.cd{font-size:13px;color:#ffa500;font-weight:600;padding:5px 14px;background:rgba(255,165,0,.08);border:1px solid rgba(255,165,0,.15);border-radius:8px;display:none;align-items:center;gap:5px;font-variant-numeric:tabular-nums;min-width:80px;justify-content:center}
.cd.vis{display:flex}
.dnd-banner{background:linear-gradient(135deg,rgba(255,165,0,.08),rgba(72,219,251,.08));border:1px solid rgba(255,165,0,.15);border-radius:10px;padding:8px 16px;margin:8px 16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px;animation:fadeIn .5s}
@keyframes fadeIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}
.dnd-banner span{font-size:12px;color:#aaa}
.dnd-banner button{background:rgba(255,165,0,.15);border:1px solid rgba(255,165,0,.3);border-radius:6px;color:#ffa500;padding:4px 12px;font-size:11px;cursor:pointer;transition:.2s;white-space:nowrap}
.dnd-banner button:hover{background:rgba(255,165,0,.25)}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;padding:12px 16px}
.c{cursor:grab;transition:transform .3s cubic-bezier(.4,0,.2,1),opacity .3s,box-shadow .3s}
.c.dragging{opacity:.4;transform:scale(.95);box-shadow:none!important}
.c.drag-over{transform:scale(1.02);box-shadow:0 0 20px rgba(255,165,0,.3)!important;border-color:rgba(255,165,0,.4)!important}
.c.drag-settle{animation:settle .4s cubic-bezier(.34,1.56,.64,1)}
@keyframes settle{0%{transform:scale(.9) translateY(10px);opacity:.7}50%{transform:scale(1.03)}100%{transform:scale(1);opacity:1}}
.c{background:linear-gradient(145deg,var(--card),var(--card2));border:1px solid var(--border);border-radius:14px;padding:16px;position:relative;overflow:hidden;user-select:none}
.c::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0}
.c.cpu::before{background:linear-gradient(90deg,#ff6b6b,#ee5a24)}
.c.gpu::before{background:linear-gradient(90deg,#ffa500,#f0932b)}
.c.mem::before{background:linear-gradient(90deg,#48dbfb,#0abde3)}
.c.swp::before{background:linear-gradient(90deg,#e056fd,#be2edd)}
.c.dsk::before{background:linear-gradient(90deg,#a29bfe,#6c5ce7)}
.c.tmp::before{background:linear-gradient(90deg,#ff4757,#ff6348)}
.c.pwr::before{background:linear-gradient(90deg,#ffa502,#e67e00)}
.c.inf::before{background:linear-gradient(90deg,#2ed573,#26de81)}
.c.bench::before{background:linear-gradient(90deg,#00d4ff,#0abde3)}
.ct{font-size:10px;color:#777;text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px}
.cv{font-size:36px;font-weight:700;line-height:1}
.cs{font-size:12px;color:#555;margin-top:4px}
.p{font-size:14px;color:#777;font-weight:400}
canvas{width:100%;height:60px;margin-top:8px;border-radius:6px}
.gr{display:flex;gap:14px;flex-wrap:wrap}
.gi{display:flex;align-items:center;gap:12px;flex:1;min-width:180px}
.ga{width:80px;height:80px;position:relative;flex-shrink:0}
.ga svg{transform:rotate(-90deg);width:80px;height:80px}
.ga circle{fill:none;stroke-width:7;stroke-linecap:round}
.ga .bg{stroke:rgba(255,255,255,.06)}
.ga .fg{transition:stroke-dashoffset .6s ease}
.gv{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700}
.gl{font-size:11px;color:#888;margin-bottom:2px}
.gb{font-size:24px;font-weight:700}
.gu{font-size:11px;color:#555}
.ir{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--border);font-size:12px}
.ir:last-child{border:none}.il{color:var(--muted)}.iv{color:#ccc;font-weight:600}
.sbar{height:6px;background:rgba(255,255,255,.06);border-radius:3px;margin-top:8px;overflow:hidden}
.sfill{height:100%;border-radius:3px;transition:width .5s;background:linear-gradient(90deg,#e056fd,#be2edd)}
.prow{display:flex;gap:16px;margin-top:4px}
.pi{flex:1;text-align:center}
.pi .pv{font-size:28px;font-weight:700;color:#ffa502}
.pi .pl{font-size:10px;color:#888;margin-bottom:2px}
.pi .pu{font-size:11px;color:#555}
@media(max-width:600px){.hdr h1{font-size:16px}.cv{font-size:26px}.g{padding:8px;gap:8px}.ga{width:60px;height:60px}.ga svg{width:60px;height:60px}}
</style></head><body>
<div class="hdr"><h1>&#9889; MacStressMonitor</h1><div class="si" id="si"></div></div>
<div class="ctrl" id="ctrl"></div>
<div id="dndBanner"></div>
<div class="g" id="grid"></div>
<script>
const H=120;let hist=[],SI={},running=false,cdi=null,endT=0;
const $=id=>document.getElementById(id);

const TILES={
cpu:`<div class="c cpu" data-tile="cpu" draggable="true"><div class="ct">CPU Usage</div><div class="cv" id="cpuV">&mdash;</div><div class="cs" id="cpuS"></div><canvas id="cpuC"></canvas></div>`,
tmp:`<div class="c tmp" data-tile="tmp" draggable="true"><div class="ct">Temperatures</div><div class="gr">
<div class="gi"><div class="ga"><svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle class="fg" id="ctA" cx="50" cy="50" r="42" stroke="#ff4757" stroke-dasharray="264" stroke-dashoffset="264"/></svg><div class="gv" id="ctV">&mdash;</div></div><div><div class="gl">CPU</div><div class="gb" id="ctB">&mdash;</div><div class="gu">&deg;C</div></div></div>
<div class="gi"><div class="ga"><svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle class="fg" id="gtA" cx="50" cy="50" r="42" stroke="#ffa500" stroke-dasharray="264" stroke-dashoffset="264"/></svg><div class="gv" id="gtV">&mdash;</div></div><div><div class="gl">GPU</div><div class="gb" id="gtB">&mdash;</div><div class="gu">&deg;C</div></div></div>
</div></div>`,
pwr:`<div class="c pwr" data-tile="pwr" draggable="true"><div class="ct">Power Consumption</div><div class="prow" id="pwrRow">
<div class="pi"><div class="pl">CPU</div><div class="pv" id="cpwV">&mdash;</div><div class="pu">watts</div></div>
<div class="pi"><div class="pl">GPU</div><div class="pv" id="gpwV">&mdash;</div><div class="pu">watts</div></div>
<div class="pi"><div class="pl">TOTAL</div><div class="pv" id="tpwV">&mdash;</div><div class="pu">watts</div></div>
</div><div class="cs" id="pwrH" style="color:#777;text-align:center;margin-top:6px"></div></div>`,
mem:`<div class="c mem" data-tile="mem" draggable="true"><div class="ct">Memory (RAM)</div><div class="cv" id="memV">&mdash;</div><div class="cs" id="memS"></div><canvas id="memC"></canvas></div>`,
swp:`<div class="c swp" data-tile="swp" draggable="true"><div class="ct">Swap (SSD &#8594; RAM)</div><div class="cv" id="swpV" style="font-size:26px">&mdash;</div><div class="cs" id="swpS"></div><div class="sbar"><div class="sfill" id="swpB"></div></div></div>`,
dsk:`<div class="c dsk" data-tile="dsk" draggable="true"><div class="ct">Disk I/O</div><div class="cv" id="dskV" style="font-size:26px">&mdash;</div><div class="cs" id="dskS"></div><canvas id="dskC"></canvas></div>`,
bench:`<div class="c bench" data-tile="bench" draggable="true"><div class="ct">Тест диску</div><div style="display:flex;flex-direction:column;justify-content:center;height:100%;"><button class="b bench" onclick="diskBench()" id="benchBtn" style="width:100%;margin-bottom:10px;font-size:14px;padding:12px">&#128300; ЗАПУСТИТИ ТЕСТ</button><div id="benchRes" style="font-family:'SF Mono',monospace;font-size:13px;color:#aaa;line-height:1.6"></div></div></div>`,
inf:`<div class="c inf" data-tile="inf" draggable="true"><div class="ct">System Info</div><div id="info" style="font-size:12px;color:#aaa;line-height:1.6"></div><div id="updStatus" style="margin-top:8px;border-top:1px solid #333;padding-top:8px"><button class="b" style="background:#333;font-size:11px;padding:4px 8px;width:100%" onclick="checkUpd()">&#128260; Check for Updates</button></div></div>`
};
const DEF_ORDER=['cpu','tmp','pwr','mem','swp','dsk','bench','inf'];
function getTileOrder(){try{let o=JSON.parse(localStorage.getItem('ms_tile_order'));if(o&&o.length===DEF_ORDER.length)return o;}catch(e){}return DEF_ORDER;}
function saveTileOrder(){let tiles=[...document.querySelectorAll('[data-tile]')].map(t=>t.dataset.tile);localStorage.setItem('ms_tile_order',JSON.stringify(tiles));}
function initBanner(){
if(localStorage.getItem('ms_dnd_dismissed'))return;
$('dndBanner').innerHTML='<div class="dnd-banner"><span>\u2728 Перетягуйте плитки, щоб змінити їх порядок</span><button onclick="dismissBanner()">Зрозумів</button></div>';}
function dismissBanner(){localStorage.setItem('ms_dnd_dismissed','1');let b=$('dndBanner');if(b){b.querySelector('.dnd-banner').style.animation='fadeIn .3s reverse forwards';setTimeout(()=>{b.innerHTML='';},300);}}
let dragSrc=null;
function initDrag(){
document.querySelectorAll('[data-tile]').forEach(t=>{
t.addEventListener('dragstart',e=>{dragSrc=t;t.classList.add('dragging');e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',t.dataset.tile);});
t.addEventListener('dragend',()=>{dragSrc=null;document.querySelectorAll('.dragging,.drag-over').forEach(el=>{el.classList.remove('dragging','drag-over');});});
t.addEventListener('dragover',e=>{e.preventDefault();e.dataTransfer.dropEffect='move';if(t!==dragSrc)t.classList.add('drag-over');});
t.addEventListener('dragleave',()=>{t.classList.remove('drag-over');});
t.addEventListener('drop',e=>{e.preventDefault();t.classList.remove('drag-over');
if(!dragSrc||dragSrc===t)return;
let grid=$('grid'),all=[...grid.querySelectorAll('[data-tile]')];
let fi=all.indexOf(dragSrc),ti=all.indexOf(t);
if(fi<ti)t.after(dragSrc);else t.before(dragSrc);
dragSrc.classList.remove('dragging');dragSrc.classList.add('drag-settle');
t.classList.add('drag-settle');
setTimeout(()=>{dragSrc&&dragSrc.classList.remove('drag-settle');t.classList.remove('drag-settle');},500);
saveTileOrder();
});});}
function init(){
let order=getTileOrder();
$('grid').innerHTML=order.map(k=>TILES[k]).join('');
initDrag();
initBanner();}

function ch(id,data,col,mx){let c=$(id);if(!c)return;let x=c.getContext('2d'),W=c.width=c.offsetWidth*2,Hc=c.height=c.offsetHeight*2;
x.clearRect(0,0,W,Hc);let g=x.createLinearGradient(0,0,0,Hc);g.addColorStop(0,col+'35');g.addColorStop(1,col+'05');
x.beginPath();let s=W/(H-1);for(let i=0;i<data.length;i++){let px=i*s,py=Hc-(data[i]/mx)*Hc;i===0?x.moveTo(px,py):x.lineTo(px,py);}
x.strokeStyle=col;x.lineWidth=2;x.stroke();x.lineTo((data.length-1)*s,Hc);x.lineTo(0,Hc);x.closePath();x.fillStyle=g;x.fill();}

function ga(aId,vId,bId,val,mx,col){
if(val==null){$(vId)&&($(vId).textContent='\u2014');$(bId)&&($(bId).textContent='\u2014');return;}
let p=Math.min(val/mx,1),off=264*(1-p);let a=$(aId);if(a){a.style.strokeDashoffset=off;a.style.stroke=col;}
$(vId)&&($(vId).textContent=Math.round(val)+'\u00b0');$(bId)&&($(bId).textContent=val.toFixed(1));}

function pwV(id,val){let el=$(id);if(!el)return;el.textContent=val!=null?val.toFixed(1):'\u2014';}
function pwHint(){let h=$('pwrH');if(!h)return;
let cpw=$('cpwV'),tpw=$('tpwV');
if((cpw&&cpw.textContent!=='\u2014')||(tpw&&tpw.textContent!=='\u2014'))h.textContent='';
else h.textContent='\u23f3 Waiting for power data...';}

function upd(d){
let cpu=d.cpu_usage||0;$('cpuV').innerHTML=cpu.toFixed(1)+'<span class="p">%</span>';
$('cpuS').textContent=(SI.cores||'?')+' cores'+(d.cpu_freq_ghz?' \u00b7 '+d.cpu_freq_ghz.toFixed(2)+' GHz':'');
let mp=d.mem_used_pct||0;$('memV').innerHTML=mp.toFixed(1)+'<span class="p">%</span>';
$('memS').textContent=(d.mem_used_gb||0)+' / '+(d.mem_total_gb||0)+' GB RAM';
ga('ctA','ctV','ctB',d.cpu_temp,110,'#ff4757');
ga('gtA','gtV','gtB',d.gpu_temp,110,'#ffa500');
pwV('cpwV',d.cpu_power_w);pwV('gpwV',d.gpu_power_w);pwV('tpwV',d.total_power_w);pwHint();
let su=d.swap_used_gb||0,st=d.swap_total_gb||0;
$('swpV').innerHTML=su.toFixed(2)+' <span class="p">/ '+st.toFixed(1)+' GB</span>';
$('swpS').textContent=st>0?(su/st*100).toFixed(1)+'% used \u2014 SSD pressure':'No swap active';
$('swpB').style.width=(st>0?Math.min(su/st*100,100):0)+'%';
$('dskV').textContent=(d.disk_read_mb||0).toFixed(1)+' / '+(d.disk_write_mb||0).toFixed(1);
$('dskS').textContent='Read / Write MB/s';
let i='';function r(l,v){return '<div class="ir"><span class="il">'+l+'</span><span class="iv">'+v+'</span></div>';}
i+=r('Model',SI.model_name||'\u2014');i+=r('OS',SI.os||'\u2014');i+=r('Arch',(SI.arch||'').toUpperCase());
i+=r('CPU',SI.cpu||'\u2014');i+=r('GPU',SI.gpu||'\u2014');
if(d.fan_rpm!=null)i+=r('Fan',d.fan_rpm+' RPM');
$('info').innerHTML=i;
hist.push({cpu,mem:mp,disk:(d.disk_read_mb||0)+(d.disk_write_mb||0)});if(hist.length>H)hist.shift();
ch('cpuC',hist.map(h=>h.cpu),'#ff6b6b',100);
ch('memC',hist.map(h=>h.mem),'#48dbfb',100);
ch('dskC',hist.map(h=>h.disk),'#a29bfe',Math.max(...hist.map(h=>h.disk),.1));}

let ctrlInit=false;
function mkC(a){
running=a.length>0;
let ts=['cpu','gpu','memory','disk'];
let tBtns=ts.map(t=>'<button class="b '+(a.includes(t)?'on':'')+'" data-t="'+t+'" onclick="tog(this)"><span class="d '+(a.includes(t)?'y':'n')+'"></span>'+t.toUpperCase()+'</button>').join('');
let allBtn=running
 ?'<button class="b st" onclick="tA(0)">&#9724; STOP ALL</button>'
 :'<button class="b go" onclick="tA(1)">&#9654; START ALL</button>';
let timer='<div class="timer"><label>Duration:</label><select id="dur"><option value="60">1 min</option><option value="300">5 min</option><option value="600" selected>10 min</option><option value="1800">30 min</option><option value="3600">1 hour</option><option value="0">&#8734; No limit</option></select></div>';
let cd='<div class="cd'+(endT>0?' vis':'')+'" id="cdBox">&#9200; <span id="cdT"></span></div>';
let hint='<div style="font-size:11px;color:#555;margin-top:6px;text-align:center">'
 +'<span style="color:#444">&#128161;</span> '
 +'Натисніть кнопку щоб увімкнути/вимкнути окремий тест'
 +'&nbsp;·&nbsp; <b style="color:#2ed573">START ALL</b> — запустити всі'
 +'</div>';
$('ctrl').innerHTML=tBtns+timer+allBtn+cd+hint;
ctrlInit=true;
}
function uC(a){
let wasRunning=running;
running=a.length>0;
document.querySelectorAll('.b[data-t]').forEach(b=>{let on=a.includes(b.dataset.t);b.className='b '+(on?'on':'');b.querySelector('.d').className='d '+(on?'y':'n');});
if(wasRunning!==running){
 let allBtns=document.querySelectorAll('.b.go,.b.st');
 allBtns.forEach(b=>{
  if(running){b.className='b st';b.innerHTML='&#9724; STOP ALL';b.onclick=()=>tA(0);}
  else{b.className='b go';b.innerHTML='&#9654; START ALL';b.onclick=()=>tA(1);}
 });
}
if(!running){endT=0;if(cdi){clearInterval(cdi);cdi=null;}
 let cb=$('cdBox');if(cb)cb.className='cd';}}

function updCD(){
let cb=$('cdBox'),ct=$('cdT');
if(!cb||!ct)return;
if(endT<=0){cb.className='cd';return;}
let rem=Math.max(0,Math.ceil((endT-Date.now())/1000));
if(rem<=0){cb.className='cd';endT=0;if(cdi){clearInterval(cdi);cdi=null;}return;}
let m=Math.floor(rem/60),s=rem%60;
ct.textContent=m+':'+(s<10?'0':'')+s;
cb.className='cd vis';}

function tog(b){let dur=$('dur')?$('dur').value:'600';fetch('/api/toggle?test='+b.dataset.t+'&dur='+dur,{method:'POST'});}
function tA(on){let dur=$('dur')?$('dur').value:'600';
fetch('/api/toggle_all?on='+on+'&dur='+dur,{method:'POST'});
if(on==1&&parseInt(dur)>0){endT=Date.now()+parseInt(dur)*1000;if(cdi)clearInterval(cdi);cdi=setInterval(updCD,200);updCD();}
else if(on==0){endT=0;if(cdi){clearInterval(cdi);cdi=null;}let cb=$('cdBox');if(cb)cb.className='cd';}}

function checkUpd(){
 let b=document.querySelector('#updStatus button');
 b.disabled=true;b.textContent='Перевірка...';
 fetch('/api/check_update').then(r=>r.json()).then(d=>{
  let s=document.getElementById('updStatus');
  if(d.has_update){
   s.innerHTML='<div style="color:#2ed573;margin-bottom:5px">🆕 Нова версія: v'+d.latest+'</div><button class="b go" style="display:block;width:100%;text-align:center;font-size:11px;padding:6px;background:#2ed573;color:#000;border:none;border-radius:6px;cursor:pointer" onclick="doUpdate(this,\''+d.latest+'\')">⬇ Оновити</button>';
  } else {
   b.textContent='\u2705 Актуальна (v'+d.current+')';
   b.style.background='rgba(46,213,115,0.1)';
   b.style.color='#2ed573';
   setTimeout(()=>{b.disabled=false;b.textContent='\ud83d\udd04 Check for Updates';b.style.background='#333';b.style.color='#fff'}, 5000);
  }
 });
}
function doUpdate(btn,ver){
 btn.disabled=true;btn.textContent='\u23f3 Оновлення...';
 fetch('/api/do_update?ver='+ver,{method:'POST'}).then(r=>r.json()).then(d=>{
  if(d.ok){btn.textContent='\u2705 Перезавантаження...';btn.style.background='#2ed573';
   setTimeout(()=>{location.reload()},3000);
  } else {btn.textContent='\u274c '+d.error;btn.style.background='#c0392b';}
 }).catch(()=>{btn.textContent='\u274c Помилка мережі';btn.style.background='#c0392b';});
}

function diskBench(){
let bb=document.getElementById('benchBtn');if(!bb)return;
let res=document.getElementById('benchRes');
bb.disabled=true;bb.textContent='⏳ Виконується...';
if(res)res.innerHTML='';
fetch('/api/disk_bench',{method:'POST'}).then(()=>{
 let pi=setInterval(()=>{
  fetch('/api/disk_bench_result').then(r=>r.json()).then(d=>{
   if(!d.running&&d.results.length>0){
    clearInterval(pi);bb.disabled=false;bb.textContent='✅ Готово';
    setTimeout(()=>{bb.disabled=false;bb.textContent='🔄 ПОВТОРИТИ';bb.style.background='';}, 2000);
    let t='<table style="width:100%;border-collapse:collapse"><tr style="color:#666;font-size:11px;text-transform:uppercase;letter-spacing:.8px"><td>Тест</td><td style="text-align:right">Запис</td><td style="text-align:right">Читання</td></tr>';
    d.results.forEach(r=>{t+='<tr style="border-top:1px solid #222"><td style="color:#ddd;font-size:13px;padding:4px 0">'+r.label+'</td><td style="text-align:right;color:#ff6b6b;font-size:15px;font-weight:700">'+r.write_mb+'</td><td style="text-align:right;color:#48dbfb;font-size:15px;font-weight:700">'+r.read_mb+'</td></tr>';});
    t+='<tr><td colspan="3" style="font-size:10px;color:#555;padding-top:4px;text-align:right">МБ/с</td></tr></table>';
    if(res)res.innerHTML=t;
   } else if(d.running){
     bb.textContent='⏳ '+d.results.length+'/4 тестів';
     if(d.results.length>0 && res){
        let last=d.results[d.results.length-1];
        res.innerHTML='<span style="color:#777;font-size:12px">Зараз: '+last.label+'</span><br><span style="color:#ff6b6b">Запис: '+last.write_mb+'</span> · <span style="color:#48dbfb">Читання: '+last.read_mb+'</span> МБ/с';
     }
   }
  });
 },1000);
});}

function sse(){let es=new EventSource('/events');
es.onmessage=e=>{try{let d=JSON.parse(e.data);
if(d.sys_info&&!ctrlInit){SI=d.sys_info;mkI();mkC(d.active||[]);}
if(d.sys_info&&ctrlInit){SI=d.sys_info;mkI();}
if(d.metrics)upd(d.metrics);
if(d.active)uC(d.active);
}catch(x){}};
es.onerror=()=>{es.close();setTimeout(sse,2000);};}

function mkI(){let s=SI;$('si').innerHTML=
'<div class="sb md"><b>'+s.model_name+'</b></div>'+
'<div class="sb os"><b>'+s.os+'</b></div>'+
'<div class="sb"><b>'+(s.arch||'').toUpperCase()+'</b></div>'+
'<div class="sb"><b>'+s.cores+'</b> cores \u00b7 <b>'+s.ram_gb+'</b> GB</div>';}
init();sse();
</script></body></html>'''
