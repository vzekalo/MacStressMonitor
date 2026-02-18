#!/bin/bash
# ⚡ MacStress Lite — Pure Bash, Zero Dependencies
# Compatible with bash 3.2+ (macOS default)

R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'
C='\033[0;36m'; W='\033[1;37m'; D='\033[0;90m'; N='\033[0m'; BOLD='\033[1m'

MODEL=$(sysctl -n hw.model 2>/dev/null)
CPU_BRAND=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null || echo "?")
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
ARCH=$(uname -m)

# ── Powermetrics (background) ────────────────────────────
PM_DATA="/tmp/macstress_pm_data"
printf "" > "$PM_DATA"

start_powermetrics() {
    if [ "$ARCH" = "x86_64" ]; then
        SAMPLERS="smc,cpu_power,gpu_power"
    else
        SAMPLERS="cpu_power,gpu_power"
    fi
    echo -e "  ${Y}🔑${N} Для температури/споживання потрібен пароль (1 раз)"
    sudo powermetrics --samplers "$SAMPLERS" -i 3000 -n 0 2>/dev/null | while IFS= read -r line; do
        ll=$(echo "$line" | tr '[:upper:]' '[:lower:]')
        val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if [ -z "$val" ]; then continue; fi
        case "$ll" in
            *"cpu die temperature"*|*"cpu thermal level"*) echo "cpu_temp=$val" >> "$PM_DATA" ;;
            *"gpu die temperature"*|*"gpu thermal level"*) echo "gpu_temp=$val" >> "$PM_DATA" ;;
            "cpu power"*|"package power"*)                 echo "cpu_power=$val" >> "$PM_DATA" ;;
            "gpu power"*)                                  echo "gpu_power=$val" >> "$PM_DATA" ;;
        esac
        lines=$(wc -l < "$PM_DATA" 2>/dev/null)
        if [ "$lines" -gt 40 ] 2>/dev/null; then
            tail -20 "$PM_DATA" > "${PM_DATA}.tmp" && mv "${PM_DATA}.tmp" "$PM_DATA"
        fi
    done &
    PM_BG_PID=$!
}
get_pm() { grep "^$1=" "$PM_DATA" 2>/dev/null | tail -1 | cut -d= -f2; }

# ── Stress state ─────────────────────────────────────────
STRESS_PIDS=""
STRESS_TYPE=""
STRESS_DUR=0
STRESS_T0=0

add_pid() { STRESS_PIDS="$STRESS_PIDS $1"; }

stop_stress() {
    for p in $STRESS_PIDS; do
        kill "$p" 2>/dev/null
        wait "$p" 2>/dev/null
    done
    STRESS_PIDS=""
    STRESS_TYPE=""
    rm -f /tmp/macstress_mem_* /tmp/macstress_disk_* 2>/dev/null
}

cleanup() {
    stop_stress
    kill "$PM_BG_PID" 2>/dev/null
    sudo pkill -9 powermetrics 2>/dev/null
    rm -f "$PM_DATA" "${PM_DATA}.tmp" 2>/dev/null
    tput cnorm 2>/dev/null
    echo ""
    echo -e "  ${G}✅ Bye!${N}"
    echo ""
    exit 0
}
trap cleanup EXIT INT TERM

# ── Stress: CPU ───────────────────────────────────────────
stress_cpu() {
    dur=${1:-120}
    stop_stress
    STRESS_TYPE="CPU"
    STRESS_DUR=$dur
    STRESS_T0=$(date +%s)
    i=0
    while [ "$i" -lt "$CORES" ]; do
        (while :; do :; done) &
        add_pid $!
        i=$((i + 1))
    done
    (sleep "$dur"; kill $STRESS_PIDS 2>/dev/null) &
    add_pid $!
}

# ── Stress: RAM ───────────────────────────────────────────
stress_mem() {
    mb=${1:-512}
    dur=${2:-120}
    stop_stress
    STRESS_TYPE="RAM"
    STRESS_DUR=$dur
    STRESS_T0=$(date +%s)
    chunks=$((mb / 64))
    (
        i=0
        while [ "$i" -lt "$chunks" ]; do
            dd if=/dev/urandom of="/tmp/macstress_mem_$i" bs=1m count=64 2>/dev/null
            i=$((i + 1))
        done
        while :; do
            j=0
            while [ "$j" -lt "$chunks" ]; do
                cat "/tmp/macstress_mem_$j" > /dev/null 2>/dev/null
                j=$((j + 1))
            done
            sleep 1
        done
    ) &
    add_pid $!
    (sleep "$dur"; kill $! 2>/dev/null; rm -f /tmp/macstress_mem_*) &
    add_pid $!
}

