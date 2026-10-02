# Learning-Augmented Page Replacement

## Course
CSE-307 Operating Systems

## Track
Track 1 — Learned Page Replacement

## Problem
Modern operating systems rely heavily on page replacement algorithms to manage physical memory efficiently when it becomes full. Traditional algorithms like FIFO and LRU are simple and effective for general workloads but can be suboptimal for specific application access patterns. The Optimal algorithm (Belady's) provides a theoretical lower bound on page faults by looking at future references, but it cannot be implemented in a real system. This project investigates whether a lightweight machine learning model (Decision Tree) can learn to predict the optimal eviction candidate using only historical access features, acting as a "Learning-Augmented" heuristic.

## Classical Algorithms
This project implements the following classical algorithms for comparison:
- **FIFO (First-In-First-Out):** Evicts the oldest page in memory.
- **LRU (Least Recently Used):** Evicts the page that has not been used for the longest time, exploiting temporal locality.
- **Optimal (Belady's):** An offline theoretical baseline that evicts the page whose next use is farthest in the future.

## Learned Component
The learned policy uses a lightweight `DecisionTreeClassifier` (max depth of 5) to predict eviction candidates. 
- **Features:** It uses simple history-based features: `recency`, `frequency` (in a recent window), `global_frequency`, `age`, `recent_frequency`, and `normalized_recency`.
- **Training Labels:** The model is trained on a separate synthetic trace where the Optimal algorithm is used to label the best eviction candidate (1 for optimal, 0 for others).
- **Eviction Decision:** During deployment, when a page fault occurs and memory is full, the model scores all resident pages based on current features. The page with the highest probability score for being the optimal candidate is evicted. Ties are broken using LRU.

## Workload Shift
To test the adaptability of the algorithms, the evaluation trace contains a deliberate workload shift:
- **Phase 1 (Locality):** The first half of the trace consists of sequential/locality-heavy accesses with a small working set (e.g., first 20 pages).
- **Phase 2 (Random):** The second half abruptly shifts to a completely random access pattern across all 100 pages, representing bursty and unpredictable workloads.

## Experimental Setup
- **Total accesses:** 10000
- **Number of pages:** 100
- **Memory frames:** 5, 10, 20
- **Shift point:** 5000 (Access 5000)
- **Random seed:** 42 for Evaluation, 43 for Training

## Metrics
- **Hit ratio:** Number of cache hits divided by total accesses.
- **Page faults:** Number of times a requested page was not in memory.
- **Phase degradation:** The drop in hit ratio from Phase 1 to Phase 2.

## Installation
Ensure you have Python 3 installed.
```bash
python3 -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

## Run
Run the full experiment:
```bash
python src/experiment.py
```

Run a quick interactive terminal demo:
```bash
python demo/demo.py
```

## Results
Running the experiment evaluates FIFO, LRU, Optimal, and the Learned policy across different memory frame sizes (5, 10, 20). The raw results are saved to `results/raw_results.csv` and summary tables in `results/tables/`. 

Visualizations are saved in `results/figures/`:
- `figure1_hit_ratio.png`: Compares the overall hit ratio of all algorithms.
- `figure2_cumulative_faults.png`: Shows the cumulative page faults over time, marking the workload shift.
- `figure3_phase_shift.png`: Demonstrates the hit ratio before and after the workload shift.

On 10 memory frames, the Learned policy achieves an overall hit ratio of 0.2883, outperforming both FIFO (0.2216) and LRU (0.2199). During Phase 1, the Learned policy adapted well to the locality (hit ratio 0.4772), but degraded in Phase 2 during the random workload (hit ratio 0.0994), heavily mirroring the baseline optimal degradation pattern.

## Repository Structure
- `src/`: Python source code (algorithms, workload generator, features).
- `data/`: Traces.
- `results/`: Output CSV tables and matplotlib figures.
- `report/`: LaTeX source for the 3-page term paper.
- `demo/`: Lightweight terminal demo script.

## AI Assistance Disclosure
AI coding assistants were used to support implementation, debugging, and documentation. The experimental design, execution, results, interpretation, and final analysis were independently reviewed and understood by the author.
