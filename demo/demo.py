import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from workload_generator import generate_training_and_evaluation_traces
from page_replacement import FIFO, LRU, Optimal
from learned_policy import train_learned_policy, LearnedPageReplacement
from evaluation import calculate_metrics

def main():
    print("\n" + "="*50)
    print("DEMO: Learning-Augmented Page Replacement")
    print("="*50)
    
    print("\n1. Explaining the Project:")
    print("We compare classical page replacement algorithms (FIFO, LRU, Optimal)")
    print("against a Lightweight Learned Policy (Decision Tree) that predicts")
    print("the optimal page to evict based on features like recency and frequency.")
    
    TOTAL_ACCESSES = 1000
    NUM_PAGES = 50
    SHIFT_POINT = 500
    NUM_FRAMES = 10
    
    print(f"\n2. Simulating a Workload Shift:")
    print(f"Total accesses: {TOTAL_ACCESSES}")
    print(f"Shift at access: {SHIFT_POINT}")
    print("Phase 1: High Locality (small working set)")
    print("Phase 2: Random / Bursty Access (larger working set)")
    
    train_df, eval_df = generate_training_and_evaluation_traces(
        TOTAL_ACCESSES, NUM_PAGES, SHIFT_POINT
    )
    
    eval_trace = eval_df["page"].tolist()
    phase_labels = eval_df["phase"].tolist()
    train_trace = train_df["page"].tolist()
    
    print("\n3. Training the Learned Policy (on separate trace)...")
    model = train_learned_policy(train_trace, num_frames=NUM_FRAMES)
    
    policies = {
        "FIFO": FIFO(NUM_FRAMES),
        "LRU": LRU(NUM_FRAMES),
        "Optimal": Optimal(NUM_FRAMES),
        "Learned": LearnedPageReplacement(NUM_FRAMES, model)
    }
    
    print("\n4. Running Algorithms on Evaluation Trace...\n")
    print(f"{'Policy':<15} {'Hits':<10} {'Faults':<10} {'Hit Ratio':<10}")
    print("-" * 50)
    
    metrics = []
    for name, policy in policies.items():
        res = policy.process_trace(eval_trace)
        df_m = calculate_metrics(res["hit_status"], phase_labels, name, NUM_FRAMES)
        metrics.append(df_m)
        full_hr = df_m[df_m["Phase"] == "Full Trace"]["Hit Ratio"].values[0]
        hits = df_m[df_m["Phase"] == "Full Trace"]["Hits"].values[0]
        faults = df_m[df_m["Phase"] == "Full Trace"]["Faults"].values[0]
        print(f"{name:<15} {hits:<10} {faults:<10} {full_hr:.4f}")
        
    print("\n" + "="*50)
    print("For full metrics and generated figures, please run:")
    print("python src/experiment.py")
    print("Figures will be saved in: results/figures/")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
