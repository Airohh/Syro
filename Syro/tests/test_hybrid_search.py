"""Non-régression retrieval : fusion RRF + dégradation BM25-only."""

import numpy as np
from unittest.mock import Mock, patch


def _vec(chunk_id, text, score):
    return {"chunk_id": chunk_id, "text": text, "score": score, "metadata": {}}


class TestRRFFusion:
    @patch("app.services.hybrid_search.bm25_search")
    @patch("app.services.hybrid_search.VectorStore")
    @patch("app.services.hybrid_search.get_embedding_vector")
    @patch("app.services.hybrid_search.settings")
    def test_rrf_ranks_by_rank_not_raw_score(
        self, mock_settings, mock_embed, mock_vs_class, mock_bm25
    ):
        """Un chunk présent dans les deux listes doit remonter via la somme RRF,
        sans dépendre des scores bruts (immunité aux échelles)."""
        mock_settings.retrieval_top_k = 10
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_embed.return_value = np.array([0.1] * 8)

        mock_vs = Mock()
        mock_vs_class.return_value = mock_vs
        # B est en rang 1 côté vecteur, rang 0 côté BM25 -> somme RRF la plus haute.
        mock_vs.search.return_value = [_vec("A", "a", 0.99), _vec("B", "b", 0.10)]
        mock_bm25.search.return_value = [_vec("B", "b", 0.99), _vec("C", "c", 0.01)]

        results = hybrid_search(organization_id=1, query="q", top_k=10)

        ids = [r["chunk_id"] for r in results]
        assert ids[0] == "B"  # double hit gagne
        assert set(ids) == {"A", "B", "C"}

    @patch("app.services.hybrid_search.bm25_search")
    @patch("app.services.hybrid_search.VectorStore")
    @patch("app.services.hybrid_search.get_embedding_vector")
    @patch("app.services.hybrid_search.settings")
    def test_embedding_failure_degrades_to_bm25_only(
        self, mock_settings, mock_embed, mock_vs_class, mock_bm25
    ):
        """Embedding KO ne doit pas lever : on tombe sur BM25 seul, jamais de
        recherche vectorielle (pas de 500)."""
        mock_settings.retrieval_top_k = 10
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_embed.side_effect = RuntimeError("embeddings provider down")
        mock_bm25.search.return_value = [_vec("C", "c", 0.5)]

        results = hybrid_search(organization_id=1, query="q", top_k=10)

        assert [r["chunk_id"] for r in results] == ["C"]
        mock_vs_class.assert_not_called()  # aucune recherche vectorielle tentée

    @patch("app.services.hybrid_search.bm25_search")
    @patch("app.services.hybrid_search.VectorStore")
    @patch("app.services.hybrid_search.get_embedding_vector")
    @patch("app.services.hybrid_search.settings")
    def test_qdrant_down_degrades_to_bm25_only(
        self, mock_settings, mock_embed, mock_vs_class, mock_bm25
    ):
        """Qdrant KO (VectorStoreError) ne doit pas lever : le chemin vectoriel
        est neutralisé, on sert BM25 seul (clôture du bug 500 chat, T0.2)."""
        mock_settings.retrieval_top_k = 10
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_embed.return_value = np.array([0.1] * 8)
        mock_vs = Mock()
        mock_vs_class.return_value = mock_vs
        mock_vs.search.side_effect = VectorStoreError("qdrant unreachable")
        mock_bm25.search.return_value = [_vec("C", "c", 0.5)]

        results = hybrid_search(organization_id=1, query="q", top_k=10)

        assert [r["chunk_id"] for r in results] == ["C"]

    @patch("app.services.hybrid_search.expand_queries")
    @patch("app.services.hybrid_search.bm25_search")
    @patch("app.services.hybrid_search.VectorStore")
    @patch("app.services.hybrid_search.get_embedding_vectors")
    @patch("app.services.hybrid_search.settings")
    def test_query_rewriting_merges_variants_via_rrf(
        self,
        mock_settings,
        mock_embed_many,
        mock_vs_class,
        mock_bm25,
        mock_expand,
    ):
        """Plusieurs variantes → listes BM25/vector fusionnées par RRF (T2.1)."""
        mock_settings.retrieval_top_k = 10
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_expand.return_value = ["q original", "q reformulée"]
        mock_embed_many.return_value = [np.array([0.1] * 8), np.array([0.2] * 8)]

        mock_vs = Mock()
        mock_vs_class.return_value = mock_vs
        mock_vs.search.side_effect = [
            [_vec("A", "a", 0.9)],
            [_vec("B", "b", 0.8)],
        ]

        def _bm25_side_effect(organization_id, query, top_k, filters=None, **kwargs):
            if query == "q original":
                return [_vec("C", "c", 0.7)]
            return [_vec("B", "b", 0.99)]

        mock_bm25.search.side_effect = _bm25_side_effect

        results = hybrid_search(organization_id=1, query="q original", top_k=10)

        assert mock_expand.called
        assert mock_embed_many.called
        ids = [r["chunk_id"] for r in results]
        assert ids[0] == "B"
        assert set(ids) == {"A", "B", "C"}


# Import après les helpers pour garder le module léger au collect.
from app.services.hybrid_search import hybrid_search  # noqa: E402
from app.services.vector_store import VectorStoreError  # noqa: E402
