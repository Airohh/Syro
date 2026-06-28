"""Tests query decomposition multi-hop (T3.3)."""

from unittest.mock import patch

from app.services.decompose import (
    _split_multi_question,
    _split_semicolon_clauses,
    decompose,
    fuse_rrf_lists,
    retrieve_decomposed,
)


def _chunk(cid: str, text: str, score: float) -> dict:
    return {"chunk_id": cid, "text": text, "score": score, "metadata": {}}


class TestHeuristicSplit:
    def test_multi_question(self):
        q = "Qu'est-ce que Kubernetes? Comment scaler les pods?"
        parts = _split_multi_question(q)
        assert len(parts) == 2
        assert parts[0].endswith("?")

    def test_semicolon_clauses(self):
        q = "Définir le RAG documentaire; expliquer le fine-tuning des embeddings"
        parts = _split_semicolon_clauses(q)
        assert len(parts) == 2


class TestDecompose:
    @patch("app.services.decompose.settings")
    def test_disabled_returns_original(self, mock_settings):
        mock_settings.enable_query_decomposition = False
        assert decompose("Q1? Q2?") == ["Q1? Q2?"]

    @patch("app.services.decompose.settings")
    def test_splits_double_question(self, mock_settings):
        mock_settings.enable_query_decomposition = True
        mock_settings.query_decomposition_max_subqueries = 3

        out = decompose("Qu'est-ce que MLflow? Comment tracer un run?")
        assert len(out) == 2


class TestFuseRrfLists:
    @patch("app.services.decompose.settings")
    def test_merges_unique_chunks(self, mock_settings):
        mock_settings.rrf_k = 60
        list_a = [_chunk("1", "a", 0.9), _chunk("2", "b", 0.5)]
        list_b = [_chunk("2", "b", 0.8), _chunk("3", "c", 0.4)]

        fused = fuse_rrf_lists([list_a, list_b], top_k=3)

        assert len(fused) == 3
        assert fused[0]["chunk_id"] == "2"


class TestRetrieveDecomposed:
    @patch("app.services.decompose._llm_decompose", return_value=[])
    @patch("app.services.decompose.hybrid_search")
    @patch("app.services.decompose.settings")
    def test_single_subquery_delegates_hybrid(
        self, mock_settings, mock_hybrid, _mock_llm
    ):
        mock_settings.enable_query_decomposition = True
        mock_settings.enable_crag = False
        mock_settings.rerank_top_k = 5
        mock_settings.query_decomposition_max_subqueries = 3

        mock_hybrid.return_value = [_chunk("1", "x", 0.1)]

        out = retrieve_decomposed(organization_id=1, query="simple question")

        assert out == mock_hybrid.return_value
        mock_hybrid.assert_called_once()

    @patch("app.services.decompose._llm_decompose", return_value=[])
    @patch("app.services.decompose.reranker")
    @patch("app.services.decompose.hybrid_search")
    @patch("app.services.decompose.settings")
    def test_parallel_subqueries_fused(
        self, mock_settings, mock_hybrid, mock_reranker, _mock_llm
    ):
        mock_settings.enable_query_decomposition = True
        mock_settings.enable_crag = False
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 10
        mock_settings.query_decomposition_max_subqueries = 3
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_hybrid.side_effect = [
            [_chunk("1", "a", 0.9)],
            [_chunk("2", "b", 0.8)],
        ]

        q = "Qu'est-ce que MLflow? Comment tracer un run?"
        out = retrieve_decomposed(organization_id=1, query=q)

        assert mock_hybrid.call_count == 2
        assert {c["chunk_id"] for c in out} == {"1", "2"}
        mock_reranker.rerank.assert_not_called()

    @patch("app.services.decompose._llm_decompose", return_value=[])
    @patch("app.services.decompose.hybrid_search")
    @patch("app.services.crag.retrieve_with_crag")
    @patch("app.services.decompose.settings")
    def test_parallel_subqueries_use_crag_when_enabled(
        self, mock_settings, mock_crag, mock_hybrid, _mock_llm
    ):
        mock_settings.enable_query_decomposition = True
        mock_settings.enable_crag = True
        mock_settings.rerank_top_k = 5
        mock_settings.retrieval_top_k = 10
        mock_settings.query_decomposition_max_subqueries = 3
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False

        mock_crag.side_effect = [
            [_chunk("1", "a", 0.9)],
            [_chunk("2", "b", 0.8)],
        ]

        q = "Qu'est-ce que MLflow? Comment tracer un run?"
        out = retrieve_decomposed(organization_id=1, query=q)

        assert mock_crag.call_count == 2
        mock_hybrid.assert_not_called()
        assert {c["chunk_id"] for c in out} == {"1", "2"}
