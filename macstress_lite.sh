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

# ===== PASSWORD (with /dev/tty for piped scripts) =========
printf "\n"
printf "  ${Y}*${N} ${B}MacStress Lite${N}\n"
printf "  ${D}------------------------------------------------${N}\n"
printf "  Admin password is needed for temp/power.\n"
printf "  (Enter below, or Ctrl+C to skip)\n"
printf "\n"

# Ask for password explicitly through terminal
sudo -v < /dev/tty 2>&1
if [ $? -eq 0 ]; then
    GOT_SUDO=0
    printf "  ${G}OK${N}\n"
else
    printf "  ${Y}Skipped${N}\n"
fi
sleep 1

# ===== START POWERMETRICS =================================
if [ "$GOT_SUDO" -eq 0 ]; then
    if [ "$ARCH" = "x86_64" ]; then
        PMS="smc"
    else
        PMS="cpu_power,gpu_power"
    fi
    # Run powermetrics, save ALL output to temp file for parsing
    sudo powermetrics --samplers "$PMS" -i 3000 2>/dev/null > /tmp/macstress_pm_raw &
    PM_PID=$!
    # Background parser
    (while :; do
        sleep 4
        [ ! -f /tmp/macstress_pm_raw ] && continue
        # Parse temperatures (various formats)
        ct=$(grep -i "die temperature\|thermal level" /tmp/macstress_pm_raw 2>/dev/null | grep -i cpu | tail -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        gt=$(grep -i "die temperature\|thermal level" /tmp/macstress_pm_raw 2>/dev/null | grep -i gpu | tail -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        # Parse power
        cpw=$(grep -iE "^cpu power|^package power|intel energy" /tmp/macstress_pm_raw 2>/dev/null | tail -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        gpw=$(grep -iE "^gpu power" /tmp/macstress_pm_raw 2>/dev/null | tail -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        [ -n "$ct" ] && echo "cpu_temp=$ct" >> "$PM_DATA"
        [ -n "$gt" ] && echo "gpu_temp=$gt" >> "$PM_DATA"
        [ -n "$cpw" ] && echo "cpu_power=$cpw" >> "$PM_DATA"
        [ -n "$gpw" ] && echo "gpu_power=$gpw" >> "$PM_DATA"
        # Trim
        lc=$(wc -l < "$PM_DATA" 2>/dev/null)
        [ "$lc" -gt 40 ] 2>/dev/null && tail -20 "$PM_DATA" > "${PM_DATA}.tmp" && mv "${PM_DATA}.tmp" "$PM_DATA"
    done) &
    PARSER_PID=$!
fi

# ===== STRESS STATE =======================================
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
    [ -n "$PARSER_PID" ] && kill "$PARSER_PID" 2>/dev/null
    sudo pkill -9 powermetrics 2>/dev/null
    rm -f "$PM_DATA" "${PM_DATA}.tmp" /tmp/macstress_pm_raw /tmp/macstress_bench_* 2>/dev/null
    tput cnorm 2>/dev/null
    printf "\n  ${G}Bye!${N}\n\n"
    exit 0
}
trap cleanup EXIT INT TERM

# ===== STRESS FUNCTIONS ===================================
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

# ===== DISK BENCHMARK (multi-size) ========================
BENCH_LINES=""

run_dd_bench() {
    # $1=label $2=bs $3=count $4=file
    label=$1; bs=$2; cnt=$3; f=$4
    total_mb=$5

    # Write
    t0s=$(date +%s); t0ms=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1000' 2>/dev/null || echo "0")
    dd if=/dev/zero of="$f" bs="$bs" count="$cnt" 2>/dev/null
    sync
    t1s=$(date +%s); t1ms=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1000' 2>/dev/null || echo "0")
    
    if [ "$t0ms" != "0" ] && [ "$t1ms" != "0" ]; then
        wms=$((t1ms - t0ms))
        [ "$wms" -lt 1 ] && wms=1
        ws=$(echo "scale=0; $total_mb * 1000 / $wms" | bc 2>/dev/null)
    else
        wd=$((t1s - t0s)); [ "$wd" -lt 1 ] && wd=1
        ws=$((total_mb / wd))
    fi

    # Read (purge disk cache)
    sudo purge 2>/dev/null
    t0s=$(date +%s); t0ms=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1000' 2>/dev/null || echo "0")
    dd if="$f" of=/dev/null bs="$bs" 2>/dev/null
    t1s=$(date +%s); t1ms=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time*1000' 2>/dev/null || echo "0")
    
    if [ "$t0ms" != "0" ] && [ "$t1ms" != "0" ]; then
        rms=$((t1ms - t0ms))
        [ "$rms" -lt 1 ] && rms=1
        rs=$(echo "scale=0; $total_mb * 1000 / $rms" | bc 2>/dev/null)
    else
        rd=$((t1s - t0s)); [ "$rd" -lt 1 ] && rd=1
        rs=$((total_mb / rd))
    fi

    rm -f "$f"
    printf "  %-12s  Write: %4s MB/s  Read: %4s MB/s\n" "$label" "${ws:-?}" "${rs:-?}"
}

disk_bench() {
    bf="/tmp/macstress_bench"
    printf "\n"
    printf "  ${B}Disk Benchmark${N}\n"
    printf "  ${D}------------------------------------------------${N}\n"

    # Sequential 1MB blocks, 512MB total
    printf "  ${Y}Testing...${N} Sequential 1MB x 512\n"
    r1=$(run_dd_bench "Seq 1MB" "1m" 512 "${bf}_seq1m" 512)

    # Sequential 256KB blocks, 256MB total
    printf "  ${Y}Testing...${N} Sequential 256K x 1024\n"
    r2=$(run_dd_bench "Seq 256K" "256k" 1024 "${bf}_seq256k" 256)

    # Sequential 64KB blocks, 128MB total
    printf "  ${Y}Testing...${N} Sequential 64K x 2048\n"
    r3=$(run_dd_bench "Seq 64K" "64k" 2048 "${bf}_seq64k" 128)

    # Sequential 4KB blocks, 32MB total
    printf "  ${Y}Testing...${N} Random 4K x 8192\n"
    r4=$(run_dd_bench "Rnd 4K" "4k" 8192 "${bf}_rnd4k" 32)

    BENCH_LINES=$(printf "%s\n%s\n%s\n%s" "$r1" "$r2" "$r3" "$r4")

    printf "\r  ${G}Done!${N}                              \n"
    printf "\n"
    printf "  ${B}Results:${N}\n"
    printf "%s\n" "$BENCH_LINES"
    printf "  ${D}------------------------------------------------${N}\n"
    printf "  ${D}Press any key to continue...${N}\n"
    read -n 1 dummy < /dev/tty 2>/dev/null
    clear
    draw_header
}

# ===== HELPERS ============================================
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

# ===== HEADER =============================================
draw_header() {
    printf "\n"
    printf "  ${Y}*${N} ${B}MacStress Lite${N}\n"
    printf "  ${D}================================================${N}\n"
    printf "  ${C}Model${N}  %s\n" "$MODEL"
    printf "  ${C}CPU${N}    %s\n" "$CPU_BRAND"
    printf "  ${C}Cores${N}  %s   ${C}RAM${N}  %s GB   ${C}macOS${N}  %s (%s)\n" "$CORES" "$RAM_GB" "$OS_VER" "$ARCH"
    printf "  ${D}================================================${N}\n"
    printf "  ${B}Controls:${N}\n"
    printf "  ${Y}[1]${N} CPU  ${Y}[2]${N} RAM  ${Y}[3]${N} Disk  ${Y}[4]${N} ALL\n"
    printf "  ${Y}[5]${N} Disk Bench  ${Y}[x]${N} Stop  ${Y}[q]${N} Quit\n"
    printf "  ${D}================================================${N}\n"
    printf "\n\n\n\n\n\n\n\n\n\n"
    LL=13
}

clear
draw_header
tput civis 2>/dev/null

# ===== MAIN LOOP =========================================
while true; do
    cr=$(ps -A -o %cpu | awk '{s+=$1} END {printf "%.1f", s}')
    cp=$(echo "scale=1; $cr / $CORES" | bc 2>/dev/null || echo "0")
    ci=${cp%.*}; ci=${ci:-0}
    [ "$ci" -gt 100 ] 2>/dev/null && cp="100.0" && ci=100

    mu=$(parse_vm); mu=${mu:-0}
    mp=$(echo "scale=1; $mu * 100 / $RAM_GB" | bc 2>/dev/null || echo "0")
    mi=${mp%.*}; mi=${mi:-0}

    sw=$(sysctl vm.swapusage 2>/dev/null | grep -oE 'used = [0-9.]+M' | grep -oE '[0-9.]+')
    ld=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')
    bt=$(pmset -g batt 2>/dev/null | grep -oE '[0-9]+%' | head -1)
    di=$(disk_io)

    ct=$(get_pm cpu_temp); gt=$(get_pm gpu_temp)
    pw=$(get_pm cpu_power); gw=$(get_pm gpu_power)

    cc=$G; [ "$ci" -gt 50 ] 2>/dev/null && cc=$Y; [ "$ci" -gt 80 ] 2>/dev/null && cc=$R
    mc=$G; [ "$mi" -gt 60 ] 2>/dev/null && mc=$Y; [ "$mi" -gt 85 ] 2>/dev/null && mc=$R

    cb=$(bar "$ci")
    mb=$(bar "$mi")

    tp=""
    [ -n "$ct" ] && tp="${tp}CPU:${ct}C "
    [ -n "$gt" ] && tp="${tp}GPU:${gt}C "
    [ -n "$pw" ] && tp="${tp}Pwr:${pw}W "
    [ -n "$gw" ] && tp="${tp}GPU:${gw}W "
    if [ -z "$tp" ]; then
        if [ "$GOT_SUDO" -eq 0 ]; then tp="waiting..."; else tp="(need sudo)"; fi
    fi

    sl="${G}OFF${N}"
    if [ -n "$STYPE" ]; then
        now=$(date +%s); rem=$((SDUR - (now - ST0)))
        if [ "$rem" -le 0 ] 2>/dev/null; then
            stop_s
        else
            sl="${R}${STYPE} ${rem}s left${N}"
        fi
    fi

    # Last bench result (one-liner)
    br=""
    if [ -n "$BENCH_LINES" ]; then
        # Show just seq 1MB result as summary
        br=$(echo "$BENCH_LINES" | head -1)
    fi

    tput cup "$LL" 0 2>/dev/null
    printf "  ${W}CPU${N}   %5s%%  ${cc}%s${N}                       \n" "$cp" "$cb"
    printf "  ${W}RAM${N}   %5s%%  ${mc}%s${N}  ${D}%s/%sGB${N}          \n" "$mp" "$mb" "$mu" "$RAM_GB"
    printf "  ${W}Disk${N}  %-22s  ${W}Batt${N} %-5s       \n" "$di" "${bt:-n/a}"
    printf "  ${W}Swap${N}  %-5s MB  ${W}Load${N} %-8s            \n" "${sw:-0}" "${ld:-?}"
    printf "  ${W}Temp${N}  %-44s\n" "$tp"
    printf "  ${W}Test${N}  %s                                     \n" "$sl"
    if [ -n "$br" ]; then
        printf "  ${W}Bench${N}${C}%s${N}          \n" "$br"
    else
        printf "  ${D}  [5] = disk benchmark (4 tests)${N}                \n"
    fi
    printf "  ${D}------------------------------------------------${N}\n"
    printf "                                                          \n"
    printf "                                                          \n"

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
