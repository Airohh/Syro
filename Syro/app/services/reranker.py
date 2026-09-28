"""Reranking cross-encoder (bge-reranker-v2-m3 par défaut, multilingue)."""

from __future__ import annotations

import logging
import math
import threading
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


class Reranker:
    """Charge le modèle à la demande ; un échec de chargement est mémorisé
    (sinon chaque requête retenterait un chargement de plusieurs Go)."""

    def __init__(self) -> None:
        self._model = None
        self._load_failed = False
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._load_model() is not None

    def _load_model(self):
        if self._model is not None or self._load_failed:
            return self._model
        with self._lock:
            if self._model is not None or self._load_failed:
                return self._model
            try:
                from FlagEmbedding import FlagReranker

                device = "cpu"
                try:
                    import torch

                    if torch.cuda.is_available():
                        device = "cuda"
                except ImportError:
                    pass
                self._model = FlagReranker(
                    settings.reranker_model,
                    use_fp16=device == "cuda",
                    device=device,
                )
                logger.info("Reranker %s loaded on %s", settings.reranker_model, device)
            except Exception as exc:
                self._load_failed = True
                logger.warning(
                    "Reranker unavailable (%s) — falling back to RRF order", exc
                )
        return self._model

    def warmup(self) -> None:
        """Pré-charge le modèle (appelé au démarrage dans un thread)."""
        if settings.enable_reranking:
            self._load_model()

    def score(self, query: str, texts: list[str]) -> list[float] | None:
        """Probabilités de pertinence [0, 1] (sigmoïde des logits), ou None."""
        model = self._load_model()
        if model is None or not texts:
            return None
        try:
            raw = model.compute_score([(query, t) for t in texts])
        except Exception as exc:
            logger.warning("Reranking failed, keeping RRF order: %s", exc)
            return None
        # Un seul couple → scalaire (float ou numpy 0-d) ; sinon liste/ndarray.
        values = (
            [float(raw)]
            if getattr(raw, "ndim", None) == 0 or isinstance(raw, (int, float))
            else [float(s) for s in raw]
        )
        if len(values) != len(texts):
            return None
        return [_sigmoid(v) for v in values]

    def rerank(
        self,
        query: str,
        passages: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]] | None:
        """Trie par score cross-encoder et écarte les passages sous le seuil.

        Retourne None si le reranker est indisponible (l'appelant garde
        l'ordre RRF). Une liste vide signifie « rien de pertinent ».
        """
        scores = self.score(query, [p["text"] for p in passages])
        if scores is None:
            return None
        reranked = [
            {**p, "rerank_score": s, "score": s} for p, s in zip(passages, scores)
        ]
        reranked.sort(key=lambda p: p["rerank_score"], reverse=True)
        kept = [p for p in reranked if p["rerank_score"] >= settings.rerank_min_score]
        return kept[:top_k]


reranker = Reranker()
