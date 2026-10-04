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

## How to Run

You only need **two simple commands**:

### 1. Run the Full Experiment Benchmark
Runs the 10,000-access page replacement simulation across 5, 10, and 20 frames, compares all algorithms, and saves the output charts to `results/figures/`:
```bash
./run.sh
```

### 2. Run the Quick Test Experiment
Runs a lightweight simulation of 1,000 accesses with the workload shift and displays a fast comparison table:
```bash
./run.sh quick
# (or: python src/quick_test.py)
```

## Results
Running the experiment evaluates FIFO, LRU, Optimal, and the Learned policy across different memory frame sizes (5, 10, 20). The raw results are saved to `results/raw_results.csv` and summary tables in `results/tables/`. 

Visualizations are saved in `results/figures/`:
- `figure1_hit_ratio.png`: Compares the overall hit ratio of all algorithms.
- `figure2_cumulative_faults.png`: Shows the cumulative page faults over time, marking the workload shift.
- `figure3_phase_shift.png`: Demonstrates the hit ratio before and after the workload shift.

On 10 memory frames, the Learned policy achieves an overall hit ratio of 0.2883, outperforming both FIFO (0.2216) and LRU (0.2199). During Phase 1, the Learned policy adapted well to the locality (hit ratio 0.4772), but degraded in Phase 2 during the random workload (hit ratio 0.0994), heavily mirroring the baseline optimal degradation pattern.

## Bonus Track — Explanation Confidence
This project implements the optional Explanation Confidence bonus track. A **rule-based template generator** (no external API required) produces a short natural-language explanation of each algorithm's eviction decision at every step, along with a self-rated confidence score (0.0–1.0).

### How It Works
- **Template Engine** (`src/explanation_engine.py`): Each algorithm (FIFO, LRU, Optimal, Learned) has a dedicated explainer class that generates human-readable text describing *why* a particular page was evicted and computes a confidence score from domain-specific heuristics:
  - **FIFO**: Confidence decreases with higher recent page diversity (many unique pages → FIFO is a worse heuristic).
  - **LRU**: Confidence scales with the recency "dominance gap" between the victim and the runner-up, penalised by high workload diversity.
  - **Optimal**: Confidence is always near 1.0 (perfect future knowledge).
  - **Learned**: Confidence is derived from the model's eviction probability and the margin over the runner-up candidate.
- **Ground-Truth Comparison**: Each eviction is compared against the Optimal baseline to determine whether it was "correct".
- **Calibration Analysis**: The Expected Calibration Error (ECE), overconfidence %, and per-bucket accuracy are computed and visualised.

### Running the Bonus Track
The confidence experiment runs automatically as part of the main experiment:
```bash
python src/experiment.py
```

Or run it standalone:
```bash
python src/confidence_experiment.py
```

### Bonus Track Outputs
- `results/tables/confidence_summary.csv` — Aggregate metrics (accuracy, mean confidence, ECE, overconfidence %).
- `results/tables/confidence_calibration.csv` — Per-bucket calibration data.
- `results/confidence_sample_explanations.txt` — Sample natural-language explanations for each algorithm.
- `results/figures/figure4_confidence_calibration.png` — Calibration diagram (confidence vs accuracy scatter).
- `results/figures/figure5_confidence_vs_accuracy.png` — Bar chart comparing actual accuracy to self-rated confidence.
- `results/figures/figure6_confidence_distributions.png` — Histograms of confidence score distributions.

## Repository Structure
- `src/`: Python source code (algorithms, workload generator, features).
  - `src/experiment.py`: Main benchmark simulation runner.
  - `src/quick_test.py`: Fast lightweight simulation script (1,000 accesses).
  - `src/explanation_engine.py`: Rule-based explanation and confidence generator (Bonus Track).
  - `src/confidence_experiment.py`: Standalone experiment runner for the Bonus Track.
- `data/`: Traces.
- `results/`: Output CSV tables and matplotlib figures.

## AI Assistance Disclosure
Google Antigravity was used as an AI coding assistant for code implementation and debugging assistance, in accordance with Section 2 of the course brief. All experimental design, workload parameters, results interpretation, and final analysis were independently conducted and verified by the author.
