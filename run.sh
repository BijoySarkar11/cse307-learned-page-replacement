#!/usr/bin/env bash
# ==============================================================================
# CSE-307: Operating Systems - Unified Project Runner
# 
# Usage:
#   ./run.sh        -> Runs full experiment benchmark (10,000 accesses across 5, 10, 20 frames)
#   ./run.sh demo   -> Runs quick test experiment (1,000 accesses on 10 frames)
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Auto-activate virtual environment if available
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

MODE="${1:-all}"

if [ "$MODE" = "demo" ] || [ "$MODE" = "quick" ]; then
    echo -e "\n\033[1;36m▶ Running Quick Test Experiment (src/quick_test.py)...\033[0m"
    python3 src/quick_test.py
    exit 0
fi

# Default: Run experiment benchmark
echo -e "\n\033[1;34m=================================================================\033[0m"
echo -e "\033[1;34m  CSE-307: RUNNING PAGE REPLACEMENT EXPERIMENT BENCHMARK          \033[0m"
echo -e "\033[1;34m=================================================================\033[0m"

bash scripts/run_experiments.sh

echo -e "\033[1;32m=================================================================\033[0m"
echo -e "\033[1;32m✓ Benchmark completed successfully!\033[0m"
echo -e "  • Raw Results : results/raw_results.csv"
echo -e "  • Figures     : results/figures/"
echo -e "\033[1;32m=================================================================\033[0m\n"
