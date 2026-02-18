#!/bin/bash
# ⚡ MacStress Lite — Pure Bash, Zero Dependencies
# Works on ANY Mac without Python, Xcode, or anything else

# ── Colors ────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; B='\033[0;34m'
C='\033[0;36m'; W='\033[1;37m'; D='\033[0;90m'; N='\033[0m'; BOLD='\033[1m'

# ── System Info ───────────────────────────────────────────
MODEL=$(sysctl -n hw.model 2>/dev/null)
CPU_BRAND=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null || echo "?")
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
ARCH=$(uname -m)

clear
echo ""
echo -e "  ${Y}⚡${N} ${BOLD}MacStress Lite${N} ${D}— Pure Bash Monitor + Stress${N}"
echo -e "  ${D}──────────────────────────────────────────────${N}"
echo -e "  ${C}Model:${N}  $MODEL    ${C}CPU:${N} $CPU_BRAND"
echo -e "  ${C}Cores:${N}  $CORES  ·  ${C}RAM:${N} ${RAM_GB} GB  ·  ${C}macOS:${N} $OS_VER ($ARCH)"
echo -e "  ${D}──────────────────────────────────────────────${N}"

# ── Stress test state ─────────────────────────────────────
STRESS_PIDS=()
STRESS_TYPE=""
STRESS_DURATION=0
STRESS_START=0

stop_stress() {
    for pid in "${STRESS_PIDS[@]}"; do
        kill $pid 2>/dev/null
        wait $pid 2>/dev/null
    done
    STRESS_PIDS=()
    STRESS_TYPE=""
    # Clean temp files
    rm -f /tmp/macstress_mem_* /tmp/macstress_disk_* 2>/dev/null
}

cleanup() {
    stop_stress
    tput cnorm 2>/dev/null
    echo ""; echo -e "  ${G}✅ Done. Goodbye!${N}"; echo ""
    exit 0
}
trap cleanup EXIT INT TERM

# ── CPU Stress: saturate all cores ────────────────────────
stress_cpu() {
    local dur=${1:-60}
    stop_stress
    STRESS_TYPE="CPU"; STRESS_DURATION=$dur; STRESS_START=$(date +%s)
    echo -e "\n  ${R}🔥 CPU Stress: $CORES потоків на ${dur}с${N}"
    for ((i=0; i<CORES; i++)); do
        (while true; do :; done) &
        STRESS_PIDS+=($!)
    done
    # Auto-stop timer
    (sleep $dur; for p in "${STRESS_PIDS[@]}"; do kill $p 2>/dev/null; done) &
    STRESS_PIDS+=($!)
}

# ── Memory Stress: allocate RAM in chunks ─────────────────
stress_mem() {
    local mb=${1:-1024}
    local dur=${2:-60}
    stop_stress
    STRESS_TYPE="RAM ${mb}MB"; STRESS_DURATION=$dur; STRESS_START=$(date +%s)
    echo -e "\n  ${R}🔥 Memory Stress: ${mb} MB на ${dur}с${N}"
    (
        # Allocate memory by creating large files in RAM (tmpfs-like via /tmp)
        local chunk=64  # 64MB chunks
        local count=$((mb / chunk))
        for ((i=0; i<count; i++)); do
            dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=$chunk 2>/dev/null &
        done
        wait
        # Hold memory by reading files
        while true; do
            for ((i=0; i<count; i++)); do
                cat /tmp/macstress_mem_$i > /dev/null 2>/dev/null
            done
            sleep 1
        done
    ) &
    STRESS_PIDS+=($!)
    (sleep $dur; kill ${STRESS_PIDS[-1]} 2>/dev/null; rm -f /tmp/macstress_mem_* 2>/dev/null) &
    STRESS_PIDS+=($!)
}

# ── Disk Stress: sequential read/write ────────────────────
stress_disk() {
    local dur=${1:-60}
    stop_stress
    STRESS_TYPE="DISK"; STRESS_DURATION=$dur; STRESS_START=$(date +%s)
    echo -e "\n  ${R}🔥 Disk Stress: read/write на ${dur}с${N}"
    (
        while true; do
            dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=256 2>/dev/null
            dd if=/tmp/macstress_disk_w of=/dev/null bs=1m 2>/dev/null
            rm -f /tmp/macstress_disk_w 2>/dev/null
        done
    ) &
    STRESS_PIDS+=($!)
    (sleep $dur; kill ${STRESS_PIDS[-1]} 2>/dev/null; rm -f /tmp/macstress_disk_* 2>/dev/null) &
    STRESS_PIDS+=($!)
}

# ── All Stress: CPU + RAM + Disk ──────────────────────────
stress_all() {
    local dur=${1:-120}
    stop_stress
    STRESS_TYPE="ALL"; STRESS_DURATION=$dur; STRESS_START=$(date +%s)
    echo -e "\n  ${R}🔥 FULL STRESS: CPU + RAM + Disk на ${dur}с${N}"

    # CPU
    for ((i=0; i<CORES; i++)); do
        (while true; do :; done) &
        STRESS_PIDS+=($!)
    done

    # RAM (512MB)
    (
        for ((i=0; i<8; i++)); do
            dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=64 2>/dev/null
        done
        while true; do
            for ((i=0; i<8; i++)); do cat /tmp/macstress_mem_$i > /dev/null 2>/dev/null; done
            sleep 1
        done
    ) &
    STRESS_PIDS+=($!)

    # Disk
    (while true; do
        dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=128 2>/dev/null
        dd if=/tmp/macstress_disk_w of=/dev/null bs=1m 2>/dev/null
        rm -f /tmp/macstress_disk_w 2>/dev/null
    done) &
    STRESS_PIDS+=($!)

    # Timer
    (sleep $dur; for p in "${STRESS_PIDS[@]}"; do kill $p 2>/dev/null; done; rm -f /tmp/macstress_* 2>/dev/null) &
    STRESS_PIDS+=($!)
}

