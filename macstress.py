#!/usr/bin/env python3
"""
MacStress — Native macOS Stress Test + System Monitor
Menu bar app with real-time CPU/RAM/SSD display.
Supports Intel & Apple Silicon. Single file, no external deps except PyObjC.

Usage:
  python3 macstress.py          (menu bar monitor + dashboard)
  sudo python3 macstress.py     (adds power consumption data)

Install PyObjC if needed:
  pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit
"""

import os, sys, json, time, math, mmap, re, signal, struct, random, hashlib
import platform, subprocess, threading, tempfile, shutil, socket
import urllib.parse
import multiprocessing as mp
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import deque
from pathlib import Path

VERSION = "1.3.0"
GITHUB_REPO = "vzekalo/MacStressMonitor"

# ═══════════════════════════ System Detection ═══════════════════════════

def detect_system():
    arch = platform.machine()
    is_apple_silicon = arch == "arm64"
    cpu_brand = subprocess.getoutput("sysctl -n machdep.cpu.brand_string").strip()
    core_count = mp.cpu_count()
    try:
        perf_cores = int(subprocess.getoutput("sysctl -n hw.perflevel0.logicalcpu").strip())
        eff_cores = int(subprocess.getoutput("sysctl -n hw.perflevel1.logicalcpu").strip())
    except Exception:
        perf_cores, eff_cores = core_count, 0
    mem_bytes = int(subprocess.getoutput("sysctl -n hw.memsize").strip())
    model_id = subprocess.getoutput("sysctl -n hw.model").strip()
    model_name = subprocess.getoutput(
        "system_profiler SPHardwareDataType 2>/dev/null | grep 'Model Name' | cut -d: -f2"
    ).strip() or model_id
    os_ver = subprocess.getoutput("sw_vers -productVersion").strip()
    os_name = subprocess.getoutput("sw_vers -productName").strip()
    os_build = subprocess.getoutput("sw_vers -buildVersion").strip()
    gpu_name = cpu_brand if is_apple_silicon else (
        subprocess.getoutput(
            "system_profiler SPDisplaysDataType 2>/dev/null | grep 'Chipset Model' | head -1 | cut -d: -f2"
        ).strip() or "Intel Integrated"
    )
    return {
        "arch": "apple_silicon" if is_apple_silicon else "intel",
        "cpu": cpu_brand, "model_id": model_id, "model_name": model_name,
        "gpu": gpu_name, "os": f"{os_name} {os_ver} ({os_build})",
        "cores": core_count, "perf_cores": perf_cores, "eff_cores": eff_cores,
        "ram_gb": round(mem_bytes / (1024**3), 1),
    }

# ═══════════════════════ Temperature Sensor (Apple Silicon) ══════════════
# Based on fermion-star/apple_sensors (BSD-3-Clause license)

TEMP_SENSOR_SRC = r'''
#include <stdio.h>
#include <unistd.h>
#import <Foundation/Foundation.h>
#import <IOKit/hidsystem/IOHIDEventSystemClient.h>

typedef struct __IOHIDEvent *IOHIDEventRef;
typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
#ifdef __LP64__
typedef double IOHIDFloat;
#else
typedef float IOHIDFloat;
#endif
#define kIOHIDEventTypeTemperature 15
#define IOHIDEventFieldBase(type) (type << 16)

IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef allocator);
int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef client, CFDictionaryRef match);
IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
CFStringRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef service, CFStringRef property);
IOHIDFloat IOHIDEventGetFloatValue(IOHIDEventRef event, int32_t field);

int main() {
    CFNumberRef nums[2]; CFStringRef keys[2];
    int page = 0xff00, usage = 5;
    keys[0] = CFStringCreateWithCString(0, "PrimaryUsagePage", 0);
    keys[1] = CFStringCreateWithCString(0, "PrimaryUsage", 0);
    nums[0] = CFNumberCreate(0, kCFNumberSInt32Type, &page);
    nums[1] = CFNumberCreate(0, kCFNumberSInt32Type, &usage);
    CFDictionaryRef match = CFDictionaryCreate(0, (const void**)keys, (const void**)nums, 2,
                              &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    while (1) {
        IOHIDEventSystemClientRef system = IOHIDEventSystemClientCreate(kCFAllocatorDefault);
        IOHIDEventSystemClientSetMatching(system, match);
        CFArrayRef srvs = IOHIDEventSystemClientCopyServices(system);
        if (srvs) {
            long count = CFArrayGetCount(srvs);
            for (int i = 0; i < count; i++) {
                IOHIDServiceClientRef sc = (IOHIDServiceClientRef)CFArrayGetValueAtIndex(srvs, i);
                CFStringRef name = IOHIDServiceClientCopyProperty(sc, CFSTR("Product"));
                IOHIDEventRef event = IOHIDServiceClientCopyEvent(sc, kIOHIDEventTypeTemperature, 0, 0);
                double val = 0;
                if (event) { val = IOHIDEventGetFloatValue(event, IOHIDEventFieldBase(kIOHIDEventTypeTemperature)); CFRelease(event); }
                if (name && val > 0) {
                    char buf[256];
                    CFStringGetCString(name, buf, sizeof(buf), kCFStringEncodingUTF8);
                    printf("%s: %.2f\n", buf, val);
                }
                if (name) CFRelease(name);
            }
            CFRelease(srvs);
        }
        CFRelease(system);
        printf("---\n"); fflush(stdout);
        usleep(1500000);
    }
    return 0;
}
'''

