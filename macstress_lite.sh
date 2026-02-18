#!/bin/bash
# ⚡ MacStress Lite — Pure Bash, Zero Dependencies
# Works on ANY Mac without Python, Xcode, or anything else

# ── Colors ────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; B='\033[0;34m'
C='\033[0;36m'; W='\033[1;37m'; D='\033[0;90m'; N='\033[0m'; BOLD='\033[1m'

# ── System Info ───────────────────────────────────────────
MODEL=$(sysctl -n hw.model 2>/dev/null)
CPU_BRAND=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "?")
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null || echo "?")
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
ARCH=$(uname -m)

clear
echo ""
echo -e "  ${Y}⚡${N} ${BOLD}MacStress Lite${N} ${D}— Pure Bash Monitor${N}"
echo -e "  ${D}────────────────────────────────────────${N}"
echo -e "  ${C}Model:${N}  $MODEL"
echo -e "  ${C}CPU:${N}    $CPU_BRAND"
echo -e "  ${C}Cores:${N}  $CORES  ·  ${C}RAM:${N} ${RAM_GB} GB"
echo -e "  ${C}macOS:${N}  $OS_VER  ·  ${C}Arch:${N} $ARCH"
echo -e "  ${D}────────────────────────────────────────${N}"
echo ""

# ── Stress test functions ─────────────────────────────────
STRESS_PIDS=()

start_cpu_stress() {
    echo -e "  ${R}🔥 CPU Stress: $CORES потоків${N}"
    for ((i=0; i<CORES; i++)); do
        yes > /dev/null 2>&1 &
        STRESS_PIDS+=($!)
    done
}

start_mem_stress() {
    local mb=${1:-512}
    echo -e "  ${R}🔥 Memory Stress: ${mb} MB${N}"
    # Allocate memory using dd
    dd if=/dev/zero bs=1m count=$mb 2>/dev/null | cat > /dev/null &
    STRESS_PIDS+=($!)
}

stop_stress() {
    for pid in "${STRESS_PIDS[@]}"; do
        kill $pid 2>/dev/null
    done
    STRESS_PIDS=()
    echo -e "  ${G}✅ Стрес-тест зупинено${N}"
}

cleanup() {
    stop_stress
    tput cnorm 2>/dev/null  # Show cursor
    echo ""
    echo -e "  ${G}✅ Done. Goodbye!${N}"
    echo ""
    exit 0
}
trap cleanup EXIT INT TERM

# ── Parse vm_stat ─────────────────────────────────────────
parse_vm() {
    local data=$(vm_stat 2>/dev/null)
    local ps=16384  # Apple Silicon page size
    [[ "$ARCH" == "x86_64" ]] && ps=4096

    local active=$(echo "$data" | awk '/Pages active/ {gsub(/\./,"",$NF); print $NF}')
    local wired=$(echo "$data" | awk '/Pages wired/ {gsub(/\./,"",$NF); print $NF}')
    local compressed=$(echo "$data" | awk '/occupied by compressor/ {gsub(/\./,"",$NF); print $NF}')

    active=${active:-0}; wired=${wired:-0}; compressed=${compressed:-0}
    local used_bytes=$(( (active + wired + compressed) * ps ))
    echo "scale=1; $used_bytes / 1073741824" | bc 2>/dev/null
}

# ── Menu ──────────────────────────────────────────────────
echo -e "  ${W}Команди:${N}"
echo -e "    ${Y}s${N} — Стрес-тест CPU     ${Y}q${N} — Вихід"
echo -e "    ${Y}x${N} — Зупинити тест      ${Y}Enter${N} — Оновити"
echo ""
echo -e "  ${D}────────────────────────────────────────${N}"

# ── Main monitoring loop ──────────────────────────────────
tput civis 2>/dev/null  # Hide cursor

