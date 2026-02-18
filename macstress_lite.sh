#!/bin/bash
# MacStress Lite — Pure Bash, Zero Dependencies
# Works on any Mac from 2010+ (bash 3.2 compatible)

R=$'\033[0;31m'
G=$'\033[0;32m'
Y=$'\033[0;33m'
C=$'\033[0;36m'
W=$'\033[1;37m'
D=$'\033[0;90m'
N=$'\033[0m'
B=$'\033[1m'

MODEL=$(sysctl -n hw.model 2>/dev/null || echo "Mac")
CPU_BRAND=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "?")
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "4")
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null || echo "?")
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "?")
ARCH=$(uname -m)

PM_DATA="/tmp/macstress_pm_data"
printf "" > "$PM_DATA"
PM_PID=""
GOT_SUDO=1

get_pm() { grep "^$1=" "$PM_DATA" 2>/dev/null | tail -1 | cut -d= -f2; }

# ===== ASK FOR PASSWORD (before clear, with /dev/tty) =====
# When run via bash <(curl ...), stdin is the pipe, not terminal.
# We MUST read password from /dev/tty explicitly.
printf "\n"
printf "  ${Y}*${N} ${B}MacStress Lite${N}\n"
printf "  ${D}------------------------------------------------${N}\n"
printf "  For temp/power monitoring, admin password is needed.\n"
printf "  Enter password below (asked once):\n"
printf "\n"

# Try sudo with tty
if sudo -v < /dev/tty 2>/dev/null; then
    GOT_SUDO=0
    printf "  ${G}OK - admin access granted${N}\n"
else
    printf "  ${Y}Skipped - temp/power unavailable${N}\n"
fi
sleep 1

# Start powermetrics if we have sudo
if [ "$GOT_SUDO" -eq 0 ]; then
    if [ "$ARCH" = "x86_64" ]; then
        PMS="smc,cpu_power,gpu_power"
    else
        PMS="cpu_power,gpu_power"
    fi
    sudo powermetrics --samplers "$PMS" -i 3000 -n 0 2>/dev/null | while IFS= read -r line; do
        ll=$(echo "$line" | tr '[:upper:]' '[:lower:]')
        val=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+' | head -1)
        [ -z "$val" ] && continue
        case "$ll" in
            *"cpu die temp"*|*"cpu thermal"*)     echo "cpu_temp=$val" >> "$PM_DATA" ;;
            *"gpu die temp"*|*"gpu thermal"*)     echo "gpu_temp=$val" >> "$PM_DATA" ;;
            "cpu power"*|"package power"*|*"intel energy"*) echo "cpu_power=$val" >> "$PM_DATA" ;;
            "gpu power"*)                         echo "gpu_power=$val" >> "$PM_DATA" ;;
        esac
        lc=$(wc -l < "$PM_DATA" 2>/dev/null)
        [ "$lc" -gt 40 ] 2>/dev/null && tail -20 "$PM_DATA" > "${PM_DATA}.tmp" && mv "${PM_DATA}.tmp" "$PM_DATA"
    done &
    PM_PID=$!
fi

# ===== STRESS STATE =====
SPIDS=""
STYPE=""
SDUR=0
ST0=0

apid() { SPIDS="$SPIDS $1"; }

stop_s() {
    for p in $SPIDS; do kill "$p" 2>/dev/null; wait "$p" 2>/dev/null; done
    SPIDS=""; STYPE=""
    rm -f /tmp/macstress_mem_* /tmp/macstress_disk_* 2>/dev/null
}

cleanup() {
    stop_s
    [ -n "$PM_PID" ] && kill "$PM_PID" 2>/dev/null
    sudo pkill -9 powermetrics 2>/dev/null
    rm -f "$PM_DATA" "${PM_DATA}.tmp" /tmp/macstress_bench_* 2>/dev/null
    tput cnorm 2>/dev/null
    printf "\n  ${G}Bye!${N}\n\n"
    exit 0
}
trap cleanup EXIT INT TERM

# ===== STRESS FUNCTIONS =====
s_cpu() {
    d=${1:-120}; stop_s; STYPE="CPU ($CORES cores)"; SDUR=$d; ST0=$(date +%s)
    i=0; while [ "$i" -lt "$CORES" ]; do
        (while :; do :; done) &
        apid $!; i=$((i+1))
    done
    (sleep "$d"; kill $SPIDS 2>/dev/null) &
    apid $!
}

