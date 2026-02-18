#!/bin/bash
# ⚡ MacStress Lite — Pure Bash, Zero Dependencies

R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'
C='\033[0;36m'; W='\033[1;37m'; D='\033[0;90m'; N='\033[0m'; BOLD='\033[1m'

MODEL=$(sysctl -n hw.model 2>/dev/null)
CPU_BRAND=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null || echo "?")
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
ARCH=$(uname -m)

# ── Powermetrics background ──────────────────────────────
PM_DATA="/tmp/macstress_pm_data"
PM_PID_FILE="/tmp/macstress_pm_pid"
printf "" > "$PM_DATA"

start_powermetrics() {
    [[ "$ARCH" == "x86_64" ]] && SAMPLERS="smc,cpu_power,gpu_power" || SAMPLERS="cpu_power,gpu_power"
    (
        sudo powermetrics --samplers "$SAMPLERS" -i 3000 -n 0 2>/dev/null | while IFS= read -r line; do
            ll=$(echo "$line" | tr '[:upper:]' '[:lower:]')
            if echo "$ll" | grep -q "cpu die temperature\|cpu thermal level"; then
                val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
                [[ -n "$val" ]] && echo "cpu_temp=$val" >> "$PM_DATA"
            elif echo "$ll" | grep -q "gpu die temperature\|gpu thermal level"; then
                val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
                [[ -n "$val" ]] && echo "gpu_temp=$val" >> "$PM_DATA"
            elif echo "$ll" | grep -q "^cpu power\|^package power"; then
                val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
                [[ -n "$val" ]] && echo "cpu_power=$val" >> "$PM_DATA"
            elif echo "$ll" | grep -q "^gpu power"; then
                val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
                [[ -n "$val" ]] && echo "gpu_power=$val" >> "$PM_DATA"
            fi
            [[ $(wc -l < "$PM_DATA" 2>/dev/null) -gt 40 ]] && tail -20 "$PM_DATA" > "${PM_DATA}.tmp" && mv "${PM_DATA}.tmp" "$PM_DATA"
        done
    ) &
    echo $! > "$PM_PID_FILE"
}
get_pm() { grep "^$1=" "$PM_DATA" 2>/dev/null | tail -1 | cut -d= -f2; }

# ── Stress ────────────────────────────────────────────────
STRESS_PIDS=(); STRESS_TYPE=""; STRESS_DUR=0; STRESS_T0=0

stop_stress() {
    for p in "${STRESS_PIDS[@]}"; do kill $p 2>/dev/null; wait $p 2>/dev/null; done
    STRESS_PIDS=(); STRESS_TYPE=""
    rm -f /tmp/macstress_mem_* /tmp/macstress_disk_* 2>/dev/null
}
cleanup() {
    stop_stress
    [[ -f "$PM_PID_FILE" ]] && kill $(cat "$PM_PID_FILE") 2>/dev/null
    sudo pkill -9 powermetrics 2>/dev/null
    rm -f "$PM_DATA" "${PM_DATA}.tmp" "$PM_PID_FILE" 2>/dev/null
    tput cnorm 2>/dev/null; echo ""; echo -e "  ${G}✅ Bye!${N}"; echo ""
    exit 0
}
trap cleanup EXIT INT TERM

