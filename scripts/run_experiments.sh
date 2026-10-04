#!/usr/bin/env bash
# ==============================================================================
# CSE-307: Operating Systems - Master Experiment Runner with OS Profiling
# Orchestrates full benchmark suite, attaches system resource monitoring,
# and generates terminal analytical summaries.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Terminal Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo -e "\n${BOLD}${BLUE}=================================================================${RESET}"
echo -e "${BOLD}${BLUE}     CSE-307: AUTOMATED BENCHMARK & OS MONITORING RUNNER         ${RESET}"
echo -e "${BOLD}${BLUE}=================================================================${RESET}\n"

# 1. Environment Verification
cd "$PROJECT_ROOT"

if [ -f ".venv/bin/activate" ]; then
    echo -e "${CYAN}→ Activating virtual environment (.venv)...${RESET}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}→ Using system python3...${RESET}"
else
    echo -e "\033[0;31mError: python3 not found!${RESET}" >&2
    exit 1
fi

# Ensure output directories exist
mkdir -p "$PROJECT_ROOT/results/figures" "$PROJECT_ROOT/results/tables" "$PROJECT_ROOT/data/traces"

MONITOR_SCRIPT="$SCRIPT_DIR/monitor_system.sh"
SYSTEM_METRICS="$PROJECT_ROOT/results/os_system_metrics.csv"

# Function to clean up background monitor upon exit
MONITOR_PID=""
cleanup() {
    if [ -n "$MONITOR_PID" ] && kill -0 "$MONITOR_PID" 2>/dev/null; then
        echo -e "\n${YELLOW}→ Stopping OS resource monitor...${RESET}"
        kill "$MONITOR_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# 2. Run Main Experiment with OS Profiling
echo -e "${CYAN}→ Launching main experiment workload (src/experiment.py)...${RESET}"

# Launch experiment in background to get its PID
python3 "$PROJECT_ROOT/src/experiment.py" &
EXP_PID=$!

# Launch OS kernel / resource monitor tracking EXP_PID
if [ -x "$MONITOR_SCRIPT" ]; then
    echo -e "${CYAN}→ Attaching OS kernel /proc & memory monitor to PID $EXP_PID...${RESET}"
    "$MONITOR_SCRIPT" "$EXP_PID" "$SYSTEM_METRICS" 0.3 &
    MONITOR_PID=$!
fi

# Wait for experiment to finish
wait "$EXP_PID"
echo -e "${GREEN}✓ Main experiment finished successfully.${RESET}"

# Give monitor a moment to finalize
sleep 0.5
if [ -n "$MONITOR_PID" ] && kill -0 "$MONITOR_PID" 2>/dev/null; then
    kill "$MONITOR_PID" 2>/dev/null || true
    MONITOR_PID=""
fi

# 3. Invoke Automated Results Analysis
echo -e "\n${CYAN}→ Invoking Bash data analysis pipeline...${RESET}"
bash "$SCRIPT_DIR/analyze_results.sh"

echo -e "${BOLD}${GREEN}=================================================================${RESET}"
echo -e "${BOLD}${GREEN}   All experiments and OS profiling completed successfully!     ${RESET}"
echo -e "${BOLD}${GREEN}=================================================================${RESET}\n"