s_mem() {
    mb=${1:-512}; d=${2:-120}; stop_s; STYPE="RAM (${mb}MB)"; SDUR=$d; ST0=$(date +%s)
    ch=$((mb/64))
    (i=0; while [ "$i" -lt "$ch" ]; do
        dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=64 2>/dev/null; i=$((i+1))
    done
    while :; do j=0; while [ "$j" -lt "$ch" ]; do
        cat /tmp/macstress_mem_$j >/dev/null 2>/dev/null; j=$((j+1))
    done; sleep 1; done) &
    apid $!
    (sleep "$d"; kill $! 2>/dev/null; rm -f /tmp/macstress_mem_*) &
    apid $!
}

s_disk() {
    d=${1:-120}; stop_s; STYPE="DISK (R/W)"; SDUR=$d; ST0=$(date +%s)
    (while :; do
        dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=256 2>/dev/null
        dd if=/tmp/macstress_disk_w of=/dev/null bs=1m 2>/dev/null
        rm -f /tmp/macstress_disk_w
    done) &
    apid $!
    (sleep "$d"; kill $! 2>/dev/null; rm -f /tmp/macstress_disk_*) &
    apid $!
}

s_all() {
    d=${1:-180}; stop_s; STYPE="ALL (CPU+RAM+Disk)"; SDUR=$d; ST0=$(date +%s)
    i=0; while [ "$i" -lt "$CORES" ]; do
        (while :; do :; done) &
        apid $!; i=$((i+1))
    done
    (i=0; while [ "$i" -lt 8 ]; do
        dd if=/dev/urandom of=/tmp/macstress_mem_$i bs=1m count=64 2>/dev/null; i=$((i+1))
    done
    while :; do j=0; while [ "$j" -lt 8 ]; do
        cat /tmp/macstress_mem_$j >/dev/null 2>/dev/null; j=$((j+1))
    done; sleep 1; done) &
    apid $!
    (while :; do dd if=/dev/zero of=/tmp/macstress_disk_w bs=1m count=128 2>/dev/null; rm -f /tmp/macstress_disk_w; done) &
    apid $!
    (sleep "$d"; kill $SPIDS 2>/dev/null; rm -f /tmp/macstress_*) &
    apid $!
}

# ===== DISK BENCHMARK =====
BENCH_RESULT=""

disk_bench() {
    BENCH_RESULT="running..."
    bf="/tmp/macstress_bench_file"
    sz=256  # MB

    # Write test
    t0=$(date +%s)
    dd if=/dev/zero of="$bf" bs=1m count=$sz 2>/dev/null
    sync
    t1=$(date +%s)
    wd=$((t1 - t0))
    [ "$wd" -lt 1 ] && wd=1
    ws=$((sz / wd))

    # Read test
    t0=$(date +%s)
    dd if="$bf" of=/dev/null bs=1m 2>/dev/null
    t1=$(date +%s)
    rd=$((t1 - t0))
    [ "$rd" -lt 1 ] && rd=1
    rs=$((sz / rd))

    rm -f "$bf"
    BENCH_RESULT="Write: ${ws} MB/s  Read: ${rs} MB/s  (${sz}MB test)"
}

# ===== HELPERS =====
parse_vm() {
    data=$(vm_stat 2>/dev/null); ps=16384
    [ "$ARCH" = "x86_64" ] && ps=4096
    a=$(echo "$data"|awk '/Pages active/{gsub(/\./,"",$NF);print $NF}')
    w=$(echo "$data"|awk '/Pages wired/{gsub(/\./,"",$NF);print $NF}')
    c=$(echo "$data"|awk '/occupied by compressor/{gsub(/\./,"",$NF);print $NF}')
    echo "scale=1; $(( (${a:-0} + ${w:-0} + ${c:-0}) * ps )) / 1073741824" | bc 2>/dev/null
}

bar() {
    p=$1; m=20; l=$((p * m / 100))
    [ "$l" -lt 0 ] 2>/dev/null && l=0; [ "$l" -gt "$m" ] && l=$m
    b=""; i=0
    while [ "$i" -lt "$l" ]; do b="${b}#"; i=$((i+1)); done
    while [ "$i" -lt "$m" ]; do b="${b}."; i=$((i+1)); done
    printf "[%s]" "$b"
}

disk_io() {
    io=$(iostat -d -c 2 2>/dev/null | tail -1)
    if [ -n "$io" ]; then
        r=$(echo "$io" | awk '{printf "%.1f", $2/1024}')
        w=$(echo "$io" | awk '{printf "%.1f", $3/1024}')
        printf "R:%s W:%s MB/s" "$r" "$w"
    else
        printf "n/a"
    fi
}