stress_cpu() {
    local d=${1:-120}; stop_stress; STRESS_TYPE="CPU"; STRESS_DUR=$d; STRESS_T0=$(date +%s)
    for ((i=0;i<CORES;i++)); do (while :; do :; done) &; STRESS_PIDS+=($!); done
    (sleep $d; for p in "${STRESS_PIDS[@]}"; do kill $p 2>/dev/null; done) &; STRESS_PIDS+=($!)
}
stress_mem() {
    local mb=${1:-1024} d=${2:-120}; stop_stress; STRESS_TYPE="RAM"; STRESS_DUR=$d; STRESS_T0=$(date +%s)
    (c=$((mb/64)); for ((i=0;i<c;i++)); do dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=64 2>/dev/null &; done; wait
     while :; do for ((i=0;i<c;i++)); do cat /tmp/macstress_mem_$i >/dev/null 2>/dev/null; done; sleep 1; done) &; STRESS_PIDS+=($!)
    (sleep $d; kill ${STRESS_PIDS[-1]} 2>/dev/null; rm -f /tmp/macstress_mem_*) &; STRESS_PIDS+=($!)
}
stress_disk() {
    local d=${1:-120}; stop_stress; STRESS_TYPE="DISK"; STRESS_DUR=$d; STRESS_T0=$(date +%s)
    (while :; do dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=256 2>/dev/null; dd if=/tmp/macstress_disk_w of=/dev/null bs=1m 2>/dev/null; rm -f /tmp/macstress_disk_w; done) &; STRESS_PIDS+=($!)
    (sleep $d; kill ${STRESS_PIDS[-1]} 2>/dev/null; rm -f /tmp/macstress_disk_*) &; STRESS_PIDS+=($!)
}
stress_all() {
    local d=${1:-180}; stop_stress; STRESS_TYPE="ALL"; STRESS_DUR=$d; STRESS_T0=$(date +%s)
    for ((i=0;i<CORES;i++)); do (while :; do :; done) &; STRESS_PIDS+=($!); done
    (for ((i=0;i<8;i++)); do dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=64 2>/dev/null; done
     while :; do for ((i=0;i<8;i++)); do cat /tmp/macstress_mem_$i >/dev/null 2>/dev/null; done; sleep 1; done) &; STRESS_PIDS+=($!)
    (while :; do dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=128 2>/dev/null; rm -f /tmp/macstress_disk_w; done) &; STRESS_PIDS+=($!)
    (sleep $d; for p in "${STRESS_PIDS[@]}"; do kill $p 2>/dev/null; done; rm -f /tmp/macstress_*) &; STRESS_PIDS+=($!)
}

parse_vm() {
    local d=$(vm_stat 2>/dev/null) ps=16384
    [[ "$ARCH" == "x86_64" ]] && ps=4096
    local a=$(echo "$d"|awk '/Pages active/{gsub(/\./,"",$NF);print $NF}')
    local w=$(echo "$d"|awk '/Pages wired/{gsub(/\./,"",$NF);print $NF}')
    local c=$(echo "$d"|awk '/occupied by compressor/{gsub(/\./,"",$NF);print $NF}')
    echo "scale=1; $(( (${a:-0} + ${w:-0} + ${c:-0}) * ps )) / 1073741824" | bc 2>/dev/null
}

make_bar() {
    local pct=$1 max=30 len=$((pct * max / 100))
    [[ $len -lt 0 ]] && len=0; [[ $len -gt $max ]] && len=$max
    local bar=""; for ((i=0;i<len;i++)); do bar+="█"; done
    for ((i=len;i<max;i++)); do bar+="░"; done
    echo "$bar"
}

# ── Draw static header ───────────────────────────────────
clear
tput civis 2>/dev/null

# Line 0: title
echo -e "  ${Y}⚡${N} ${BOLD}MacStress Lite${N}"
# Line 1: separator
echo -e "  ${D}══════════════════════════════════════════════════${N}"
# Line 2: model
echo -e "  ${C}Модель${N}   $MODEL"
# Line 3: CPU
echo -e "  ${C}CPU${N}      $CPU_BRAND"
# Line 4: specs
echo -e "  ${C}Ядра${N}  $CORES  ·  ${C}RAM${N}  ${RAM_GB} GB  ·  ${C}macOS${N}  $OS_VER ($ARCH)"
# Line 5: separator
echo -e "  ${D}══════════════════════════════════════════════════${N}"
# Line 6: controls header
echo -e "  ${BOLD}Керування:${N}"
# Line 7: controls
echo -e "  ${Y}[1]${N} Стрес CPU  ${Y}[2]${N} Стрес RAM  ${Y}[3]${N} Стрес Диска"
# Line 8: controls cont
echo -e "  ${Y}[4]${N} ВСЕ разом  ${Y}[x]${N} Зупинити   ${Y}[q]${N} Вийти"
# Line 9: separator
echo -e "  ${D}══════════════════════════════════════════════════${N}"
# Lines 10-16: live data (7 lines, updated in-place)
echo ""; echo ""; echo ""; echo ""; echo ""; echo ""; echo ""

