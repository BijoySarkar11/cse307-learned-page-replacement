#!/usr/bin/env bash
# ==============================================================================
# CSE-307: Operating Systems - Automated Experiment Analyzer
# Uses pure Bash, AWK, and coreutils (grep, sort, cut, column) to parse,
# analyze, and report experimental and OS system-level performance.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_CSV="$PROJECT_ROOT/results/raw_results.csv"
SYSTEM_CSV="$PROJECT_ROOT/results/os_system_metrics.csv"

# Terminal Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "\n${BOLD}${BLUE}=================================================================${RESET}"
echo -e "${BOLD}${BLUE}   CSE-307 OPERATING SYSTEMS: EXPERIMENTAL RESULTS ANALYSIS     ${RESET}"
echo -e "${BOLD}${BLUE}=================================================================${RESET}\n"

if [ ! -f "$RESULTS_CSV" ]; then
    echo -e "${RED}Error: Results file not found at $RESULTS_CSV${RESET}"
    echo "Please run the experiments first: ./scripts/run_experiments.sh"
    exit 1
fi

echo -e "${CYAN}${BOLD}[1] OVERALL EXPERIMENT RESULTS (FULL TRACE ACROSS MEMORY FRAMES)${RESET}\n"

awk -F',' '
BEGIN {
    printf "%-12s %-8s %-12s %-12s %-12s\n", "Policy", "Frames", "Hits", "Faults", "Hit Ratio"
    print "--------------------------------------------------------"
}
NR > 1 && $3 == "Full Trace" {
    printf "%-12s %-8s %-12s %-12s %-12.4f\n", $1, $2, $4, $5, $6
}
' "$RESULTS_CSV"

echo -e "\n${CYAN}${BOLD}[2] ALGORITHM RANKING UNDER CONSTRAINED MEMORY (10 FRAMES, FULL TRACE)${RESET}\n"

awk -F',' '
NR > 1 && $2 == 10 && $3 == "Full Trace" {
    print $6, $1, $4, $5
}
' "$RESULTS_CSV" | sort -k1 -n -r | awk '
BEGIN {
    rank = 1
}
{
    printf "  Rank %d: %-10s -> Hit Ratio: \033[1;32m%.4f\033[0m (Hits: %5d | Page Faults: %5d)\n", rank, $2, $1, $3, $4
    rank++
}
'

echo -e "\n${CYAN}${BOLD}[3] WORKLOAD SHIFT DEGRADATION ANALYSIS (10 FRAMES: PHASE 1 VS PHASE 2)${RESET}\n"

awk -F',' '
NR > 1 && $2 == 10 {
    policy = $1
    phase = $3
    hr = $6
    if (phase ~ /Phase 1/) {
        p1[policy] = hr
    } else if (phase ~ /Phase 2/) {
        p2[policy] = hr
    }
}
END {
    for (pol in p1) {
        p1_val = p1[pol]
        p2_val = p2[pol]
        drop_pct = ((p1_val - p2_val) / (p1_val > 0 ? p1_val : 1)) * 100
        printf "  • %-10s -> Phase 1: %.4f | Phase 2: %.4f | Performance Drop: \033[1;31m-%.2f%%\033[0m\n", \
            pol, p1_val, p2_val, drop_pct
    }
}
' "$RESULTS_CSV"

# Section 4: OS-Level Resource Consumption
if [ -f "$SYSTEM_CSV" ] && [ "$(wc -l < "$SYSTEM_CSV")" -gt 1 ]; then
    echo -e "\n${CYAN}${BOLD}[4] HOST OS SYSTEM & KERNEL PROFILE (FROM /proc MONITOR)${RESET}\n"

    awk -F',' '
    NR > 1 {
        if ($3 > max_rss) max_rss = $3
        if ($6 > max_minflt) max_minflt = $6
        if ($7 > max_majflt) max_majflt = $7
        last_free = $8
        last_avail = $9
        last_swap = $10
        samples++
    }
    END {
        printf "  • Total Kernel Minor Page Faults (Soft Faults) : %s%d%s\n", "\033[1;32m", max_minflt, "\033[0m"
        printf "  • Total Kernel Major Page Faults (Disk I/O)    : %s%d%s\n", "\033[1;32m", max_majflt, "\033[0m"
        printf "  • Peak Process Resident Set Size (RSS)         : %s%.2f MB%s\n", "\033[1;32m", (max_rss / 1024), "\033[0m"
        printf "  • Final Host OS Available Memory               : %d MB\n", last_avail
        printf "  • Final Host OS Swap Used                      : %d MB\n", last_swap
        printf "  • Resource Metric Samples Captured             : %d samples\n", samples
    }
    ' "$SYSTEM_CSV"
fi

echo -e "\n${GREEN}${BOLD}✓ Analysis complete.${RESET}\n"
