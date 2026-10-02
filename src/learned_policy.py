import numpy as np
from sklearn.tree import DecisionTreeClassifier
from features import FeatureExtractor

def generate_training_data(trace, num_frames, window_size=100):
    feature_extractor = FeatureExtractor(window_size=window_size)
    
    next_use_dict = {}
    for i in range(len(trace) - 1, -1, -1):
        p = trace[i]
        if p not in next_use_dict:
            next_use_dict[p] = []
        next_use_dict[p].append(i)
        
    frames = []
    X = []
    y = []
    
    for i, page in enumerate(trace):
        next_use_dict[page].pop()
        
        in_memory = page in frames
        
        if not in_memory:
            if len(frames) < num_frames:
                frames.append(page)
            else:
                farthest_use = -1
                optimal_evict = None
                for resident in frames:
                    next_uses = next_use_dict.get(resident, [])
                    if not next_uses:
                        optimal_evict = resident
                        break
                    else:
                        next_use_idx = next_uses[-1]
                        if next_use_idx > farthest_use:
                            farthest_use = next_use_idx
                            optimal_evict = resident
                
                for resident in frames:
                    features = feature_extractor.get_features(resident)
                    label = 1 if resident == optimal_evict else 0
                    X.append(features)
                    y.append(label)
                
                frames.remove(optimal_evict)
                frames.append(page)
                
        feature_extractor.record_access(page, in_memory)
        
    return X, y

def train_learned_policy(train_trace, num_frames, window_size=100):
    X, y = generate_training_data(train_trace, num_frames, window_size)
    model = DecisionTreeClassifier(max_depth=5, random_state=42)
    if len(set(y)) > 1:
        model.fit(X, y)
    else:
        model.fit(X, [0]*len(y))
    return model

class LearnedPageReplacement:
    def __init__(self, num_frames, model, window_size=100):
        self.num_frames = num_frames
        self.model = model
        self.window_size = window_size
        self.frames = []
        self.page_faults = 0
        self.hits = 0

    def process_trace(self, trace):
        self.frames = []
        self.page_faults = 0
        self.hits = 0
        hit_status = []
        feature_extractor = FeatureExtractor(window_size=self.window_size)
        
        for i, page in enumerate(trace):
            in_memory = page in self.frames
            
            if in_memory:
                self.hits += 1
                hit_status.append(True)
            else:
                self.page_faults += 1
                hit_status.append(False)
                if len(self.frames) < self.num_frames:
                    self.frames.append(page)
                else:
                    max_score = -1
                    candidates = []
                    
                    for resident in self.frames:
                        features = feature_extractor.get_features(resident)
                        if hasattr(self.model, 'predict_proba') and len(self.model.classes_) > 1:
                            proba = self.model.predict_proba([features])[0]
                            # Assuming class '1' is the second class (index 1)
                            score = proba[1] if 1 in self.model.classes_ else 0
                        else:
                            score = self.model.predict([features])[0]
                            
                        if score > max_score:
                            max_score = score
                            candidates = [resident]
                        elif score == max_score:
                            candidates.append(resident)
                            
                    if len(candidates) > 1:
                        # Tie breaker: max recency (LRU fallback)
                        best_candidate = candidates[0]
                        max_recency = -1
                        for c in candidates:
                            rec = feature_extractor.get_features(c)[0] # recency
                            if rec > max_recency:
                                max_recency = rec
                                best_candidate = c
                        best_evict_page = best_candidate
                    else:
                        best_evict_page = candidates[0]
                        
                    self.frames.remove(best_evict_page)
                    self.frames.append(page)
            
            feature_extractor.record_access(page, in_memory)
            
        return {
            "page_faults": self.page_faults,
            "hits": self.hits,
            "hit_status": hit_status
        }
