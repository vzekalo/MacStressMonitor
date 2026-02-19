"""StressManager — thread-safe test orchestrator."""

import os, signal, threading, subprocess
import multiprocessing as mp
from .stress import cpu_stress_worker, gpu_stress_worker, memory_stress_worker, disk_stress_worker


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
                # Reserve 2 cores for GUI/system responsiveness
                stress_cores = max(1, self.sys_info["cores"] - 2)
                for i in range(stress_cores):
                    p = mp.Process(target=cpu_stress_worker, args=(ev, i, intel), daemon=True)
                    p.start(); procs.append(p)
            elif name == "gpu":
                p = mp.Process(target=gpu_stress_worker, args=(ev, self.sys_info), daemon=True)
                p.start(); procs.append(p)
            elif name == "memory":
                p = mp.Process(target=memory_stress_worker, args=(ev, self.sys_info["ram_gb"] * 0.55), daemon=True)
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
