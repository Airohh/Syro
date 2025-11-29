"""Reranking service using bge-reranker-v2-m3 for improved precision."""

from __future__ import annotations

from typing import Any

from ..config import settings

try:
    import numpy as np
except ImportError:
    np = None

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
                    'BAAI/bge-reranker-v2-m3',
                    use_fp16=True,
                    device='cuda' if self._check_cuda() else 'cpu',
                )
                device_info = "GPU" if self._check_cuda() else "CPU"
                print(f"Reranker loaded on {device_info}")
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
            # Prepare pairs for reranking: (query, passage_text)
            pairs = [(query, p["text"]) for p in passages]
            
            # Get rerank scores using compute_score method
            # FlagReranker.compute_score can return different formats
            # For single pair: scalar, for multiple: list/array
            if len(pairs) == 1:
                score = model.compute_score(pairs)
                rerank_scores = [float(score)]
            else:
                rerank_scores = model.compute_score(pairs)
            
            # Handle different return types from compute_score
            import numpy as np
            if isinstance(rerank_scores, np.ndarray):
                rerank_scores = rerank_scores.tolist()
            elif isinstance(rerank_scores, (int, float)):
                # Single score returned for multiple pairs (shouldn't happen but handle it)
                rerank_scores = [float(rerank_scores)] * len(passages)
            elif not isinstance(rerank_scores, list):
                rerank_scores = list(rerank_scores)
            
            # Ensure we have the right number of scores
            if len(rerank_scores) != len(passages):
                if len(rerank_scores) == 1 and len(passages) > 1:
                    # Single score for all - use it
                    rerank_scores = rerank_scores * len(passages)
                elif len(rerank_scores) < len(passages):
                    # Pad with last score or 0
                    last_score = rerank_scores[-1] if rerank_scores else 0.0
                    rerank_scores.extend([last_score] * (len(passages) - len(rerank_scores)))
                elif len(rerank_scores) > len(passages):
                    # Truncate
                    rerank_scores = rerank_scores[:len(passages)]
            
            # Normalize rerank scores to [0, 1]
            if rerank_scores:
                min_score = min(rerank_scores)
                max_score = max(rerank_scores)
                if max_score > min_score:
                    rerank_scores = [(s - min_score) / (max_score - min_score) for s in rerank_scores]
                else:
                    rerank_scores = [1.0] * len(rerank_scores)
            
            # Update passages with rerank scores
            reranked = []
            for i, passage in enumerate(passages):
                rerank_score = float(rerank_scores[i]) if i < len(rerank_scores) else 0.0
                original_score = passage.get("score", 0.0)
                
                # Combine original hybrid score with rerank score
                rerank_weight = settings.rerank_weight
                final_score = (
                    original_score * (1 - rerank_weight) +
                    rerank_score * rerank_weight
                )
                
                reranked.append({
                    **passage,
                    "rerank_score": rerank_score,
                    "final_score": final_score,
                })
            
            # Sort by final score
            reranked.sort(key=lambda x: x["final_score"], reverse=True)
            
            # Return top_k
            if top_k:
                return reranked[:top_k]
            return reranked
            
        except Exception:
            return passages[:top_k] if top_k else passages

# Global instance
reranker = Reranker()

