class FeatureExtractor:
    def __init__(self, window_size=100):
        self.window_size = window_size
        self.time_step = 0
        self.last_access = {}
        self.global_freq = {}
        self.entry_time = {}
        self.recent_accesses = []
        self.window_counts = {}
        
    def record_access(self, page, in_memory):
        self.time_step += 1
        
        self.last_access[page] = self.time_step
        self.global_freq[page] = self.global_freq.get(page, 0) + 1
        
        self.recent_accesses.append(page)
        self.window_counts[page] = self.window_counts.get(page, 0) + 1
        
        if len(self.recent_accesses) > self.window_size:
            evicted_from_window = self.recent_accesses.pop(0)
            self.window_counts[evicted_from_window] -= 1
            
        if not in_memory:
            self.entry_time[page] = self.time_step
            
    def get_features(self, page):
        recency = self.time_step - self.last_access.get(page, 0) if page in self.last_access else self.time_step
        freq = self.window_counts.get(page, 0)
        global_freq = self.global_freq.get(page, 0)
        age = self.time_step - self.entry_time.get(page, self.time_step)
        recent_frequency = freq 
        normalized_recency = recency / self.window_size if self.window_size > 0 else 0
        
        return [recency, freq, global_freq, age, recent_frequency, normalized_recency]
    
    @staticmethod
    def feature_names():
        return ["recency", "frequency", "global_frequency", "age", "recent_frequency", "normalized_recency"]
