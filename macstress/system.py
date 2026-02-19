"""System detection and temperature sensor compilation."""

import os, platform, subprocess, hashlib, tempfile
import multiprocessing as mp
from pathlib import Path


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
