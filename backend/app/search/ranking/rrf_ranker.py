import uuid
from typing import Dict, List, Tuple
from backend.app.search.ranking.base import BaseRanker, CandidateMatch


class ReciprocalRankFusionRanker(BaseRanker):
    """
    Modular ranker implementing Reciprocal Rank Fusion (RRF).
    Combines ranked lists from diverse retrieval strategies (dense vector and sparse keyword)
    robustly without requiring score calibration across different metric distributions.

    Formula:
      score(d) = w_sem * 1/(k + rank_sem) + w_kw * 1/(k + rank_kw)
    """

    def __init__(self, k: int = 60):
        self.k = k

    def rank(
        self,
        semantic_candidates: Dict[uuid.UUID, CandidateMatch],
        keyword_candidates: Dict[uuid.UUID, CandidateMatch],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Tuple[uuid.UUID, float]]:
        all_doc_ids = set(semantic_candidates.keys()) | set(keyword_candidates.keys())
        if not all_doc_ids:
            return []

        # Ensure non-zero total weight
        total_weight = semantic_weight + keyword_weight
        w_sem = (semantic_weight / total_weight) if total_weight > 0 else 0.5
        w_kw = (keyword_weight / total_weight) if total_weight > 0 else 0.5

        # Maximum possible RRF raw score (rank 1 in both): 1 / (k + 1)
        max_possible = 1.0 / (self.k + 1)

        fused_scores: Dict[uuid.UUID, float] = {}

        for doc_id in all_doc_ids:
            score = 0.0
            if doc_id in semantic_candidates:
                sem_rank = semantic_candidates[doc_id].rank
                score += w_sem / (self.k + sem_rank)
            if doc_id in keyword_candidates:
                kw_rank = keyword_candidates[doc_id].rank
                score += w_kw / (self.k + kw_rank)

            # Normalize to approximately [0.0, 1.0]
            normalized_score = min(1.0, score / max_possible) if max_possible > 0 else score
            fused_scores[doc_id] = round(normalized_score, 4)

        # Sort descending by score
        sorted_items = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_items[offset : offset + limit]
