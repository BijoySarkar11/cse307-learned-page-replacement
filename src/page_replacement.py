class PageReplacementAlgorithm:
    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.frames = []
        self.page_faults = 0
        self.hits = 0

    def process_trace(self, trace):
        raise NotImplementedError


class FIFO(PageReplacementAlgorithm):
    def process_trace(self, trace):
        self.frames = []
        self.page_faults = 0
        self.hits = 0
        hit_status = []
        
        for page in trace:
            if page in self.frames:
                self.hits += 1
                hit_status.append(True)
            else:
                self.page_faults += 1
                hit_status.append(False)
                if len(self.frames) < self.num_frames:
                    self.frames.append(page)
                else:
                    self.frames.pop(0)
                    self.frames.append(page)
                    
        return {
            "page_faults": self.page_faults,
            "hits": self.hits,
            "hit_status": hit_status
        }


class LRU(PageReplacementAlgorithm):
    def process_trace(self, trace):
        self.frames = []
        self.page_faults = 0
        self.hits = 0
        hit_status = []
        
        for page in trace:
            if page in self.frames:
                self.hits += 1
                hit_status.append(True)
                self.frames.remove(page)
                self.frames.append(page)
            else:
                self.page_faults += 1
                hit_status.append(False)
                if len(self.frames) < self.num_frames:
                    self.frames.append(page)
                else:
                    self.frames.pop(0)
                    self.frames.append(page)
                    
        return {
            "page_faults": self.page_faults,
            "hits": self.hits,
            "hit_status": hit_status
        }


class Optimal(PageReplacementAlgorithm):
    def process_trace(self, trace):
        self.frames = []
        self.page_faults = 0
        self.hits = 0
        hit_status = []
        
        next_use_dict = {}
        for i in range(len(trace) - 1, -1, -1):
            p = trace[i]
            if p not in next_use_dict:
                next_use_dict[p] = []
            next_use_dict[p].append(i)
            
        for i, page in enumerate(trace):
            next_use_dict[page].pop()
            
            if page in self.frames:
                self.hits += 1
                hit_status.append(True)
            else:
                self.page_faults += 1
                hit_status.append(False)
                if len(self.frames) < self.num_frames:
                    self.frames.append(page)
                else:
                    farthest_use = -1
                    page_to_evict = None
                    for resident_page in self.frames:
                        next_uses = next_use_dict.get(resident_page, [])
                        if not next_uses:
                            page_to_evict = resident_page
                            break
                        else:
                            next_use_idx = next_uses[-1]
                            if next_use_idx > farthest_use:
                                farthest_use = next_use_idx
                                page_to_evict = resident_page
                    
                    self.frames.remove(page_to_evict)
                    self.frames.append(page)
                    
        return {
            "page_faults": self.page_faults,
            "hits": self.hits,
            "hit_status": hit_status
        }
