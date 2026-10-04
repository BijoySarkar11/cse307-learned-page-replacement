#!/usr/bin/env bash
# ==============================================================================
# CSE-307: Operating Systems - OS Resource & Kernel Page Fault Monitor
# Monitors real Linux system memory, RSS, swap, and minor/major page faults
# for a target process using /proc and kernel statistics.
# ==============================================================================

set -euo pipefail

TARGET_PID="${1:-}"
OUTPUT_CSV="${2:-../results/os_system_metrics.csv}"
INTERVAL="${3:-0.5}"

if [ -z "$TARGET_PID" ]; then
    echo "Usage: $0 <PID> [OUTPUT_CSV] [INTERVAL_SEC]" >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT_CSV")"

# CSV Header
echo "timestamp_sec,pid,rss_kb,mem_pct,cpu_pct,minor_faults,major_faults,sys_free_mb,sys_available_mb,sys_swap_used_mb" > "$OUTPUT_CSV"

START_TIME=$(date +%s)

while kill -0 "$TARGET_PID" 2>/dev/null; do
    CURR_TIME=$(date +%s)
    ELAPSED=$(( CURR_TIME - START_TIME ))

    # Process-specific stats via /proc/[pid]/stat
    # Field 10: minflt (minor page faults)
    # Field 12: majflt (major page faults requiring disk I/O)
    if [ -r "/proc/$TARGET_PID/stat" ]; then
        STAT_CONTENT=$(cat "/proc/$TARGET_PID/stat")
        MIN_FLT=$(echo "$STAT_CONTENT" | awk '{print $10}')
        MAJ_FLT=$(echo "$STAT_CONTENT" | awk '{print $12}')
    else
        MIN_FLT=0
        MAJ_FLT=0
    fi

    # Process RSS, %MEM, %CPU via ps
    PS_OUT=$(ps -p "$TARGET_PID" -o rss=,%mem=,%cpu= 2>/dev/null || echo "0 0.0 0.0")
    RSS=$(echo "$PS_OUT" | awk '{print $1}')
    PMEM=$(echo "$PS_OUT" | awk '{print $2}')
    PCPU=$(echo "$PS_OUT" | awk '{print $3}')

    # System-level memory via free -m
    SYS_FREE=$(free -m | awk '/^Mem:/ {print $4}')
    SYS_AVAIL=$(free -m | awk '/^Mem:/ {print $7}')
    SYS_SWAP=$(free -m | awk '/^Swap:/ {print $3}')

    echo "${ELAPSED},${TARGET_PID},${RSS:-0},${PMEM:-0.0},${PCPU:-0.0},${MIN_FLT:-0},${MAJ_FLT:-0},${SYS_FREE:-0},${SYS_AVAIL:-0},${SYS_SWAP:-0}" >> "$OUTPUT_CSV"

    sleep "$INTERVAL"
done

exit 0
