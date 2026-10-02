def generate_trace(total_accesses=10000, num_pages=100, shift_point=5000, seed=42):
    import numpy as np
    import pandas as pd
    
    np.random.seed(seed)
    
    # Phase 1: Locality / Sequential
    phase1_length = shift_point
    phase1_accesses = []
    
    current_page = 0
    working_set_size = min(20, num_pages)
    for _ in range(phase1_length):
        if np.random.rand() < 0.8:
            current_page = (current_page + 1) % working_set_size
        else:
            current_page = np.random.randint(0, working_set_size)
        phase1_accesses.append(current_page)
        
    # Phase 2: Random / Bursty
    phase2_length = total_accesses - shift_point
    phase2_accesses = []
    
    for _ in range(phase2_length):
        current_page = np.random.randint(0, num_pages)
        phase2_accesses.append(current_page)
        
    trace_pages = phase1_accesses + phase2_accesses
    phases = ["Phase 1 (Locality)"] * phase1_length + ["Phase 2 (Random)"] * phase2_length
    
    df = pd.DataFrame({
        "step": range(total_accesses),
        "page": trace_pages,
        "phase": phases
    })
    
    return df

def generate_training_and_evaluation_traces(total_accesses=10000, num_pages=100, shift_point=5000, eval_seed=42, train_seed=43):
    eval_df = generate_trace(total_accesses, num_pages, shift_point, seed=eval_seed)
    train_df = generate_trace(total_accesses, num_pages, shift_point, seed=train_seed)
    return train_df, eval_df