# ── Parse vm_stat ─────────────────────────────────────────
parse_vm() {
    local data=$(vm_stat 2>/dev/null)
    local ps=16384
    [[ "$ARCH" == "x86_64" ]] && ps=4096
    local active=$(echo "$data" | awk '/Pages active/ {gsub(/\./,"",$NF); print $NF}')
    local wired=$(echo "$data" | awk '/Pages wired/ {gsub(/\./,"",$NF); print $NF}')
    local compressed=$(echo "$data" | awk '/occupied by compressor/ {gsub(/\./,"",$NF); print $NF}')
    active=${active:-0}; wired=${wired:-0}; compressed=${compressed:-0}
    local used_bytes=$(( (active + wired + compressed) * ps ))
    echo "scale=1; $used_bytes / 1073741824" | bc 2>/dev/null
}

# ── Menu ──────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Стрес-тести:${N}"
echo -e "    ${Y}1${N} CPU (всі ядра)   ${Y}2${N} RAM (1GB)   ${Y}3${N} Disk (r/w)"
echo -e "    ${Y}4${N} ALL (CPU+RAM+Disk)              ${Y}x${N} Зупинити"
echo -e "    ${Y}q${N} Вихід"
echo -e "  ${D}──────────────────────────────────────────────${N}"

# ── Main Loop ─────────────────────────────────────────────
tput civis 2>/dev/null
LINES_UP=6

while true; do
    # CPU
    CPU_RAW=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    CPU_PCT=$(echo "scale=1; $CPU_RAW / $CORES" | bc 2>/dev/null || echo "$CPU_RAW")
    CPU_INT=${CPU_PCT%.*}; [[ ${CPU_INT:-0} -gt 100 ]] && CPU_PCT="100.0" && CPU_INT=100

    # RAM
    MEM_USED=$(parse_vm)
    MEM_PCT=$(echo "scale=1; $MEM_USED * 100 / $RAM_GB" | bc 2>/dev/null || echo "0")
    MEM_INT=${MEM_PCT%.*}

    # Swap
    SWAP_USED=$(sysctl vm.swapusage 2>/dev/null | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    SWAP_USED=${SWAP_USED:-0}

    # Load
    LOAD=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')

    # Disk I/O
    DISK_IO=$(iostat -d -c 2 2>/dev/null | tail -1 | awk '{printf "R:%.1f W:%.1f MB/s", $2/1024, $3/1024}')

    # Battery
    BATT=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)

    # Stress timer
    STRESS_INFO=""
    if [[ -n "$STRESS_TYPE" && ${#STRESS_PIDS[@]} -gt 0 ]]; then
        local_now=$(date +%s)
        elapsed=$((local_now - STRESS_START))
        remain=$((STRESS_DURATION - elapsed))
        if [[ $remain -le 0 ]]; then
            stop_stress
        else
            STRESS_INFO="${R}🔥 ${STRESS_TYPE} — ${remain}с${N}"
        fi
    fi

    # Bars
    CPU_BAR_LEN=$((CPU_INT * 40 / 100)); [[ $CPU_BAR_LEN -lt 1 ]] && CPU_BAR_LEN=1
    MEM_BAR_LEN=$((MEM_INT * 40 / 100)); [[ $MEM_BAR_LEN -lt 1 ]] && MEM_BAR_LEN=1
    CPU_BAR=$(printf '█%.0s' $(seq 1 $CPU_BAR_LEN)); CPU_COLOR=$G; [[ $CPU_INT -gt 50 ]] && CPU_COLOR=$Y; [[ $CPU_INT -gt 80 ]] && CPU_COLOR=$R
    MEM_BAR=$(printf '█%.0s' $(seq 1 $MEM_BAR_LEN)); MEM_COLOR=$G; [[ $MEM_INT -gt 60 ]] && MEM_COLOR=$Y; [[ $MEM_INT -gt 85 ]] && MEM_COLOR=$R

    # Render
    echo -ne "\033[${LINES_UP}A"
    printf "  ${W}CPU${N}  %5s%%  ${CPU_COLOR}%-40s${N}\n" "$CPU_PCT" "$CPU_BAR"
    printf "  ${W}RAM${N}  %5s%%  ${MEM_COLOR}%-40s${N}  ${D}${MEM_USED}/${RAM_GB} GB${N}\n" "$MEM_PCT" "$MEM_BAR"
    printf "  ${W}Swap${N} %5s MB  ${D}Load: ${LOAD}${N}                              \n" "$SWAP_USED"
    printf "  ${W}Disk${N} %-30s ${D}Batt: ${BATT:-n/a}${N}       \n" "$DISK_IO"
    printf "  %-60s\n" "$STRESS_INFO"
    printf "  ${D}──────────────────────────────────────────────${N}\n"

    read -t 2 -n 1 key 2>/dev/null
    case "$key" in
        1) tput cnorm; stress_cpu 120; tput civis ;;
        2) tput cnorm; stress_mem 1024 120; tput civis ;;
        3) tput cnorm; stress_disk 120; tput civis ;;
        4) tput cnorm; stress_all 180; tput civis ;;
        x|X) stop_stress; echo -e "\n  ${G}✅ Зупинено${N}" ;;
        q|Q) exit 0 ;;
    esac
done