def compile_temp_sensor():
    sensor_dir = Path(tempfile.gettempdir()) / "macstress_sensor"
    sensor_dir.mkdir(exist_ok=True)
    src = sensor_dir / "temp_sensor.m"
    binary = sensor_dir / "temp_sensor"
    src_hash = hashlib.md5(TEMP_SENSOR_SRC.encode()).hexdigest()[:8]
    hash_file = sensor_dir / "hash.txt"
    if binary.exists() and hash_file.exists() and hash_file.read_text().strip() == src_hash:
        return str(binary)
    src.write_text(TEMP_SENSOR_SRC)
    r = subprocess.run(
        ['clang', '-Wall', '-O2', str(src), '-framework', 'IOKit', '-framework', 'Foundation', '-o', str(binary)],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode == 0:
        hash_file.write_text(src_hash)
        print("  ✅ Temperature sensor compiled")
        return str(binary)
    print(f"  ⚠️  Sensor compile failed: {r.stderr[:200]}")
    return None

# ═══════════════════════════ Stress Workers ═════════════════════════════

def cpu_stress_worker(stop_event, core_id, is_intel):
    x = 1.0000001
    if is_intel:
        while not stop_event.is_set():
            for _ in range(200000):
                x = math.sin(x) * math.cos(x) + math.sqrt(abs(x) + 1)
                x = math.tan(x + 0.0001) * math.log(abs(x) + 1)
                x = math.exp(min(abs(x), 500) * 0.001) * math.atan2(x, x + 1)
                x = (x * 1.0000001) + hashlib.sha256(struct.pack('d', x)).digest()[0] * 1e-7
    else:
        while not stop_event.is_set():
            for _ in range(500000):
                x = math.sin(x) * math.cos(x) + math.sqrt(abs(x) + 1)
                x = math.tan(x + 0.0001) * math.log(abs(x) + 1)
                x = (x * 1.0000001) + hashlib.md5(struct.pack('d', x)).digest()[0] * 1e-7

def gpu_stress_worker(stop_event, sys_info):
    N = 128
    while not stop_event.is_set():
        a = [[random.random() for _ in range(N)] for _ in range(N)]
        b = [[random.random() for _ in range(N)] for _ in range(N)]
        _ = [[sum(a[i][k]*b[k][j] for k in range(N)) for j in range(N)] for i in range(N)]
        if sys_info["arch"] == "apple_silicon":
            try:
                ms = '#include <metal_stdlib>\nusing namespace metal;\nkernel void s(device float *d [[buffer(0)]], uint i [[thread_position_in_grid]]){float x=d[i];for(int j=0;j<50000;j++){x=sin(x)*cos(x)+sqrt(abs(x)+1.0);}d[i]=x;}\n'
                t = tempfile.NamedTemporaryFile(suffix='.metal', delete=False, mode='w')
                t.write(ms); t.close()
                subprocess.run(['xcrun', '-sdk', 'macosx', 'metal', '-c', t.name, '-o', '/dev/null'],
                              capture_output=True, timeout=15)
                os.unlink(t.name)
            except Exception: pass

def memory_stress_worker(stop_event, target_gb):
    blocks, chunk = [], 256 * 1024 * 1024
    target = int(target_gb * 1024**3)
    allocated = 0
    try:
        while allocated < target and not stop_event.is_set():
            sz = min(chunk, target - allocated)
            blk = mmap.mmap(-1, sz)
            blk.write(os.urandom(min(sz, 4096)) * (sz // 4096))
            blocks.append(blk); allocated += sz
            time.sleep(0.1)
        while not stop_event.is_set():
            for blk in blocks:
                if stop_event.is_set(): break
                blk.seek(0); blk.write(os.urandom(4096))
                time.sleep(0.05)
    finally:
        for blk in blocks:
            try: blk.close()
            except Exception: pass

def disk_stress_worker(stop_event, worker_id):
    tmp = tempfile.mkdtemp(prefix=f"macstress_disk_{worker_id}_")
    chunk = bytearray(os.urandom(1024 * 1024))
    try:
        while not stop_event.is_set():
            fp = os.path.join(tmp, f"s{worker_id}.bin")
            with open(fp, 'wb') as f:
                for _ in range(128):
                    if stop_event.is_set(): break
                    f.write(chunk)
            if stop_event.is_set(): break
            with open(fp, 'rb') as f:
                while f.read(1024*1024):
                    if stop_event.is_set(): break
            try: os.unlink(fp)
            except Exception: pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ═══════════════════════════ Metrics Collector ══════════════════════════

class MetricsCollector:
    def __init__(self, sys_info):
        self.sys_info = sys_info
        self.data = {
            "cpu_usage": 0, "cpu_temp": None, "gpu_temp": None,
            "mem_used_pct": 0, "mem_used_gb": 0, "mem_total_gb": sys_info["ram_gb"],
            "swap_used_gb": 0, "swap_total_gb": 0,
            "disk_read_mb": 0, "disk_write_mb": 0,
            "fan_rpm": None, "cpu_freq_ghz": None,
            "cpu_power_w": None, "gpu_power_w": None, "total_power_w": None,
            "per_core_usage": [], "timestamp": 0,
        }
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._history = deque(maxlen=120)
        self._pm_proc = None
        self._ts_proc = None

    def start(self):
        threading.Thread(target=self._collect_loop, daemon=True).start()
        if self.sys_info["arch"] == "apple_silicon":
            ts_bin = compile_temp_sensor()
            if ts_bin:
                threading.Thread(target=self._sensor_loop, args=(ts_bin,), daemon=True).start()
        # Always start powermetrics — uses osascript elevation if not root
        threading.Thread(target=self._powermetrics_loop, daemon=True).start()

    def stop(self):
        self._stop.set()
        for p in [self._pm_proc, self._ts_proc]:
            if p:
                try: p.kill()
                except Exception: pass

    def get_snapshot(self):
        with self._lock:
            return dict(self.data)

    def _collect_loop(self):
        cores = self.sys_info["cores"]
        while not self._stop.is_set():
            try:
                cpu_raw = subprocess.getoutput(
                    "ps -A -o %cpu | awk '{s+=$1} END {printf \"%.1f\", s}'"
                )
                try:
                    cpu_total = min(round(float(cpu_raw.strip()) / cores, 1), 100.0)
                except (ValueError, ZeroDivisionError):
                    cpu_total = 0.0

                vm = subprocess.getoutput("vm_stat")
                ps = 16384 if self.sys_info["arch"] == "apple_silicon" else 4096
                active = self._pvm(vm, "Pages active")
                wired = self._pvm(vm, "Pages wired down")
                compressed = self._pvm(vm, "Pages occupied by compressor")
                used_bytes = (active + wired + compressed) * ps
                used_gb = used_bytes / (1024**3)
                mem_pct = (used_gb / self.sys_info["ram_gb"]) * 100 if self.sys_info["ram_gb"] > 0 else 0

                swap_used, swap_total = 0.0, 0.0
                try:
                    sw = subprocess.getoutput("sysctl vm.swapusage")
                    m_total = re.search(r'total\s*=\s*([\d.]+)M', sw)
                    m_used = re.search(r'used\s*=\s*([\d.]+)M', sw)
                    if m_total: swap_total = float(m_total.group(1)) / 1024
                    if m_used: swap_used = float(m_used.group(1)) / 1024
                except Exception: pass

                disk_r = disk_w = 0.0
                try:
                    io = subprocess.getoutput("iostat -d -c 2 2>/dev/null | tail -1").split()
                    if len(io) >= 3:
                        disk_r, disk_w = float(io[1]) / 1024, float(io[2]) / 1024
                except Exception: pass

                with self._lock:
                    self.data.update({
                        "cpu_usage": cpu_total, "mem_used_pct": round(mem_pct, 1),
                        "mem_used_gb": round(used_gb, 1), "swap_used_gb": round(swap_used, 2),
                        "swap_total_gb": round(swap_total, 2),
                        "disk_read_mb": round(disk_r, 2), "disk_write_mb": round(disk_w, 2),
                        "timestamp": time.time(),
                    })
                    self._history.append(dict(self.data))
            except Exception: pass
            time.sleep(0.5)

    def _sensor_loop(self, binary):
        try:
            self._ts_proc = subprocess.Popen(
                [binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            buf = []
            for line in self._ts_proc.stdout:
                if self._stop.is_set(): break
                line = line.strip()
                if line == "---":
                    self._parse_sensors(buf); buf = []
                else:
                    buf.append(line)
        except Exception: pass

    def _parse_sensors(self, lines):
        cpu_t, gpu_t = [], []
        for l in lines:
            if ':' not in l: continue
            name_val = l.rsplit(':', 1)
            if len(name_val) != 2: continue
            name = name_val[0].strip().lower()
            try: v = float(name_val[1].strip())
            except ValueError: continue
            if v < 1 or v > 130: continue
            if 'tdie' in name: cpu_t.append(v)
            elif name.endswith('g') and name.startswith('pmu tp'): gpu_t.append(v)
            elif name.endswith('s') and name.startswith('pmu tp'): cpu_t.append(v)

        with self._lock:
            if cpu_t: self.data["cpu_temp"] = round(max(cpu_t), 1)
            if gpu_t: self.data["gpu_temp"] = round(max(gpu_t), 1)

    def _powermetrics_loop(self):
        """Run powermetrics with admin privileges (piping password via sudo -S)."""
        try:
            samplers = "smc,cpu_power,gpu_power" if self.sys_info["arch"] == "intel" else "cpu_power,gpu_power"

            def _stream_pm_simple(cmd_prefix=[]):
                """Stream powermetrics output continuously (no stdin needed)."""
                self._pm_proc = subprocess.Popen(
                    cmd_prefix + ["powermetrics", "--samplers", samplers, "-i", "2000", "-n", "0"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                buf = []
                for line in self._pm_proc.stdout:
                    if self._stop.is_set(): break
                    buf.append(line)
                    if line.strip() == "" and len(buf) > 5:
                        self._parse_pm("".join(buf)); buf = []

            # Strategy 1: Already root
            if os.geteuid() == 0:
                _stream_pm_simple()
                return

            # Strategy 2: sudo -n works (no password needed — cached or NOPASSWD)
            try:
                test = subprocess.run(["sudo", "-n", "powermetrics", "--samplers", samplers, "-i", "1000", "-n", "1"],
                                      capture_output=True, timeout=10)
                if test.returncode == 0:
                    _stream_pm_simple(["sudo", "-n"])
                    return
            except Exception:
                pass

            # Strategy 3: Use password from pre-elevation (piped via sudo -S)
            pw = getattr(self, '_sudo_pw', None)
            if pw:
                self._pm_proc = subprocess.Popen(
                    ["sudo", "-S", "powermetrics", "--samplers", samplers, "-i", "2000", "-n", "0"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                self._pm_proc.stdin.write(pw + "\n")
                self._pm_proc.stdin.flush()
                self._sudo_pw = None  # Clear password from memory
                buf = []
                for line in self._pm_proc.stdout:
                    if self._stop.is_set(): break
                    buf.append(line)
                    if line.strip() == "" and len(buf) > 5:
                        self._parse_pm("".join(buf)); buf = []
                return

        except Exception as e:
            print(f"  ⚠️  powermetrics: {e}")

    def _parse_pm(self, block):
        ct = gt = fan = freq = cpu_pw = gpu_pw = None
        for l in block.split("\n"):
            ll = l.lower().strip()
            if "cpu die temperature" in ll or "cpu thermal level" in ll:
                try: ct = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                except: pass
            elif "gpu die temperature" in ll or "gpu thermal level" in ll:
                try: gt = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                except: pass
            elif "fan" in ll and "rpm" in ll:
                try: fan = int(re.search(r'(\d+)', ll).group(1))
                except: pass
            elif "cpu power" in ll and ("mw" in ll or "w" in ll):
                try:
                    v = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                    cpu_pw = v / 1000 if "mw" in ll else v
                except: pass
            elif "gpu power" in ll and ("mw" in ll or "w" in ll):
                try:
                    v = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                    gpu_pw = v / 1000 if "mw" in ll else v
                except: pass
            elif "package power" in ll and ("mw" in ll or "w" in ll):
                try:
                    v = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                    if cpu_pw is None: cpu_pw = v / 1000 if "mw" in ll else v
                except: pass
            elif "hw active frequency" in ll or "average frequency" in ll:
                try:
                    v = float(re.search(r'([\d.]+)', ll.split(":")[-1]).group(1))
                    freq = v / 1000 if v > 100 else v
                except: pass
        with self._lock:
            if ct is not None: self.data["cpu_temp"] = round(ct, 1)
            if gt is not None: self.data["gpu_temp"] = round(gt, 1)
            if fan is not None: self.data["fan_rpm"] = fan
            if cpu_pw is not None: self.data["cpu_power_w"] = round(cpu_pw, 1)
            if gpu_pw is not None: self.data["gpu_power_w"] = round(gpu_pw, 1)
            if cpu_pw is not None:
                self.data["total_power_w"] = round((cpu_pw or 0) + (gpu_pw or 0), 1)
            if freq is not None: self.data["cpu_freq_ghz"] = round(freq, 2)

    def _pvm(self, text, key):
        for l in text.split("\n"):
            if key in l:
                try: return int(l.split(":")[-1].strip().rstrip('.'))
                except: pass
        return 0

# ═══════════════════════════ HTML Dashboard ═════════════════════════════

DASHBOARD_HTML = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MacStress Dashboard</title>
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
<div class="hdr"><h1>&#9889; MacStress</h1><div class="si" id="si"></div></div>
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
inf:`<div class="c inf" data-tile="inf" draggable="true"><div class="ct">System Info</div><div id="info"></div></div>`
};
const DEF_ORDER=['cpu','tmp','pwr','mem','swp','dsk','inf'];
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
let bench='<button class="b bench" onclick="diskBench()" id="benchBtn">&#128300; BENCHMARK</button>';
$('ctrl').innerHTML=tBtns+timer+allBtn+bench+cd;
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

function diskBench(){
let bb=document.getElementById('benchBtn');if(!bb)return;
bb.disabled=true;bb.textContent='⏳ Running...';
fetch('/api/disk_bench',{method:'POST'}).then(()=>{
 let pi=setInterval(()=>{
  fetch('/api/disk_bench_result').then(r=>r.json()).then(d=>{
   if(!d.running&&d.results.length>0){
    clearInterval(pi);bb.disabled=false;bb.textContent='🔬 BENCHMARK';
    let h='<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.85);z-index:999;display:flex;align-items:center;justify-content:center" onclick="this.remove()"><div style="background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:24px;min-width:400px" onclick="event.stopPropagation()"><h3 style="margin:0 0 16px;color:#00d4ff">💽 Disk Benchmark Results</h3><table style="width:100%;border-collapse:collapse">';
    h+='<tr style="color:#888"><td>Test</td><td style="text-align:right">Write MB/s</td><td style="text-align:right">Read MB/s</td></tr>';
    d.results.forEach(r=>{h+='<tr style="border-top:1px solid #333"><td style="color:#eee;padding:6px 0">'+r.label+'</td><td style="text-align:right;color:#ff6b6b;padding:6px 0">'+r.write_mb+'</td><td style="text-align:right;color:#48dbfb;padding:6px 0">'+r.read_mb+'</td></tr>';});
    h+='</table><p style="color:#666;font-size:12px;margin:12px 0 0">Click outside to close</p></div></div>';
    document.body.insertAdjacentHTML('beforeend',h);
   } else if(d.running){bb.textContent='⏳ '+d.results.length+'/4...';}
  });
 },1500);
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

# ═══════════════════════════ Stress Manager ═════════════════════════════

class StressManager:
    def __init__(self, sys_info):
        self.sys_info = sys_info
        self.workers = {}
        self.stop_events = {}
        self.active = set()
        self._lock = threading.Lock()
        self._timer = None

    def start_test(self, name):
        with self._lock:
            if name in self.active: return
            ev = mp.Event()
            self.stop_events[name] = ev
            procs = []
            intel = self.sys_info["arch"] == "intel"
            if name == "cpu":
                for i in range(self.sys_info["cores"]):
                    p = mp.Process(target=cpu_stress_worker, args=(ev, i, intel), daemon=True)
                    p.start(); procs.append(p)
            elif name == "gpu":
                p = mp.Process(target=gpu_stress_worker, args=(ev, self.sys_info), daemon=True)
                p.start(); procs.append(p)
            elif name == "memory":
                p = mp.Process(target=memory_stress_worker, args=(ev, self.sys_info["ram_gb"] * 0.7), daemon=True)
                p.start(); procs.append(p)
            elif name == "disk":
                for i in range(4):
                    p = mp.Process(target=disk_stress_worker, args=(ev, i), daemon=True)
                    p.start(); procs.append(p)
            self.workers[name] = procs
            self.active.add(name)

    def stop_test(self, name):
        with self._lock:
            if name not in self.active: return
            ev = self.stop_events.get(name)
            if ev: ev.set()
            for p in self.workers.get(name, []):
                p.join(timeout=2)
                if p.is_alive():
                    try: p.kill(); p.join(timeout=1)
                    except: pass
                if p.is_alive():
                    try: os.kill(p.pid, signal.SIGKILL)
                    except: pass
            self.active.discard(name)
            self.workers.pop(name, None)
            self.stop_events.pop(name, None)

    def toggle(self, name):
        if name in self.active: self.stop_test(name)
        else: self.start_test(name)

    def stop_all(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        for n in list(self.active): self.stop_test(n)
        try:
            subprocess.run("pkill -9 -f 'cpu_stress_worker|gpu_stress_worker|memory_stress_worker|disk_stress_worker' 2>/dev/null",
                          shell=True, capture_output=True, timeout=3)
        except: pass

    def start_all(self, duration=600):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        for n in ["cpu", "gpu", "memory", "disk"]: self.start_test(n)
        if duration and duration > 0:
            self._timer = threading.Timer(duration, self._auto_stop)
            self._timer.daemon = True
            self._timer.start()

    def _auto_stop(self):
        print(f"  ⏰ Timer expired — stopping all stress tests")
        self.stop_all()

    def get_active(self):
        with self._lock: return list(self.active)

# ═══════════════════════════ Web Server ═════════════════════════════════

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

_mc = None
_sm = None
_si = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._ok("text/html", DASHBOARD_HTML.encode())
        elif self.path == "/events":
            self.send_response(200)
            for k, v in [("Content-Type","text/event-stream"),("Cache-Control","no-cache"),
                         ("Connection","keep-alive"),("Access-Control-Allow-Origin","*")]:
                self.send_header(k, v)
            self.end_headers()
            self._send_event(json.dumps({"sys_info": _si, "active": _sm.get_active()}))
            try:
                while True:
                    self._send_event(json.dumps({
                        "metrics": _mc.get_snapshot(), "active": _sm.get_active(), "sys_info": _si
                    }))
                    time.sleep(0.5)
            except (BrokenPipeError, ConnectionResetError, OSError): pass
        elif self.path == "/api/status":
            self._ok("application/json", json.dumps({"metrics": _mc.get_snapshot(), "active": _sm.get_active(), "sys_info": _si}).encode())
        elif self.path == "/api/disk_bench_result":
            self._ok("application/json", json.dumps({
                "running": _disk_bench_running,
                "results": _disk_bench_results
            }).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/toggle?"):
            t = self.path.split("test=")[-1].split("&")[0]
            if t in ("cpu","gpu","memory","disk"):
                threading.Thread(target=_sm.toggle, args=(t,), daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path.startswith("/api/toggle_all"):
            on = "on=1" in self.path
            dur = 600
            try:
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                dur = int(params.get('dur', ['600'])[0])
            except: pass
            if on:
                threading.Thread(target=_sm.start_all, args=(dur,), daemon=True).start()
            else:
                threading.Thread(target=_sm.stop_all, daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path == "/api/disk_bench":
            if _disk_bench_running:
                self._ok("application/json", json.dumps({"error": "Benchmark already running"}).encode())
            else:
                threading.Thread(target=_run_disk_benchmark, daemon=True).start()
                self._ok("application/json", json.dumps({"ok": True, "status": "started"}).encode())
        else:
            self.send_error(404)

    def _ok(self, ct, body):
        self.send_response(200); self.send_header("Content-Type", ct); self.end_headers(); self.wfile.write(body)

    def _send_event(self, data):
        self.wfile.write(f"data: {data}\n\n".encode()); self.wfile.flush()

# ═══════════════════════ Native macOS App (PyObjC) ══════════════════════

def run_native_app(port):
    """Run native macOS app with menu bar monitor + WKWebView dashboard."""
    import objc
    from AppKit import (
        NSApplication, NSApp, NSObject, NSStatusBar, NSVariableStatusItemLength,
        NSMenu, NSMenuItem, NSFont, NSAttributedString, NSImage,
        NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
        NSBackingStoreBuffered, NSApplicationActivationPolicyAccessory,
    )
    from Foundation import NSTimer, NSRunLoop, NSDefaultRunLoopMode, NSURL, NSURLRequest, NSDictionary, NSMakeRect
    import WebKit

    url = f"http://localhost:{port}"

    class AppDelegate(NSObject):
        _window = None
        _webview = None
        _status_item = None
        _timer = None

        def applicationDidFinishLaunching_(self, notification):
            # Set as accessory app (menu bar only, no dock icon)
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

            # ── Menu bar status item ──
            self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
            self._status_item.setTitle_("⚡ MacStress")

            # Menu
            menu = NSMenu.alloc().init()
            open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Open Dashboard", "openDashboard:", "d")
            open_item.setTarget_(self)
            menu.addItem_(open_item)

            menu.addItem_(NSMenuItem.separatorItem())

            start_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Start All Stress Tests", "startAll:", "s")
            start_item.setTarget_(self)
            menu.addItem_(start_item)

            stop_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Stop All Stress Tests", "stopAll:", "x")
            stop_item.setTarget_(self)
            menu.addItem_(stop_item)

            menu.addItem_(NSMenuItem.separatorItem())

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit MacStress", "quit:", "q")
            quit_item.setTarget_(self)
            menu.addItem_(quit_item)

            self._status_item.setMenu_(menu)

            # ── Timer for menu bar updates ──
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "updateMenuBar:", None, True
            )
            NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSDefaultRunLoopMode)

            # Auto-open dashboard
            self.openDashboard_(None)

        def updateMenuBar_(self, timer):
            """Update menu bar with live CPU / RAM / Temp / Power stats."""
            try:
                snap = _mc.get_snapshot()
                cpu = snap.get("cpu_usage", 0)
                mem = snap.get("mem_used_pct", 0)
                ct = snap.get("cpu_temp")
                pw = snap.get("total_power_w")

                # Build compact status: CPU% · RAM% · Temp · Power
                parts = [f"CPU {cpu:.0f}%", f"RAM {mem:.0f}%"]
                if ct is not None:
                    parts.append(f"{ct:.0f}°C")
                if pw is not None:
                    parts.append(f"{pw:.1f}W")
                title = "  ".join(parts)

                font = NSFont.monospacedDigitSystemFontOfSize_weight_(12.0, 0.0)
                attrs = NSDictionary.dictionaryWithObject_forKey_(font, "NSFont")
                attr_str = NSAttributedString.alloc().initWithString_attributes_(title, attrs)
                self._status_item.setAttributedTitle_(attr_str)
            except Exception:
                pass

        def openDashboard_(self, sender):
            """Open (or focus) the native dashboard window."""
            if self._window and self._window.isVisible():
                self._window.makeKeyAndOrderFront_(None)
                NSApp.activateIgnoringOtherApps_(True)
                return

            # Create window
            style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                     NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
            rect = NSMakeRect(100, 100, 1200, 750)
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, style, NSBackingStoreBuffered, False
            )
            self._window.setTitle_("MacStress Dashboard")
            self._window.setMinSize_((800, 500))
            self._window.setReleasedWhenClosed_(False)

            # Set dark appearance
            try:
                from AppKit import NSAppearance
                dark = NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua")
                if dark:
                    self._window.setAppearance_(dark)
            except Exception:
                pass

            # WKWebView
            config = WebKit.WKWebViewConfiguration.alloc().init()
            self._webview = WebKit.WKWebView.alloc().initWithFrame_configuration_(
                rect, config
            )
            req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
            self._webview.loadRequest_(req)
            self._window.setContentView_(self._webview)
            self._window.center()
            self._window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)

        def startAll_(self, sender):
            threading.Thread(target=_sm.start_all, args=(600,), daemon=True).start()

        def stopAll_(self, sender):
            threading.Thread(target=_sm.stop_all, daemon=True).start()

        def quit_(self, sender):
            _sm.stop_all()
            _mc.stop()
            NSApp.terminate_(None)

    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


# ═══════════════════════════ Disk Benchmark ═════════════════════════════

_disk_bench_running = False
_disk_bench_results = []

def _dd_bench(label, bs, count, filepath, total_mb):
    """Run a write+read benchmark pass. Returns dict with results."""
    import time as _t
    # Write
    t0 = _t.monotonic()
    try:
        subprocess.run(["dd", "if=/dev/zero", f"of={filepath}", f"bs={bs}", f"count={count}"],
                       capture_output=True, timeout=120)
        subprocess.run(["sync"], capture_output=True, timeout=10)
    except Exception:
        pass
    t1 = _t.monotonic()
    w_dur = max(t1 - t0, 0.001)
    w_speed = int(total_mb / w_dur)

    # Read (purge cache first)
    subprocess.run(["sudo", "-n", "purge"], capture_output=True, timeout=10)
    t0 = _t.monotonic()
    try:
        subprocess.run(["dd", f"if={filepath}", "of=/dev/null", f"bs={bs}"],
                       capture_output=True, timeout=120)
    except Exception:
        pass
    t1 = _t.monotonic()
    r_dur = max(t1 - t0, 0.001)
    r_speed = int(total_mb / r_dur)

    try: os.unlink(filepath)
    except: pass
    return {"label": label, "write_mb": w_speed, "read_mb": r_speed}

def _run_disk_benchmark():
    """Run full 4-pass disk benchmark (matches macstress_lite.sh)."""
    global _disk_bench_running, _disk_bench_results
    _disk_bench_running = True
    _disk_bench_results = []
    bf = "/tmp/macstress_bench"
    passes = [
        ("Seq 1MB",   "1048576",  512,  f"{bf}_seq1m",   512),
        ("Seq 256K",  "262144",   1024, f"{bf}_seq256k", 256),
        ("Seq 64K",   "65536",    2048, f"{bf}_seq64k",  128),
        ("Rnd 4K",    "4096",     8192, f"{bf}_rnd4k",   32),
    ]
    for label, bs, count, fpath, total_mb in passes:
        r = _dd_bench(label, bs, count, fpath, total_mb)
        _disk_bench_results.append(r)
    _disk_bench_running = False

# ═══════════════════════════ Sudo Pre-Elevation ═════════════════════════

def _pre_elevate_sudo():
    """Get sudo password early via native macOS dialog.
    Returns the password string (to pipe via sudo -S), or None if not needed/failed.
    NOTE: sudo caches credentials per-TTY on macOS, so we CANNOT rely on
    sudo -v caching — we must pipe the password directly to sudo -S."""
    if os.geteuid() == 0:
        return None  # already root, no password needed
    # Check if sudo is already working without password
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5)
        if r.returncode == 0:
            print("  🔐 sudo: вже авторизовано")
            return None  # sudo works without password
    except Exception:
        pass
    # Show native macOS password dialog
    try:
        dialog_script = (
            'text returned of (display dialog '
            '"MacStress потребує пароль для моніторингу '
            'температури та споживання енергії" '
            'with title "MacStress" default answer "" with hidden answer '
            'with icon caution)'
        )
        proc = subprocess.run(
            ["osascript", "-e", dialog_script],
            capture_output=True, text=True, timeout=120
        )
        if proc.returncode == 0 and proc.stdout.strip():
            pw = proc.stdout.strip()
            # Verify the password is correct
            sv = subprocess.run(
                ["sudo", "-S", "-v"],
                input=pw + "\n", capture_output=True, text=True, timeout=10
            )
            if sv.returncode == 0:
                print("  🔐 sudo: авторизовано через діалог")
                return pw  # Return password for piping to sudo -S
            else:
                print("  ❌ sudo: невірний пароль")
                del pw
    except Exception as e:
        print(f"  ⚠️  sudo dialog: {e}")
    print("  ⚠️  Дані температури/енергії можуть бути недоступні")
    return None

# ═══════════════════════════ Update Check ═══════════════════════════════

def _ver_tuple(v):
    """Parse version string to tuple for comparison: '1.3.0' -> (1, 3, 0)."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)

def check_for_updates(silent=False):
    """Check GitHub for newer version. Returns (has_update, latest_ver) or None."""
    try:
        import urllib.request
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "MacStress"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            if latest and _ver_tuple(latest) > _ver_tuple(VERSION):
                print(f"\n  🆕 Нова версія доступна: v{latest} (поточна: v{VERSION})")
                print(f"  📥 https://github.com/{GITHUB_REPO}/releases/latest")
                return True, latest
            elif not silent:
                print(f"  ✅ Актуальна версія: v{VERSION}")
            return False, VERSION
    except Exception:
        if not silent:
            print("  ⚠️  Не вдалося перевірити оновлення")
        return None, VERSION


# ═══════════════════════════ App Launcher ═══════════════════════════════

def create_app_launcher(app_type="full"):
    """Create .app bundle in ~/Applications for easy launching."""
    apps_dir = Path.home() / "Applications"
    apps_dir.mkdir(exist_ok=True)

    if app_type == "full":
        app_name = "MacStress"
        # Find the Python that runs this script
        python_path = sys.executable
        script_path = os.path.abspath(__file__)
        launch_cmd = f'exec "{python_path}" "{script_path}" "$@"'
    else:
        app_name = "MacStress Lite"
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macstress_lite.sh")
        launch_cmd = f'exec bash "{script_path}"'

    app_path = apps_dir / f"{app_name}.app"
    contents = app_path / "Contents"
    macos = contents / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)

    # Launcher script
    launcher = macos / app_name.replace(" ", "")
    launcher.write_text(f"""#!/bin/bash
# {app_name} Launcher — auto-generated by MacStress v{VERSION}
# Opens Terminal with the app running

if [ -x /usr/bin/open ]; then
    # Open in Terminal.app
    osascript -e 'tell app "Terminal" to do script "{launch_cmd.replace(chr(34), chr(92)+chr(34))}"' \
        -e 'tell app "Terminal" to activate'
else
    {launch_cmd}
fi
""")
    launcher.chmod(0o755)

    # Copy icon if available
    resources = contents / "Resources"
    resources.mkdir(exist_ok=True)
    icon_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "icons"
    icon_name = "macstress" if app_type == "full" else "macstress_lite"
    icon_src = icon_dir / f"{icon_name}.icns"
    icon_ref = ""
    if icon_src.exists():
        shutil.copy2(str(icon_src), str(resources / f"{icon_name}.icns"))
        icon_ref = f"\n    <key>CFBundleIconFile</key>\n    <string>{icon_name}</string>"

    # Info.plist
    plist = contents / "Info.plist"
    bundle_id = f"com.macstress.{app_name.lower().replace(' ', '')}"
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{app_name.replace(' ', '')}</string>
    <key>CFBundleIdentifier</key>
    <string>{bundle_id}</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleVersion</key>
    <string>{VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>{VERSION}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>{icon_ref}
</dict>
</plist>
""")
    # Force Finder to refresh icon cache on reinstall
    subprocess.run(["touch", str(app_path)], capture_output=True)
    subprocess.run([
        "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister",
        "-f", str(app_path)
    ], capture_output=True)

    print(f"  ✅ {app_name}.app створено в ~/Applications/")
    print(f"  📂 {app_path}")
    return str(app_path)


# ═══════════════════════════ Main ═══════════════════════════════════════

def main():
    global _mc, _sm, _si

    # Handle CLI flags
    if "--install-app" in sys.argv:
        create_app_launcher("full")
        return
    if "--install-lite-app" in sys.argv:
        create_app_launcher("lite")
        return
    if "--check-update" in sys.argv:
        check_for_updates()
        return
    if "--version" in sys.argv:
        print(f"MacStress v{VERSION}")
        return

    print("\n" + "="*60)
    print(f"  ⚡ MacStress v{VERSION} — Native macOS Stress Test + Monitor")
    print("="*60)

    _si = detect_system()
    _si["has_sudo"] = os.geteuid() == 0
    print(f"\n  🖥  {_si['model_name']}  ({_si['model_id']})")
    print(f"  🧠 {_si['cpu']}  ·  {_si['cores']} cores ({_si['perf_cores']}P+{_si['eff_cores']}E)")
    print(f"  🎮 {_si['gpu']}")
    print(f"  💾 {_si['ram_gb']} GB  ·  {_si['arch'].upper()}")
    print(f"  💿 {_si['os']}")

    # Check for updates in background
    threading.Thread(target=check_for_updates, args=(True,), daemon=True).start()

    # Pre-elevate sudo for powermetrics (before NSApp takes over the process)
    _sudo_pw = _pre_elevate_sudo()
    _si["has_sudo"] = os.geteuid() == 0 or _sudo_pw is not None

    _mc = MetricsCollector(_si)
    if _sudo_pw:
        _mc._sudo_pw = _sudo_pw  # Pass password for piping to sudo -S
        del _sudo_pw
    _sm = StressManager(_si)
    _mc.start()

    port = 9630
    subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", shell=True, capture_output=True)
    time.sleep(0.3)

    server = ThreadedHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except: pass

    print(f"\n  🌐 http://localhost:{port}")
    print(f"  📱 http://{ip}:{port}")

    # Decide: native app or browser fallback
    use_native = True
    try:
        import objc
        from AppKit import NSApplication
        import WebKit
    except ImportError:
        use_native = False
        print("\n  ⚠️  PyObjC not installed — falling back to browser mode")
        print("  Install: pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit")

    if use_native:
        print("\n  🚀 Starting native macOS app...")
        print("  📊 Menu bar: CPU / RAM / SSD live stats")
        print("="*60 + "\n")

        # Signal handling for native app
        def sig_handler(sig, frame):
            _sm.stop_all()
            _mc.stop()
            server.shutdown()
            print("\n  ✅ Done. Goodbye!")
            os._exit(0)

        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

        # Run native app (blocks on NSApp.run())
        run_native_app(port)
    else:
        import webbrowser
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        print("\n  ⏳ Dashboard ready — start stress tests from the UI")
        print("="*60 + "\n")

        def cleanup(sig=None, frame=None):
            print("\n  🛑 Stopping...")
            _sm.stop_all()
            _mc.stop()
            server.shutdown()
            print("  ✅ Done. Goodbye!\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cleanup()


if __name__ == "__main__":
    mp.set_start_method("fork", force=True)
    main()