# ===== DRAW HEADER =====
clear
printf "\n"
printf "  ${Y}*${N} ${B}MacStress Lite${N}\n"
printf "  ${D}================================================${N}\n"
printf "  ${C}Model${N}  %s\n" "$MODEL"
printf "  ${C}CPU${N}    %s\n" "$CPU_BRAND"
printf "  ${C}Cores${N}  %s   ${C}RAM${N}  %s GB   ${C}macOS${N}  %s (%s)\n" "$CORES" "$RAM_GB" "$OS_VER" "$ARCH"
printf "  ${D}================================================${N}\n"
printf "  ${B}Controls:${N}\n"
printf "  ${Y}[1]${N} CPU  ${Y}[2]${N} RAM  ${Y}[3]${N} Disk  ${Y}[4]${N} ALL  ${Y}[5]${N} Bench\n"
printf "  ${Y}[x]${N} Stop stress   ${Y}[q]${N} Quit\n"
printf "  ${D}================================================${N}\n"
printf "\n\n\n\n\n\n\n\n\n\n"

LL=13
tput civis 2>/dev/null

# ===== MAIN LOOP =====
while true; do
    # CPU
    cr=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    cp=$(echo "scale=1; $cr / $CORES" | bc 2>/dev/null || echo "0")
    ci=${cp%.*}; ci=${ci:-0}
    [ "$ci" -gt 100 ] 2>/dev/null && cp="100.0" && ci=100

    # RAM
    mu=$(parse_vm); mu=${mu:-0}
    mp=$(echo "scale=1; $mu * 100 / $RAM_GB" | bc 2>/dev/null || echo "0")
    mi=${mp%.*}; mi=${mi:-0}

    # System
    sw=$(sysctl vm.swapusage 2>/dev/null | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    ld=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')
    bt=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)
    di=$(disk_io)

    # Temp/Power
    ct=$(get_pm cpu_temp); gt=$(get_pm gpu_temp)
    pw=$(get_pm cpu_power); gw=$(get_pm gpu_power)

    cc=$G; [ "$ci" -gt 50 ] 2>/dev/null && cc=$Y; [ "$ci" -gt 80 ] 2>/dev/null && cc=$R
    mc=$G; [ "$mi" -gt 60 ] 2>/dev/null && mc=$Y; [ "$mi" -gt 85 ] 2>/dev/null && mc=$R

    cb=$(bar "$ci")
    mb=$(bar "$mi")

    # Temp string
    tp=""
    [ -n "$ct" ] && tp="${tp}CPU:${ct}C "
    [ -n "$gt" ] && tp="${tp}GPU:${gt}C "
    [ -n "$pw" ] && tp="${tp}Pwr:${pw}W "
    [ -n "$gw" ] && tp="${tp}GPU:${gw}W "
    if [ -z "$tp" ]; then
        if [ "$GOT_SUDO" -eq 0 ]; then tp="waiting..."; else tp="(need sudo)"; fi
    fi

    # Stress status
    sl="${G}OFF${N}"
    if [ -n "$STYPE" ]; then
        now=$(date +%s); rem=$((SDUR - (now - ST0)))
        if [ "$rem" -le 0 ] 2>/dev/null; then
            stop_s
        else
            sl="${R}${STYPE} ${rem}s left${N}"
        fi
    fi

    # Bench result
    br=""
    [ -n "$BENCH_RESULT" ] && br="$BENCH_RESULT"

    # Render
    tput cup "$LL" 0 2>/dev/null
    printf "  ${W}CPU${N}   %5s%%  ${cc}%s${N}                \n" "$cp" "$cb"
    printf "  ${W}RAM${N}   %5s%%  ${mc}%s${N}  ${D}%s/%sGB${N}   \n" "$mp" "$mb" "$mu" "$RAM_GB"
    printf "  ${W}Disk${N}  %-22s  ${W}Batt${N} %-5s    \n" "$di" "${bt:-n/a}"
    printf "  ${W}Swap${N}  %-5s MB  ${W}Load${N} %-6s             \n" "${sw:-0}" "${ld:-?}"
    printf "  ${W}Temp${N}  %-42s\n" "$tp"
    printf "  ${W}Test${N}  %s                                  \n" "$sl"
    if [ -n "$br" ]; then
        printf "  ${W}Bench${N} ${C}%s${N}                  \n" "$br"
    else
        printf "  ${D}[5] = disk benchmark${N}                        \n"
    fi
    printf "  ${D}------------------------------------------------${N}\n"
    printf "                                                       \n"

    read -t 2 -n 1 key < /dev/tty 2>/dev/null
    case "$key" in
        1) s_cpu 120 ;;
        2) s_mem 512 120 ;;
        3) s_disk 120 ;;
        4) s_all 180 ;;
        5) tput cnorm 2>/dev/null; disk_bench; tput civis 2>/dev/null ;;
        x|X) stop_s ;;
        q|Q) exit 0 ;;
    esac
done
