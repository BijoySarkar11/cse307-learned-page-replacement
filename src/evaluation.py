import pandas as pd

def calculate_metrics(hit_status, phase_labels, policy_name, num_frames):
    df = pd.DataFrame({
        'hit': hit_status,
        'phase': phase_labels
    })
    
    metrics = []
    
    for phase in df['phase'].unique():
        phase_df = df[df['phase'] == phase]
        hits = phase_df['hit'].sum()
        total = len(phase_df)
        faults = total - hits
        metrics.append({
            'Policy': policy_name,
            'Frames': num_frames,
            'Phase': phase,
            'Hits': hits,
            'Faults': faults,
            'Hit Ratio': hits / total if total > 0 else 0
        })
        
    hits = df['hit'].sum()
    total = len(df)
    faults = total - hits
    metrics.append({
        'Policy': policy_name,
        'Frames': num_frames,
        'Phase': 'Full Trace',
        'Hits': hits,
        'Faults': faults,
        'Hit Ratio': hits / total if total > 0 else 0
    })
    
    return pd.DataFrame(metrics)