LIVE_START=10  # line where live data begins

# ── Ask for powermetrics password ─────────────────────────
tput cnorm 2>/dev/null
start_powermetrics
tput civis 2>/dev/null

# ── Main Loop ─────────────────────────────────────────────
while true; do
    CPU_RAW=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    CPU_PCT=$(echo "scale=1; $CPU_RAW / $CORES" | bc 2>/dev/null || echo "0")
    CPU_INT=${CPU_PCT%.*}; [[ ${CPU_INT:-0} -gt 100 ]] && CPU_PCT="100.0" && CPU_INT=100

    MEM_USED=$(parse_vm); MEM_USED=${MEM_USED:-0}
    MEM_PCT=$(echo "scale=1; $MEM_USED * 100 / $RAM_GB" | bc 2>/dev/null || echo "0")
    MEM_INT=${MEM_PCT%.*}; MEM_INT=${MEM_INT:-0}

    SWAP=$(sysctl vm.swapusage 2>/dev/null | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    LOAD=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')
    BATT=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)

    CT=$(get_pm cpu_temp); GT=$(get_pm gpu_temp)
    CP=$(get_pm cpu_power); GP=$(get_pm gpu_power)

    # Color for CPU/MEM
    CC=$G; [[ ${CPU_INT:-0} -gt 50 ]] && CC=$Y; [[ ${CPU_INT:-0} -gt 80 ]] && CC=$R
    MC=$G; [[ ${MEM_INT:-0} -gt 60 ]] && MC=$Y; [[ ${MEM_INT:-0} -gt 85 ]] && MC=$R

    CPU_BAR=$(make_bar ${CPU_INT:-0})
    MEM_BAR=$(make_bar ${MEM_INT:-0})

    # Stress info
    SI=""
    if [[ -n "$STRESS_TYPE" && ${#STRESS_PIDS[@]} -gt 0 ]]; then
        now=$(date +%s); rem=$((STRESS_DUR - (now - STRESS_T0)))
        if [[ $rem -le 0 ]]; then stop_stress
        else SI="  ${R}🔥 СТРЕС: ${STRESS_TYPE} — ${rem}с залишилось${N}"; fi
    fi

    # Temp+Power line
    TP=""
    [[ -n "$CT" ]] && TP="${TP}CPU ${CT}°C  "
    [[ -n "$GT" ]] && TP="${TP}GPU ${GT}°C  "
    [[ -n "$CP" ]] && TP="${TP}⚡${CP}W  "
    [[ -n "$GP" ]] && TP="${TP}GPU⚡${GP}W  "
    [[ -z "$TP" ]] && TP="⏳ чекаю дані..."

    # Position cursor at live data area and overwrite
    tput cup $LIVE_START 0 2>/dev/null
    printf "  ${W}CPU${N}  %5s%%  ${CC}%s${N}\n" "$CPU_PCT" "$CPU_BAR"
    printf "  ${W}RAM${N}  %5s%%  ${MC}%s${N}  ${D}(${MEM_USED}/${RAM_GB} GB)${N}\n" "$MEM_PCT" "$MEM_BAR"
    printf "  ${W}Swap${N}  %-6s MB    ${W}Load${N}  %-8s  ${W}Batt${N}  %-5s\n" "${SWAP:-0}" "${LOAD:-?}" "${BATT:-n/a}"
    printf "  ${W}🌡${N}  %-50s\n" "$TP"
    printf "%-62s\n" "$SI"
    printf "  ${D}──────────────────────────────────────────────────${N}\n"
    printf "                                                           \n"

    read -t 2 -n 1 key 2>/dev/null
    case "$key" in
        1) stress_cpu 120 ;;
        2) stress_mem 1024 120 ;;
        3) stress_disk 120 ;;
        4) stress_all 180 ;;
        x|X) stop_stress ;;
        q|Q) exit 0 ;;
    esac
done
