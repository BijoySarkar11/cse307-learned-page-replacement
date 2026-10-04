"""
Explanation Confidence Engine (Bonus Track)
===========================================
A rule-based template generator that produces a short natural-language
explanation of each algorithm's eviction decision, along with a self-rated
confidence score (0.0 – 1.0).

Design rationale
----------------
Instead of calling an external LLM API (which would require a paid key and
introduce network latency for 10 000 steps), we use a deterministic
template generator whose confidence heuristic is *derived from the same
features the algorithms actually use*.  This keeps the bonus track
self-contained, reproducible, and free of API dependencies, while still
being educationally meaningful: the confidence score is calibrated against
ground-truth Optimal decisions so we can measure reliability.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import math


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EvictionExplanation:
    """One explanation record for a single page-fault event."""
    step: int                   # global access index in the trace
    requested_page: int         # the page that caused the fault
    evicted_page: int           # the page that was evicted
    algorithm: str              # FIFO / LRU / Optimal / Learned
    explanation: str            # human-readable explanation
    confidence: float           # self-rated confidence 0.0 – 1.0
    was_correct: Optional[bool] = None  # filled in later (matches Optimal?)
    optimal_eviction: Optional[int] = None  # ground-truth page to evict


# ---------------------------------------------------------------------------
# Explanation generators (one per algorithm)
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class FIFOExplainer:
    """Explains FIFO evictions."""

    def __init__(self, window_size: int = 50):
        self.recent_pages: list[int] = []
        self.window_size = window_size

    def explain(self, step: int, requested_page: int, evicted_page: int,
                frames: list, entry_order: list, **_kw) -> EvictionExplanation:
        rank = entry_order.index(evicted_page) if evicted_page in entry_order else 0
        total = len(entry_order)

        # Track recent page diversity.
        self.recent_pages.append(requested_page)
        if len(self.recent_pages) > self.window_size:
            self.recent_pages.pop(0)
        diversity = len(set(self.recent_pages)) / max(total, 1)

        explanation = (
            f"FIFO evicts page {evicted_page} because it was the first page "
            f"loaded into memory (position {rank+1}/{total} in arrival order). "
            f"Page {requested_page} needs a frame, so the oldest resident is removed."
        )

        # Confidence heuristic:
        # FIFO works best under low-diversity, sequential access patterns.
        # High diversity (many distinct pages recently) → less confident.
        # Low diversity (small working set cycling) → more confident.
        base = 0.55
        diversity_penalty = 0.45 * min(diversity, 1.0)  # 0 – 0.45
        confidence = _clamp(base + (0.45 - diversity_penalty))

        return EvictionExplanation(
            step=step, requested_page=requested_page,
            evicted_page=evicted_page, algorithm="FIFO",
            explanation=explanation, confidence=round(confidence, 4),
        )


class LRUExplainer:
    """Explains LRU evictions."""

    def __init__(self, window_size: int = 50):
        self.recent_pages: list[int] = []
        self.window_size = window_size

    def explain(self, step: int, requested_page: int, evicted_page: int,
                frames: list, last_access: dict, current_time: int,
                **_kw) -> EvictionExplanation:
        recency = current_time - last_access.get(evicted_page, 0)

        # Find how much "gap" there is between the LRU victim and the
        # second-least-recently-used page — a larger gap → higher confidence.
        recencies = sorted(
            [(current_time - last_access.get(p, 0), p) for p in frames],
            reverse=True,
        )
        gap = 0
        if len(recencies) >= 2:
            gap = recencies[0][0] - recencies[1][0]

        # Track recent page diversity for additional confidence modulation.
        self.recent_pages.append(requested_page)
        if len(self.recent_pages) > self.window_size:
            self.recent_pages.pop(0)
        diversity = len(set(self.recent_pages)) / max(len(frames), 1)

        explanation = (
            f"LRU evicts page {evicted_page} because it has not been accessed "
            f"for {recency} time steps — the longest gap among all {len(frames)} "
            f"resident pages. Page {requested_page} replaces it."
        )

        # Confidence: base boosted by dominance, penalised by high diversity.
        # LRU is most confident when the victim is clearly the LRU candidate
        # (large gap) and the workload has low diversity (temporal locality).
        if recency > 0:
            dominance = gap / recency  # 0 … 1
        else:
            dominance = 0.0
        diversity_factor = max(0.0, 1.0 - 0.3 * min(diversity, 3.0))  # 0.1 – 1.0
        confidence = _clamp(0.35 + 0.35 * dominance * diversity_factor
                            + 0.20 * diversity_factor)

        return EvictionExplanation(
            step=step, requested_page=requested_page,
            evicted_page=evicted_page, algorithm="LRU",
            explanation=explanation, confidence=round(confidence, 4),
        )


class OptimalExplainer:
    """Explains Optimal (Belady's) evictions."""

    def explain(self, step: int, requested_page: int, evicted_page: int,
                frames: list, next_use: dict, **_kw) -> EvictionExplanation:
        future = next_use.get(evicted_page, None)
        future_str = str(future) if future is not None else "never again"

        explanation = (
            f"Optimal evicts page {evicted_page} because its next use is "
            f"{future_str} — the farthest (or nonexistent) future reference "
            f"among all {len(frames)} resident pages. This is provably the "
            f"best choice."
        )

        # Confidence: always very high for Optimal since it has perfect knowledge.
        confidence = 1.0 if future is None else _clamp(0.90 + 0.10 * (1 - 1 / (1 + (future - step) / 100)))

        return EvictionExplanation(
            step=step, requested_page=requested_page,
            evicted_page=evicted_page, algorithm="Optimal",
            explanation=explanation, confidence=round(confidence, 4),
        )


class LearnedExplainer:
    """Explains Learned-policy evictions."""

    def explain(self, step: int, requested_page: int, evicted_page: int,
                frames: list, model_score: float, features: list,
                feature_names: list, all_scores: dict,
                **_kw) -> EvictionExplanation:
        # Build a compact feature summary for the evicted page.
        feat_parts = []
        for fn, fv in zip(feature_names, features):
            feat_parts.append(f"{fn}={fv:.1f}" if isinstance(fv, float) else f"{fn}={fv}")
        feat_str = ", ".join(feat_parts)

        # Find runner-up score to gauge margin.
        sorted_scores = sorted(all_scores.values(), reverse=True)
        margin = 0.0
        if len(sorted_scores) >= 2:
            margin = sorted_scores[0] - sorted_scores[1]

        explanation = (
            f"Learned policy evicts page {evicted_page} "
            f"(model eviction score={model_score:.3f}, features: [{feat_str}]). "
            f"Among {len(frames)} candidates it had the highest predicted "
            f"probability of being the optimal victim "
            f"(margin over runner-up: {margin:.3f})."
        )

        # Confidence: model probability itself is a natural confidence proxy,
        # boosted when the margin is large.
        confidence = _clamp(model_score * 0.6 + margin * 0.4 + 0.1)

        return EvictionExplanation(
            step=step, requested_page=requested_page,
            evicted_page=evicted_page, algorithm="Learned",
            explanation=explanation, confidence=round(confidence, 4),
        )


# ---------------------------------------------------------------------------
# Instrumented simulators  (thin wrappers that collect explanations)
# ---------------------------------------------------------------------------

class InstrumentedFIFO:
    """FIFO with explanation collection."""

    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.explainer = FIFOExplainer()

    def process_trace(self, trace):
        frames = []
        entry_order = []
        explanations: List[EvictionExplanation] = []
        hit_status = []
        page_faults = 0
        hits = 0

        for i, page in enumerate(trace):
            if page in frames:
                hits += 1
                hit_status.append(True)
            else:
                page_faults += 1
                hit_status.append(False)
                if len(frames) < self.num_frames:
                    frames.append(page)
                    entry_order.append(page)
                else:
                    evicted = entry_order.pop(0)
                    frames.remove(evicted)
                    frames.append(page)
                    entry_order.append(page)
                    explanations.append(
                        self.explainer.explain(
                            step=i, requested_page=page,
                            evicted_page=evicted, frames=frames,
                            entry_order=entry_order,
                        )
                    )

        return {"page_faults": page_faults, "hits": hits,
                "hit_status": hit_status, "explanations": explanations}


class InstrumentedLRU:
    """LRU with explanation collection."""

    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.explainer = LRUExplainer()

    def process_trace(self, trace):
        frames = []
        last_access: dict[int, int] = {}
        explanations: List[EvictionExplanation] = []
        hit_status = []
        page_faults = 0
        hits = 0

        for i, page in enumerate(trace):
            if page in frames:
                hits += 1
                hit_status.append(True)
                frames.remove(page)
                frames.append(page)
            else:
                page_faults += 1
                hit_status.append(False)
                if len(frames) < self.num_frames:
                    frames.append(page)
                else:
                    evicted = frames.pop(0)
                    frames.append(page)
                    explanations.append(
                        self.explainer.explain(
                            step=i, requested_page=page,
                            evicted_page=evicted, frames=list(frames),
                            last_access=dict(last_access),
                            current_time=i,
                        )
                    )
            last_access[page] = i

        return {"page_faults": page_faults, "hits": hits,
                "hit_status": hit_status, "explanations": explanations}


class InstrumentedOptimal:
    """Optimal (Belady's) with explanation collection."""

    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.explainer = OptimalExplainer()

    def process_trace(self, trace):
        frames = []
        explanations: List[EvictionExplanation] = []
        hit_status = []
        page_faults = 0
        hits = 0

        # Pre-compute next-use lists.
        next_use_dict: dict[int, list[int]] = {}
        for idx in range(len(trace) - 1, -1, -1):
            p = trace[idx]
            next_use_dict.setdefault(p, []).append(idx)

        for i, page in enumerate(trace):
            next_use_dict[page].pop()

            if page in frames:
                hits += 1
                hit_status.append(True)
            else:
                page_faults += 1
                hit_status.append(False)
                if len(frames) < self.num_frames:
                    frames.append(page)
                else:
                    farthest_use = -1
                    page_to_evict = None
                    next_use_snapshot: dict[int, int | None] = {}

                    for resident in frames:
                        uses = next_use_dict.get(resident, [])
                        if not uses:
                            page_to_evict = resident
                            next_use_snapshot[resident] = None
                            break
                        else:
                            nxt = uses[-1]
                            next_use_snapshot[resident] = nxt
                            if nxt > farthest_use:
                                farthest_use = nxt
                                page_to_evict = resident

                    # Fill remaining snapshots if we broke early.
                    for resident in frames:
                        if resident not in next_use_snapshot:
                            uses = next_use_dict.get(resident, [])
                            next_use_snapshot[resident] = uses[-1] if uses else None

                    frames.remove(page_to_evict)
                    frames.append(page)

                    explanations.append(
                        self.explainer.explain(
                            step=i, requested_page=page,
                            evicted_page=page_to_evict,
                            frames=list(frames),
                            next_use=next_use_snapshot,
                        )
                    )

        return {"page_faults": page_faults, "hits": hits,
                "hit_status": hit_status, "explanations": explanations}


class InstrumentedLearned:
    """Learned policy with explanation collection."""

    def __init__(self, num_frames, model, window_size=100):
        self.num_frames = num_frames
        self.model = model
        self.window_size = window_size
        self.explainer = LearnedExplainer()

    def process_trace(self, trace):
        from features import FeatureExtractor

        frames = []
        explanations: List[EvictionExplanation] = []
        hit_status = []
        page_faults = 0
        hits = 0
        feature_extractor = FeatureExtractor(window_size=self.window_size)

        for i, page in enumerate(trace):
            in_memory = page in frames

            if in_memory:
                hits += 1
                hit_status.append(True)
            else:
                page_faults += 1
                hit_status.append(False)
                if len(frames) < self.num_frames:
                    frames.append(page)
                else:
                    max_score = -1
                    candidates = []
                    all_scores: dict[int, float] = {}
                    all_features: dict[int, list] = {}

                    for resident in frames:
                        features = feature_extractor.get_features(resident)
                        all_features[resident] = features
                        if hasattr(self.model, 'predict_proba') and len(self.model.classes_) > 1:
                            proba = self.model.predict_proba([features])[0]
                            score = proba[1] if 1 in self.model.classes_ else 0
                        else:
                            score = float(self.model.predict([features])[0])

                        all_scores[resident] = score
                        if score > max_score:
                            max_score = score
                            candidates = [resident]
                        elif score == max_score:
                            candidates.append(resident)

                    if len(candidates) > 1:
                        best_candidate = candidates[0]
                        max_recency = -1
                        for c in candidates:
                            rec = feature_extractor.get_features(c)[0]
                            if rec > max_recency:
                                max_recency = rec
                                best_candidate = c
                        best_evict_page = best_candidate
                    else:
                        best_evict_page = candidates[0]

                    frames.remove(best_evict_page)
                    frames.append(page)

                    explanations.append(
                        self.explainer.explain(
                            step=i, requested_page=page,
                            evicted_page=best_evict_page,
                            frames=list(frames),
                            model_score=all_scores[best_evict_page],
                            features=all_features[best_evict_page],
                            feature_names=FeatureExtractor.feature_names(),
                            all_scores=all_scores,
                        )
                    )

            feature_extractor.record_access(page, in_memory)

        return {"page_faults": page_faults, "hits": hits,
                "hit_status": hit_status, "explanations": explanations}


# ---------------------------------------------------------------------------
# Utility: stamp ground-truth correctness onto explanations
# ---------------------------------------------------------------------------

def annotate_correctness(explanations: List[EvictionExplanation],
                         optimal_explanations: List[EvictionExplanation]):
    """
    Match each algorithm's eviction events to the Optimal baseline
    by (step, requested_page) and mark whether the eviction agreed.

    Because different algorithms fault on different accesses, we build a
    lookup from the Optimal explanations keyed on step index.
    """
    optimal_map: dict[int, int] = {}
    for oe in optimal_explanations:
        optimal_map[oe.step] = oe.evicted_page

    for ex in explanations:
        if ex.step in optimal_map:
            ex.optimal_eviction = optimal_map[ex.step]
            ex.was_correct = (ex.evicted_page == ex.optimal_eviction)
        else:
            # If Optimal didn't fault here (e.g. it was a hit there), we
            # can't directly compare — mark as None.
            ex.was_correct = None
