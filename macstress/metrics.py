"""MetricsCollector — system metrics gathering threads."""

import os, re, time, subprocess, threading
from collections import deque
from .system import compile_temp_sensor


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
        # Extended detailed metrics for popover
        self._details = {
            "top_cpu": [],      # [{name, cpu_pct}]
            "top_mem": [],      # [{name, mem_mb}]
            "uptime_sec": 0,
            "disk_free_gb": 0,
            "disk_total_gb": 0,
            "cpu_sys_pct": 0,
            "cpu_user_pct": 0,
            "cpu_idle_pct": 0,
            "load_avg": [0, 0, 0],
            "battery_pct": None,
            "battery_charging": False,
            "smart_status": None,
            "smart_model": None,
            "smart_capacity": None,
            "smart_trim": None,
            "smart_serial": None,
        }
        self._smart_counter = 0  # collect SMART every 6th cycle (30s)

    def start(self):
        threading.Thread(target=self._collect_loop, daemon=True).start()
        if self.sys_info["arch"] == "apple_silicon":
            ts_bin = compile_temp_sensor()
            if ts_bin:
                threading.Thread(target=self._sensor_loop, args=(ts_bin,), daemon=True).start()
        threading.Thread(target=self._powermetrics_loop, daemon=True).start()
        threading.Thread(target=self._detail_loop, daemon=True).start()

    def stop(self):
        self._stop.set()
        for p in [self._pm_proc, self._ts_proc]:
            if p:
                try: p.kill()
                except Exception: pass

    def get_snapshot(self):
        with self._lock:
            return dict(self.data)

    def get_details(self):
        with self._lock:
            return dict(self._details)

    def _collect_loop(self):
        cores = self.sys_info.get("cores", 1) or 1
        while not self._stop.is_set():
            try:
                cpu_total = 0.0
                try:
                    cpu_raw = subprocess.getoutput(
                        "ps -A -o %cpu | awk 'NR>1{s+=$1} END {printf \"%.1f\", s}'"
                    )
                    cpu_total = min(round(float(cpu_raw.strip()) / cores, 1), 100.0)
                except (ValueError, ZeroDivisionError):
                    pass

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
                        "cpu_usage": min(cpu_total, 100.0),
                        "mem_used_pct": round(mem_pct, 1),
                        "mem_used_gb": round(used_gb, 1), "swap_used_gb": round(swap_used, 2),
                        "swap_total_gb": round(swap_total, 2),
                        "disk_read_mb": round(disk_r, 2), "disk_write_mb": round(disk_w, 2),
                        "timestamp": time.time(),
                    })
                    self._history.append(dict(self.data))
            except Exception: pass
            self._stop.wait(2.0)

    def _detail_loop(self):
        """Collect extended metrics for popover (runs every 5s)."""
        cores = self.sys_info.get("cores", 1) or 1
        while not self._stop.is_set():
            try:
                # Top CPU processes (normalized per core)
                try:
                    raw = subprocess.getoutput("ps -eo pcpu,comm -r | head -8 | tail -7")
                    top_cpu = []
                    for line in raw.strip().split("\n"):
                        parts = line.strip().split(None, 1)
                        if len(parts) == 2:
                            try:
                                pct = float(parts[0])
                                name = parts[1].split("/")[-1][:25]
                                if pct > 0.1:
                                    # Normalize per-core % to system-wide %
                                    norm_pct = round(pct / cores * 100, 1) / 100 * cores
                                    # Show as fraction of total CPU capacity
                                    display_pct = round(pct / cores, 1)
                                    top_cpu.append({"name": name, "cpu_pct": display_pct})
                            except ValueError: pass
                    with self._lock:
                        self._details["top_cpu"] = top_cpu[:7]
                except Exception: pass

                # Top Memory processes
                try:
                    raw = subprocess.getoutput("ps -eo rss,comm -m | head -8 | tail -7")
                    top_mem = []
                    for line in raw.strip().split("\n"):
                        parts = line.strip().split(None, 1)
                        if len(parts) == 2:
                            try:
                                rss_kb = int(parts[0])
                                name = parts[1].split("/")[-1][:25]
                                mb = round(rss_kb / 1024, 1)
                                if mb > 10:
                                    top_mem.append({"name": name, "mem_mb": mb})
                            except ValueError: pass
                    with self._lock:
                        self._details["top_mem"] = top_mem[:7]
                except Exception: pass

                # Uptime
                try:
                    raw = subprocess.getoutput("sysctl -n kern.boottime")
                    m = re.search(r'sec\s*=\s*(\d+)', raw)
                    if m:
                        boot_sec = int(m.group(1))
                        with self._lock:
                            self._details["uptime_sec"] = int(time.time() - boot_sec)
                except Exception: pass

                # Disk free space
                try:
                    raw = subprocess.getoutput("df -g / | tail -1")
                    parts = raw.split()
                    if len(parts) >= 4:
                        total = int(parts[1])
                        avail = int(parts[3])
                        with self._lock:
                            self._details["disk_total_gb"] = total
                            self._details["disk_free_gb"] = avail
                except Exception: pass

                # CPU breakdown (sys/user/idle)
                try:
                    raw = subprocess.getoutput("top -l 1 -s 0 -n 0 2>/dev/null | grep 'CPU usage'")
                    if raw:
                        user_m = re.search(r'([\d.]+)%\s*user', raw)
                        sys_m = re.search(r'([\d.]+)%\s*sys', raw)
                        idle_m = re.search(r'([\d.]+)%\s*idle', raw)
                        with self._lock:
                            if user_m: self._details["cpu_user_pct"] = float(user_m.group(1))
                            if sys_m: self._details["cpu_sys_pct"] = float(sys_m.group(1))
                            if idle_m: self._details["cpu_idle_pct"] = float(idle_m.group(1))
                except Exception: pass

                # Load average
                try:
                    raw = subprocess.getoutput("sysctl -n vm.loadavg")
                    parts = raw.strip("{ }").split()
                    if len(parts) >= 3:
                        with self._lock:
                            self._details["load_avg"] = [float(parts[0]), float(parts[1]), float(parts[2])]
                except Exception: pass

                # Battery
                try:
                    raw = subprocess.getoutput("pmset -g batt")
                    pct_m = re.search(r'(\d+)%', raw)
                    if pct_m:
                        with self._lock:
                            self._details["battery_pct"] = int(pct_m.group(1))
                            self._details["battery_charging"] = "charging" in raw.lower() and "not charging" not in raw.lower()
                except Exception: pass

                # SMART data (every 30s — 6th cycle)
                self._smart_counter += 1
                if self._smart_counter >= 6:
                    self._smart_counter = 0
                    try:
                        raw = subprocess.getoutput("system_profiler SPNVMeDataType 2>/dev/null")
                        if raw:
                            model_m = re.search(r'Model:\s*(.+)', raw)
                            cap_m = re.search(r'Capacity:\s*(.+?)\s*\(', raw)
                            smart_m = re.search(r'S\.M\.A\.R\.T\.\s*status:\s*(\S+)', raw, re.IGNORECASE)
                            trim_m = re.search(r'TRIM\s+Support:\s*(\S+)', raw)
                            serial_m = re.search(r'Serial\s+Number:\s*(\S+)', raw)
                            with self._lock:
                                if model_m: self._details["smart_model"] = model_m.group(1).strip()
                                if cap_m: self._details["smart_capacity"] = cap_m.group(1).strip()
                                if smart_m: self._details["smart_status"] = smart_m.group(1).strip()
                                if trim_m: self._details["smart_trim"] = trim_m.group(1).strip()
                                if serial_m: self._details["smart_serial"] = serial_m.group(1).strip()
                    except Exception: pass

            except Exception: pass
            self._stop.wait(5.0)

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
        samplers = "smc,cpu_power,gpu_power" if self.sys_info["arch"] == "intel" else "cpu_power,gpu_power"
        pm_cmd = f"powermetrics --samplers {samplers} -i 1000 -n 1"

        def _run_once_as_root(pw=None):
            if os.geteuid() == 0:
                r = subprocess.run(["powermetrics", "--samplers", samplers, "-i", "1000", "-n", "1"],
                                   capture_output=True, text=True, timeout=15)
                return r.stdout if r.returncode == 0 else None

            r = subprocess.run(["sudo", "-n", "powermetrics", "--samplers", samplers, "-i", "1000", "-n", "1"],
                               capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout

            if pw:
                safe_pw = pw.replace('"', '\\"').replace("'", "\\'")
                script = f'do shell script "{pm_cmd}" with administrator privileges password "{safe_pw}"'
                r = subprocess.run(["osascript", "-e", script],
                                   capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    return r.stdout
                print(f"  ❌ powermetrics via osascript failed: {r.stderr.strip()}")
            return None

        pw = getattr(self, '_sudo_pw', None)
        self._sudo_pw = None

        while not self._stop.is_set():
            try:
                out = _run_once_as_root(pw)
                if out:
                    self._parse_pm(out)
                    pw = None
                else:
                    if pw is None and os.geteuid() != 0:
                        break
            except Exception as e:
                print(f"  ⚠️  powermetrics: {e}")
            self._stop.wait(2.0)

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