# ── Stress: Disk ──────────────────────────────────────────
stress_disk() {
    dur=${1:-120}
    stop_stress
    STRESS_TYPE="DISK"
    STRESS_DUR=$dur
    STRESS_T0=$(date +%s)
    (while :; do
        dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=256 2>/dev/null
        dd if=/tmp/macstress_disk_w of=/dev/null bs=1m 2>/dev/null
        rm -f /tmp/macstress_disk_w
    done) &
    add_pid $!
    (sleep "$dur"; kill $! 2>/dev/null; rm -f /tmp/macstress_disk_*) &
    add_pid $!
}

# ── Stress: ALL ───────────────────────────────────────────
stress_all() {
    dur=${1:-180}
    stop_stress
    STRESS_TYPE="ALL"
    STRESS_DUR=$dur
    STRESS_T0=$(date +%s)
    # CPU
    i=0
    while [ "$i" -lt "$CORES" ]; do
        (while :; do :; done) &
        add_pid $!
        i=$((i + 1))
    done
    # RAM 512MB
    (
        i=0; while [ "$i" -lt 8 ]; do
            dd if=/dev/urandom of="/tmp/macstress_mem_$i" bs=1m count=64 2>/dev/null
            i=$((i + 1))
        done
        while :; do
            j=0; while [ "$j" -lt 8 ]; do cat "/tmp/macstress_mem_$j" > /dev/null 2>/dev/null; j=$((j + 1)); done
            sleep 1
        done
    ) &
    add_pid $!
    # Disk
    (while :; do dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=128 2>/dev/null; rm -f /tmp/macstress_disk_w; done) &
    add_pid $!
    # Timer
    (sleep "$dur"; kill $STRESS_PIDS 2>/dev/null; rm -f /tmp/macstress_*) &
    add_pid $!
}

# ── Parse vm_stat ─────────────────────────────────────────
parse_vm() {
    data=$(vm_stat 2>/dev/null)
    ps=16384
    [ "$ARCH" = "x86_64" ] && ps=4096
    active=$(echo "$data" | awk '/Pages active/ {gsub(/\./,"",$NF); print $NF}')
    wired=$(echo "$data" | awk '/Pages wired/ {gsub(/\./,"",$NF); print $NF}')
    compressed=$(echo "$data" | awk '/occupied by compressor/ {gsub(/\./,"",$NF); print $NF}')
    active=${active:-0}; wired=${wired:-0}; compressed=${compressed:-0}
    echo "scale=1; $(( (active + wired + compressed) * ps )) / 1073741824" | bc 2>/dev/null
}

make_bar() {
    pct=$1
    max=30
    len=$((pct * max / 100))
    [ "$len" -lt 0 ] 2>/dev/null && len=0
    [ "$len" -gt "$max" ] && len=$max
    bar=""
    i=0; while [ "$i" -lt "$len" ]; do bar="${bar}█"; i=$((i + 1)); done
    while [ "$i" -lt "$max" ]; do bar="${bar}░"; i=$((i + 1)); done
    echo "$bar"
}

# ── Draw static header ──────────────────────────────────
clear
tput civis 2>/dev/null

echo -e "  ${Y}⚡${N} ${BOLD}MacStress Lite${N}"
echo -e "  ${D}══════════════════════════════════════════════════${N}"
echo -e "  ${C}Модель${N}   $MODEL"
echo -e "  ${C}CPU${N}      $CPU_BRAND"
echo -e "  ${C}Ядра${N}  $CORES  ·  ${C}RAM${N}  ${RAM_GB} GB  ·  ${C}macOS${N}  $OS_VER ($ARCH)"
echo -e "  ${D}══════════════════════════════════════════════════${N}"
echo -e "  ${BOLD}Керування:${N}"
echo -e "  ${Y}[1]${N} CPU стрес  ${Y}[2]${N} RAM стрес  ${Y}[3]${N} Диск стрес"
echo -e "  ${Y}[4]${N} ВСЕ разом  ${Y}[x]${N} Зупинити   ${Y}[q]${N} Вийти"
echo -e "  ${D}══════════════════════════════════════════════════${N}"
# 7 blank lines for live data area
echo ""; echo ""; echo ""; echo ""; echo ""; echo ""; echo ""

