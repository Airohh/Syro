"""Reranking service using bge-reranker-v2-m3 for improved precision."""

from __future__ import annotations

import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


def _normalize_unit(scores: list[float]) -> list[float]:
    """Min-max vers [0,1] ; ex æquo (ou liste vide) → 1.0."""
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


class Reranker:
    def __init__(self) -> None:
        self._model = None
        self._enabled = settings.enable_reranking
        self._cuda_available = None

    def _check_cuda(self) -> bool:
        if self._cuda_available is not None:
            return self._cuda_available
        try:
            import torch

            self._cuda_available = torch.cuda.is_available()
            return self._cuda_available
        except ImportError:
            self._cuda_available = False
            return False

    def _load_model(self):
        if self._model is not None:
            return self._model

        if not self._enabled:
            return None

        try:
            from FlagEmbedding import FlagReranker

            try:
                self._model = FlagReranker(
                    "BAAI/bge-reranker-v2-m3",
                    use_fp16=True,
                    device="cuda" if self._check_cuda() else "cpu",
                )
                import logging as _logging

                _logging.getLogger(__name__).info(
                    "Reranker loaded on %s", "GPU" if self._check_cuda() else "CPU"
                )
                return self._model
            except Exception:
                return None
        except ImportError:
            return None
        except Exception:
            return None

    def rerank(
        self,
        query: str,
        passages: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rerank passages using cross-encoder model.

        Args:
            query: Search query
            passages: List of passages with 'text' and other metadata
            top_k: Number of top results to return

        Returns:
            Reranked list of passages with updated scores
        """
        if not passages:
            return []

        if not self._enabled:
            # Return as-is if reranking disabled
            return passages[:top_k] if top_k else passages

        model = self._load_model()
        if model is None:
            # Fallback: return original order (model not available)
            # This is expected if FlagEmbedding is not installed
            return passages[:top_k] if top_k else passages

        try:
            # FlagReranker.compute_score : float pour une paire, liste/ndarray sinon.
            pairs = [(query, p["text"]) for p in passages]
            raw = model.compute_score(pairs)
            # Scalaire (1 paire) : float Python, scalaire numpy (np.float32 n'est
            # PAS sous-classe de float), ou ndarray 0-d → tous itérables-faux.
            is_scalar = isinstance(raw, (int, float)) or (
                np is not None
                and (isinstance(raw, np.generic) or getattr(raw, "ndim", None) == 0)
            )
            if is_scalar:
                rerank_scores = [float(raw)]
            else:
                rerank_scores = [float(s) for s in raw]

            # Garde-fou : si le modèle ne renvoie pas un score par passage,
            # on ne peut pas réordonner de façon fiable → ordre d'origine.
            if len(rerank_scores) != len(passages):
                return passages[:top_k] if top_k else passages

            rerank_scores = _normalize_unit(rerank_scores)

            w = settings.rerank_weight
            reranked = [
                {
                    **passage,
                    "rerank_score": rerank_scores[i],
                    "final_score": passage.get("score", 0.0) * (1 - w)
                    + rerank_scores[i] * w,
                }
                for i, passage in enumerate(passages)
            ]
            reranked.sort(key=lambda x: x["final_score"], reverse=True)
            return reranked[:top_k] if top_k else reranked

        except Exception as exc:
            logger.warning("Reranking failed, returning original order: %s", exc)
            return passages[:top_k] if top_k else passages


# Global instance
reranker = Reranker()