while true; do
    # CPU usage
    CPU_RAW=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    CPU_PCT=$(echo "scale=1; $CPU_RAW / $CORES" | bc 2>/dev/null || echo "$CPU_RAW")
    # Cap at 100
    CPU_INT=${CPU_PCT%.*}
    [[ ${CPU_INT:-0} -gt 100 ]] && CPU_PCT="100.0"

    # Memory
    MEM_USED=$(parse_vm)
    MEM_PCT=$(echo "scale=1; $MEM_USED * 100 / $RAM_GB" | bc 2>/dev/null || echo "?")

    # Swap
    SWAP_LINE=$(sysctl vm.swapusage 2>/dev/null)
    SWAP_USED=$(echo "$SWAP_LINE" | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    SWAP_USED=${SWAP_USED:-0}

    # Load average
    LOAD=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')

    # Disk I/O
    DISK_IO=$(iostat -d -c 2 2>/dev/null | tail -1 | awk '{printf "R:%.1f W:%.1f MB/s", $2/1024, $3/1024}')

    # Temperature (try ioreg for SMC, works without sudo)
    TEMP=""
    TEMP_RAW=$(ioreg -rc AppleSmartBattery 2>/dev/null | awk '/Temperature/{print $NF; exit}')
    if [[ -n "$TEMP_RAW" && "$TEMP_RAW" -gt 0 ]] 2>/dev/null; then
        TEMP=$(echo "scale=1; $TEMP_RAW / 100" | bc 2>/dev/null)
    fi

    # Battery
    BATT=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)

    # Display
    echo -ne "\033[6A"  # Move up 6 lines

    # CPU bar
    CPU_BAR_LEN=$(echo "$CPU_PCT / 2.5" | bc 2>/dev/null || echo 0)
    CPU_BAR_LEN=${CPU_BAR_LEN%.*}
    [[ -z "$CPU_BAR_LEN" || "$CPU_BAR_LEN" -le 0 ]] && CPU_BAR_LEN=1
    [[ "$CPU_BAR_LEN" -gt 40 ]] && CPU_BAR_LEN=40
    CPU_BAR=$(printf '█%.0s' $(seq 1 $CPU_BAR_LEN 2>/dev/null || echo 1))
    CPU_COLOR=$G; [[ ${CPU_INT:-0} -gt 50 ]] && CPU_COLOR=$Y; [[ ${CPU_INT:-0} -gt 80 ]] && CPU_COLOR=$R

    # RAM bar
    MEM_INT=${MEM_PCT%.*}
    MEM_BAR_LEN=$(echo "$MEM_PCT / 2.5" | bc 2>/dev/null || echo 0)
    MEM_BAR_LEN=${MEM_BAR_LEN%.*}
    [[ -z "$MEM_BAR_LEN" || "$MEM_BAR_LEN" -le 0 ]] && MEM_BAR_LEN=1
    [[ "$MEM_BAR_LEN" -gt 40 ]] && MEM_BAR_LEN=40
    MEM_BAR=$(printf '█%.0s' $(seq 1 $MEM_BAR_LEN 2>/dev/null || echo 1))
    MEM_COLOR=$G; [[ ${MEM_INT:-0} -gt 60 ]] && MEM_COLOR=$Y; [[ ${MEM_INT:-0} -gt 85 ]] && MEM_COLOR=$R

    printf "  ${W}CPU${N}  %5s%%  ${CPU_COLOR}%-40s${N}\n" "$CPU_PCT" "$CPU_BAR"
    printf "  ${W}RAM${N}  %5s%%  ${MEM_COLOR}%-40s${N}  ${D}${MEM_USED}/${RAM_GB} GB${N}\n" "$MEM_PCT" "$MEM_BAR"
    printf "  ${W}Swap${N} %5s MB  ${D}Load: ${LOAD}${N}                          \n" "$SWAP_USED"
    printf "  ${W}Disk${N} ${D}${DISK_IO}${N}                                \n"
    EXTRA=""
    [[ -n "$TEMP" ]] && EXTRA="${EXTRA}${C}Temp:${N} ${TEMP}°C  "
    [[ -n "$BATT" ]] && EXTRA="${EXTRA}${C}Batt:${N} ${BATT}  "
    [[ ${#STRESS_PIDS[@]} -gt 0 ]] && EXTRA="${EXTRA}${R}STRESS ACTIVE${N}  "
    printf "  %-60s\n" "$EXTRA"
    printf "  ${D}────────────────────────────────────────${N}\n"

    # Check for input (non-blocking)
    read -t 2 -n 1 key 2>/dev/null
    case "$key" in
        s|S) tput cnorm; start_cpu_stress; tput civis ;;
        x|X) stop_stress ;;
        q|Q) exit 0 ;;
    esac
done