LIVE_LINE=11

tput cnorm 2>/dev/null
start_powermetrics
tput civis 2>/dev/null

# ── Main Loop ─────────────────────────────────────────────
while true; do
    CPU_RAW=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    CPU_PCT=$(echo "scale=1; $CPU_RAW / $CORES" | bc 2>/dev/null || echo "0")
    CPU_INT=${CPU_PCT%.*}
    CPU_INT=${CPU_INT:-0}
    [ "$CPU_INT" -gt 100 ] 2>/dev/null && CPU_PCT="100.0" && CPU_INT=100

    MEM_USED=$(parse_vm)
    MEM_USED=${MEM_USED:-0}
    MEM_PCT=$(echo "scale=1; $MEM_USED * 100 / $RAM_GB" | bc 2>/dev/null || echo "0")
    MEM_INT=${MEM_PCT%.*}
    MEM_INT=${MEM_INT:-0}

    SWAP=$(sysctl vm.swapusage 2>/dev/null | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    LOAD=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')
    BATT=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)

    CT=$(get_pm cpu_temp)
    GT=$(get_pm gpu_temp)
    CP=$(get_pm cpu_power)
    GP=$(get_pm gpu_power)

    # Colors
    CC=$G; [ "$CPU_INT" -gt 50 ] 2>/dev/null && CC=$Y; [ "$CPU_INT" -gt 80 ] 2>/dev/null && CC=$R
    MC=$G; [ "$MEM_INT" -gt 60 ] 2>/dev/null && MC=$Y; [ "$MEM_INT" -gt 85 ] 2>/dev/null && MC=$R

    CPU_BAR=$(make_bar "$CPU_INT")
    MEM_BAR=$(make_bar "$MEM_INT")

    # Stress timer
    SI=""
    if [ -n "$STRESS_TYPE" ]; then
        now=$(date +%s)
        rem=$((STRESS_DUR - (now - STRESS_T0)))
        if [ "$rem" -le 0 ] 2>/dev/null; then
            stop_stress
        else
            SI="  ${R}🔥 СТРЕС: ${STRESS_TYPE} — ${rem}с${N}"
        fi
    fi

    # Temp+Power
    TP=""
    [ -n "$CT" ] && TP="${TP}CPU ${CT}°C  "
    [ -n "$GT" ] && TP="${TP}GPU ${GT}°C  "
    [ -n "$CP" ] && TP="${TP}⚡${CP}W  "
    [ -n "$GP" ] && TP="${TP}GPU⚡${GP}W  "
    [ -z "$TP" ] && TP="⏳ чекаю дані..."

    # Render at fixed position
    tput cup "$LIVE_LINE" 0 2>/dev/null
    printf "  ${W}CPU${N}  %5s%%  ${CC}%s${N}\n" "$CPU_PCT" "$CPU_BAR"
    printf "  ${W}RAM${N}  %5s%%  ${MC}%s${N}  ${D}(${MEM_USED}/${RAM_GB} GB)${N}\n" "$MEM_PCT" "$MEM_BAR"
    printf "  ${W}Swap${N}  %-6s MB    ${W}Load${N}  %-8s  ${W}Batt${N}  %-5s\n" "${SWAP:-0}" "${LOAD:-?}" "${BATT:-n/a}"
    printf "  ${W}🌡${N}  %-50s\n" "$TP"
    printf "%-62s\n" "$SI"
    printf "  ${D}──────────────────────────────────────────────────${N}\n"
    printf "                                                             \n"

    read -t 2 -n 1 key 2>/dev/null
    case "$key" in
        1) stress_cpu 120 ;;
        2) stress_mem 512 120 ;;
        3) stress_disk 120 ;;
        4) stress_all 180 ;;
        x|X) stop_stress ;;
        q|Q) exit 0 ;;
    esac
done
