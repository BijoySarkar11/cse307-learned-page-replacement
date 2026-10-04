"""
Confidence Experiment (Bonus Track)
====================================
Runs all four algorithms with explanation instrumentation, collects
confidence scores, compares them against ground-truth (Optimal) evictions,
and produces:
  • results/tables/confidence_summary.csv
  • results/tables/confidence_calibration.csv
  • results/figures/figure4_confidence_calibration.png
  • results/figures/figure5_confidence_vs_accuracy.png
  • results/confidence_sample_explanations.txt
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from workload_generator import generate_training_and_evaluation_traces
from learned_policy import train_learned_policy
from explanation_engine import (
    InstrumentedFIFO, InstrumentedLRU, InstrumentedOptimal,
    InstrumentedLearned, annotate_correctness, EvictionExplanation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bucket_label(conf: float) -> str:
    """Map a confidence float to a 0.1-wide bucket label."""
    bucket = min(int(conf * 10), 9)
    lo = bucket / 10
    hi = lo + 0.1
    return f"{lo:.1f}–{hi:.1f}"


def build_calibration_table(explanations: list[EvictionExplanation],
                            algorithm: str) -> pd.DataFrame:
    """
    Build a calibration table: for each confidence bucket, what fraction
    of decisions were actually correct?
    """
    buckets: dict[str, dict] = {}
    for ex in explanations:
        if ex.was_correct is None:
            continue
        lbl = _bucket_label(ex.confidence)
        if lbl not in buckets:
            buckets[lbl] = {"total": 0, "correct": 0, "conf_sum": 0.0}
        buckets[lbl]["total"] += 1
        buckets[lbl]["correct"] += int(ex.was_correct)
        buckets[lbl]["conf_sum"] += ex.confidence

    rows = []
    for lbl in sorted(buckets.keys()):
        b = buckets[lbl]
        rows.append({
            "Algorithm": algorithm,
            "Confidence Bucket": lbl,
            "Decisions": b["total"],
            "Correct": b["correct"],
            "Accuracy": b["correct"] / b["total"] if b["total"] else 0,
            "Mean Confidence": b["conf_sum"] / b["total"] if b["total"] else 0,
        })
    return pd.DataFrame(rows)


def compute_summary(explanations: list[EvictionExplanation],
                    algorithm: str) -> dict:
    """Compute aggregate stats for one algorithm."""
    comparable = [e for e in explanations if e.was_correct is not None]
    if not comparable:
        return {
            "Algorithm": algorithm,
            "Eviction Events": len(explanations),
            "Comparable Events": 0,
            "Accuracy vs Optimal": 0.0,
            "Mean Confidence": 0.0,
            "Overconfident %": 0.0,
            "Underconfident %": 0.0,
            "ECE": 0.0,
        }

    corrects = [1 if e.was_correct else 0 for e in comparable]
    confs = [e.confidence for e in comparable]
    accuracy = sum(corrects) / len(corrects)
    mean_conf = sum(confs) / len(confs)

    # Overconfident: confidence > accuracy-in-bucket
    cal_df = build_calibration_table(explanations, algorithm)
    overconfident_events = 0
    underconfident_events = 0
    ece_sum = 0.0
    total_in_cal = 0
    for _, row in cal_df.iterrows():
        n = row["Decisions"]
        total_in_cal += n
        if row["Mean Confidence"] > row["Accuracy"]:
            overconfident_events += n
        elif row["Mean Confidence"] < row["Accuracy"]:
            underconfident_events += n
        ece_sum += n * abs(row["Mean Confidence"] - row["Accuracy"])

    ece = ece_sum / total_in_cal if total_in_cal else 0.0

    return {
        "Algorithm": algorithm,
        "Eviction Events": len(explanations),
        "Comparable Events": len(comparable),
        "Accuracy vs Optimal": round(accuracy, 4),
        "Mean Confidence": round(mean_conf, 4),
        "Overconfident %": round(100 * overconfident_events / total_in_cal, 2) if total_in_cal else 0,
        "Underconfident %": round(100 * underconfident_events / total_in_cal, 2) if total_in_cal else 0,
        "ECE": round(ece, 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_confidence_experiment():
    print("=" * 60)
    print("BONUS TRACK: Explanation Confidence Analysis")
    print("=" * 60)

    # Parameters (same as main experiment)
    TOTAL_ACCESSES = 10000
    NUM_PAGES = 100
    SHIFT_POINT = 5000
    NUM_FRAMES = 10          # focus on 10 frames for depth
    TRAIN_SEED = 43
    EVAL_SEED = 42

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

    os.makedirs(os.path.join(RESULTS_DIR, "tables"), exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "figures"), exist_ok=True)

    # 1. Generate traces
    print("\n[1/5] Generating traces ...")
    train_df, eval_df = generate_training_and_evaluation_traces(
        TOTAL_ACCESSES, NUM_PAGES, SHIFT_POINT,
        eval_seed=EVAL_SEED, train_seed=TRAIN_SEED,
    )
    eval_trace = eval_df["page"].tolist()
    train_trace = train_df["page"].tolist()

    # 2. Train learned policy
    print("[2/5] Training learned policy ...")
    model = train_learned_policy(train_trace, num_frames=NUM_FRAMES, window_size=100)

    # 3. Run instrumented algorithms
    print("[3/5] Running instrumented algorithms ...")
    policies = {
        "FIFO": InstrumentedFIFO(NUM_FRAMES),
        "LRU": InstrumentedLRU(NUM_FRAMES),
        "Optimal": InstrumentedOptimal(NUM_FRAMES),
        "Learned": InstrumentedLearned(NUM_FRAMES, model, window_size=100),
    }

    results = {}
    for name, pol in policies.items():
        res = pol.process_trace(eval_trace)
        results[name] = res
        print(f"  {name:10s} → {len(res['explanations']):5d} eviction events")

    # 4. Annotate correctness
    print("[4/5] Annotating correctness against Optimal baseline ...")
    optimal_explanations = results["Optimal"]["explanations"]
    for name in ["FIFO", "LRU", "Learned"]:
        annotate_correctness(results[name]["explanations"], optimal_explanations)
    # Optimal vs. itself is always correct.
    for ex in optimal_explanations:
        ex.was_correct = True
        ex.optimal_eviction = ex.evicted_page

    # 5. Analysis & output
    print("[5/5] Computing calibration and generating output ...\n")

    # --- Summary table ---
    summary_rows = []
    for name in ["FIFO", "LRU", "Optimal", "Learned"]:
        summary_rows.append(compute_summary(results[name]["explanations"], name))
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(os.path.join(RESULTS_DIR, "tables", "confidence_summary.csv"), index=False)

    print("CONFIDENCE SUMMARY (10 Frames)")
    print("-" * 90)
    print(f"{'Algorithm':<10} {'Events':>8} {'Comparable':>11} {'Accuracy':>10} "
          f"{'MeanConf':>10} {'Overconf%':>10} {'Underconf%':>11} {'ECE':>8}")
    print("-" * 90)
    for _, r in summary_df.iterrows():
        print(f"{r['Algorithm']:<10} {r['Eviction Events']:>8} "
              f"{r['Comparable Events']:>11} {r['Accuracy vs Optimal']:>10.4f} "
              f"{r['Mean Confidence']:>10.4f} {r['Overconfident %']:>10.2f} "
              f"{r['Underconfident %']:>11.2f} {r['ECE']:>8.4f}")

    # --- Calibration table ---
    cal_frames = []
    for name in ["FIFO", "LRU", "Optimal", "Learned"]:
        cal_frames.append(build_calibration_table(results[name]["explanations"], name))
    cal_df = pd.concat(cal_frames, ignore_index=True)
    cal_df.to_csv(os.path.join(RESULTS_DIR, "tables", "confidence_calibration.csv"), index=False)

    # --- Sample explanations ---
    sample_path = os.path.join(RESULTS_DIR, "confidence_sample_explanations.txt")
    with open(sample_path, "w") as f:
        for name in ["FIFO", "LRU", "Optimal", "Learned"]:
            f.write(f"\n{'='*70}\n")
            f.write(f" {name} — Sample Explanations (first 5 eviction events)\n")
            f.write(f"{'='*70}\n\n")
            for ex in results[name]["explanations"][:5]:
                correct_str = (
                    "N/A" if ex.was_correct is None
                    else ("✓ CORRECT" if ex.was_correct else "✗ INCORRECT")
                )
                f.write(f"  Step {ex.step}: Request page {ex.requested_page}\n")
                f.write(f"  → {ex.explanation}\n")
                f.write(f"  Confidence: {ex.confidence:.4f}  |  "
                        f"Correct: {correct_str}")
                if ex.optimal_eviction is not None and not ex.was_correct:
                    f.write(f"  (Optimal would evict page {ex.optimal_eviction})")
                f.write("\n\n")
    print(f"\nSample explanations saved to {sample_path}")

    # --- FIGURE 4: Calibration diagram ---
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {"FIFO": "#1f77b4", "LRU": "#ff7f0e", "Optimal": "#2ca02c", "Learned": "#d62728"}

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect Calibration")

    for name in ["FIFO", "LRU", "Learned"]:
        sub = cal_df[cal_df["Algorithm"] == name]
        if sub.empty:
            continue
        ax.scatter(sub["Mean Confidence"], sub["Accuracy"],
                   color=colors[name], s=sub["Decisions"] * 0.4 + 20,
                   label=name, alpha=0.8, edgecolors="white", linewidths=0.5)

    ax.set_xlabel("Mean Self-Rated Confidence")
    ax.set_ylabel("Actual Accuracy (vs Optimal)")
    ax.set_title("Confidence Calibration Diagram (10 Frames)")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "figures", "figure4_confidence_calibration.png"), dpi=150)
    plt.close(fig)
    print("Saved figure4_confidence_calibration.png")

    # --- FIGURE 5: Bar chart — Accuracy vs Mean Confidence ---
    fig, ax = plt.subplots(figsize=(8, 5))
    alg_names = ["FIFO", "LRU", "Learned"]
    x = np.arange(len(alg_names))
    width = 0.35

    accuracies = [summary_df[summary_df["Algorithm"] == n]["Accuracy vs Optimal"].values[0]
                  for n in alg_names]
    mean_confs = [summary_df[summary_df["Algorithm"] == n]["Mean Confidence"].values[0]
                  for n in alg_names]

    bars1 = ax.bar(x - width / 2, accuracies, width, label="Actual Accuracy",
                   color=["#1f77b4", "#ff7f0e", "#d62728"], alpha=0.85)
    bars2 = ax.bar(x + width / 2, mean_confs, width, label="Mean Confidence",
                   color=["#1f77b4", "#ff7f0e", "#d62728"], alpha=0.45,
                   edgecolor=["#1f77b4", "#ff7f0e", "#d62728"], linewidth=1.5)

    for bar, val in zip(bars1, accuracies):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.2f}", ha="center", fontsize=9)
    for bar, val in zip(bars2, mean_confs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.2f}", ha="center", fontsize=9)

    ax.set_ylabel("Score")
    ax.set_title("Actual Accuracy vs Self-Rated Confidence (10 Frames)")
    ax.set_xticks(x)
    ax.set_xticklabels(alg_names)
    ax.set_ylim(0, 1.2)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "figures", "figure5_confidence_vs_accuracy.png"), dpi=150)
    plt.close(fig)
    print("Saved figure5_confidence_vs_accuracy.png")

    # --- FIGURE 6: Confidence distribution histograms ---
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax_item, name in zip(axes.flat, ["FIFO", "LRU", "Optimal", "Learned"]):
        confs = [e.confidence for e in results[name]["explanations"]]
        ax_item.hist(confs, bins=20, color=colors[name], alpha=0.75, edgecolor="white")
        ax_item.set_title(f"{name} Confidence Distribution")
        ax_item.set_xlabel("Confidence")
        ax_item.set_ylabel("Count")
        ax_item.set_xlim(0, 1.05)
        ax_item.axvline(x=np.mean(confs), color="black", linestyle="--",
                        label=f"Mean={np.mean(confs):.3f}")
        ax_item.legend(fontsize=8)
    fig.suptitle("Confidence Score Distributions (10 Frames)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(RESULTS_DIR, "figures", "figure6_confidence_distributions.png"), dpi=150)
    plt.close(fig)
    print("Saved figure6_confidence_distributions.png")

    print("\n" + "=" * 60)
    print("Confidence experiment complete.")
    print("Results saved to: results/tables/ and results/figures/")
    print("=" * 60)


if __name__ == "__main__":
    run_confidence_experiment()
