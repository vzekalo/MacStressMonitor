"""Disk benchmark — 4-pass dd-based test."""

import os, subprocess


_disk_bench_running = False
_disk_bench_results = []


def _dd_bench(label, bs, count, filepath, total_mb):
    """Run a write+read benchmark pass. Returns dict with results."""
    import time as _t
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


def run_disk_benchmark():
    """Run full 4-pass disk benchmark."""
    global _disk_bench_running, _disk_bench_results
    _disk_bench_running = True
    _disk_bench_results = []
    bf = "/tmp/macstress_bench"
    passes = [
        ("Seq 1MB",   "1048576",  512,  f"{bf}_seq1m",   512),
        ("Seq 256K",  "262144",   1024, f"{bf}_seq256k", 256),
        ("Seq 64K",   "65536",    2048, f"{bf}_seq64k",  128),
        ("Rnd 4K",    "4096",     16384, f"{bf}_rnd4k",  64),
    ]
    for label, bs, count, fpath, total_mb in passes:
        r = _dd_bench(label, bs, count, fpath, total_mb)
        _disk_bench_results.append(r)
    _disk_bench_running = False


def get_bench_status():
    return {"running": _disk_bench_running, "results": _disk_bench_results}
