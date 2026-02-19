"""Stress test worker functions."""

import os, math, struct, random, hashlib, mmap, time, shutil, subprocess, tempfile


def cpu_stress_worker(stop_event, core_id, is_intel):
    x = 1.0000001
    if is_intel:
        while not stop_event.is_set():
            for _ in range(200000):
                x = math.sin(x) * math.cos(x) + math.sqrt(abs(x) + 1)
                x = math.tan(x + 0.0001) * math.log(abs(x) + 1)
                x = (x * 1.0000001) + hashlib.md5(struct.pack('d', x)).digest()[0] * 1e-7
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
                time.sleep(0.2)
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
