import os
import pandas as pd
import matplotlib.pyplot as plt

from workload_generator import generate_training_and_evaluation_traces
from page_replacement import FIFO, LRU, Optimal
from learned_policy import train_learned_policy, LearnedPageReplacement
from evaluation import calculate_metrics

def run_experiment():
    print("==================================================")
    print("CSE-307 PAGE REPLACEMENT EXPERIMENT")
    print("==================================================")

    # Parameters
    TOTAL_ACCESSES = 10000
    NUM_PAGES = 100
    SHIFT_POINT = 5000
    FRAMES_LIST = [5, 10, 20]
    TRAIN_SEED = 43
    EVAL_SEED = 42

    print(f"\nTrace:")
    print(f"Total accesses: {TOTAL_ACCESSES}")
    print(f"Pages: {NUM_PAGES}")
    print(f"Shift point: {SHIFT_POINT}")
    print(f"Frames evaluated: {FRAMES_LIST}")

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")

    os.makedirs(os.path.join(DATA_DIR, "traces"), exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "tables"), exist_ok=True)
    os.makedirs(os.path.join(RESULTS_DIR, "figures"), exist_ok=True)

    # 1. Generate Traces
    print("\nGenerating traces...")
    train_df, eval_df = generate_training_and_evaluation_traces(
        TOTAL_ACCESSES, NUM_PAGES, SHIFT_POINT, eval_seed=EVAL_SEED, train_seed=TRAIN_SEED
    )
    
    eval_df.to_csv(os.path.join(DATA_DIR, "traces", "trace.csv"), index=False)
    
    eval_trace = eval_df["page"].tolist()
    phase_labels = eval_df["phase"].tolist()
    train_trace = train_df["page"].tolist()

    all_metrics = []
    policy_faults_over_time = {} # For figure 2
    hit_ratios_for_fig = {f: {} for f in FRAMES_LIST} # For figure 1 and 3

    # Run for different frame sizes
    for num_frames in FRAMES_LIST:
        print(f"\n--- Running for Memory Frames = {num_frames} ---")
        
        # 2. Train Learned Policy
        print("Training learned policy on separate training trace...")
        model = train_learned_policy(train_trace, num_frames=num_frames, window_size=100)
        
        policies = {
            "FIFO": FIFO(num_frames),
            "LRU": LRU(num_frames),
            "Optimal": Optimal(num_frames),
            "Learned": LearnedPageReplacement(num_frames, model, window_size=100)
        }
        
        # For capturing cumulative faults for figure 2 (only for frames=10 for cleaner plot)
        if num_frames == 10:
            for p_name in policies.keys():
                policy_faults_over_time[p_name] = []

        print(f"{'Policy':<15} {'Hits':<10} {'Faults':<10} {'Hit Ratio':<10}")
        print("-" * 50)
        
        for name, policy in policies.items():
            result = policy.process_trace(eval_trace)
            
            # Cumulative faults for plot
            if num_frames == 10:
                cum_faults = 0
                cum_faults_list = []
                for hit in result["hit_status"]:
                    if not hit:
                        cum_faults += 1
                    cum_faults_list.append(cum_faults)
                policy_faults_over_time[name] = cum_faults_list
                
            metrics_df = calculate_metrics(result["hit_status"], phase_labels, name, num_frames)
            all_metrics.append(metrics_df)
            
            # Extract full trace hit ratio for print summary
            full_hit_ratio = metrics_df[metrics_df["Phase"] == "Full Trace"]["Hit Ratio"].values[0]
            hits = metrics_df[metrics_df["Phase"] == "Full Trace"]["Hits"].values[0]
            faults = metrics_df[metrics_df["Phase"] == "Full Trace"]["Faults"].values[0]
            
            print(f"{name:<15} {hits:<10} {faults:<10} {full_hit_ratio:.4f}")
            
            # Store hit ratios for figures
            phase1_hr = metrics_df[metrics_df["Phase"] == "Phase 1 (Locality)"]["Hit Ratio"].values[0]
            phase2_hr = metrics_df[metrics_df["Phase"] == "Phase 2 (Random)"]["Hit Ratio"].values[0]
            hit_ratios_for_fig[num_frames][name] = {
                "Full": full_hit_ratio,
                "Phase 1": phase1_hr,
                "Phase 2": phase2_hr
            }

    # 3. Combine Metrics
    final_metrics_df = pd.concat(all_metrics, ignore_index=True)
    
    # Save CSVs
    final_metrics_df.to_csv(os.path.join(RESULTS_DIR, "raw_results.csv"), index=False)
    summary_df = final_metrics_df[final_metrics_df["Phase"] == "Full Trace"]
    summary_df.to_csv(os.path.join(RESULTS_DIR, "tables", "summary_results.csv"), index=False)
    phase_df = final_metrics_df[final_metrics_df["Phase"] != "Full Trace"]
    phase_df.to_csv(os.path.join(RESULTS_DIR, "tables", "phase_results.csv"), index=False)

    print("\nPHASE COMPARISON (Frames = 10)")
    print("-" * 50)
    for name in ["FIFO", "LRU", "Optimal", "Learned"]:
        p1 = hit_ratios_for_fig[10][name]["Phase 1"]
        p2 = hit_ratios_for_fig[10][name]["Phase 2"]
        deg = p1 - p2
        print(f"{name:<10} Phase 1: {p1:.4f} | Phase 2: {p2:.4f} | Degradation: {deg:.4f}")

    # 4. Visualizations
    
    # FIGURE 1: Hit ratio by algorithm (for Frames = 10)
    plt.figure(figsize=(8, 5))
    names = list(hit_ratios_for_fig[10].keys())
    full_hrs = [hit_ratios_for_fig[10][n]["Full"] for n in names]
    
    plt.bar(names, full_hrs, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
    plt.title('Overall Hit Ratio by Algorithm (10 Frames)')
    plt.ylabel('Hit Ratio')
    plt.xlabel('Policy')
    plt.ylim(0, 1.0)
    for i, v in enumerate(full_hrs):
        plt.text(i, v + 0.02, f"{v:.2f}", ha='center')
    plt.savefig(os.path.join(RESULTS_DIR, "figures", "figure1_hit_ratio.png"))
    plt.close()

    # FIGURE 2: Page faults over time
    plt.figure(figsize=(10, 6))
    for name, faults_over_time in policy_faults_over_time.items():
        plt.plot(range(TOTAL_ACCESSES), faults_over_time, label=name)
        
    plt.axvline(x=SHIFT_POINT, color='k', linestyle='--', label='Workload Shift')
    plt.title('Cumulative Page Faults Over Time (10 Frames)')
    plt.xlabel('Access Number')
    plt.ylabel('Cumulative Page Faults')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(RESULTS_DIR, "figures", "figure2_cumulative_faults.png"))
    plt.close()

    # FIGURE 3: Before vs after shift
    plt.figure(figsize=(10, 6))
    x = range(len(names))
    width = 0.35
    
    p1_hrs = [hit_ratios_for_fig[10][n]["Phase 1"] for n in names]
    p2_hrs = [hit_ratios_for_fig[10][n]["Phase 2"] for n in names]
    
    plt.bar([i - width/2 for i in x], p1_hrs, width, label='Phase 1 (Locality)')
    plt.bar([i + width/2 for i in x], p2_hrs, width, label='Phase 2 (Random)')
    
    plt.title('Hit Ratio Before vs After Workload Shift (10 Frames)')
    plt.ylabel('Hit Ratio')
    plt.xticks(x, names)
    plt.legend()
    plt.ylim(0, 1.0)
    plt.savefig(os.path.join(RESULTS_DIR, "figures", "figure3_phase_shift.png"))
    plt.close()

    print("\n==================================================")
    print("Results saved to:")
    print("results/raw_results.csv")
    print("Figures saved to:")
    print("results/figures/")
    print("==================================================")

    # --- Bonus Track: Explanation Confidence ---
    print("\n")
    from confidence_experiment import run_confidence_experiment
    run_confidence_experiment()

if __name__ == "__main__":
    run_experiment()
