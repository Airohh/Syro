"""Tests HyDE (T2.2) — sans LLM réel."""

import numpy as np
from unittest.mock import Mock, patch

from app.services.hyde import generate_hypothetical_passage, get_hyde_embedding_vector


class TestHyde:
    @patch("app.services.hyde.settings")
    def test_disabled_returns_none(self, mock_settings):
        mock_settings.enable_hyde = False
        assert get_hyde_embedding_vector("question") is None

    @patch("app.services.llm.get_embedding_vector")
    @patch("app.services.hyde.generate_hypothetical_passage")
    @patch("app.services.hyde.settings")
    def test_enabled_embeds_passage(self, mock_settings, mock_gen, mock_embed):
        mock_settings.enable_hyde = True
        mock_gen.return_value = "passage hypothétique sur le RAG"
        mock_embed.return_value = np.array([0.1, 0.2], dtype=np.float32)

        vec = get_hyde_embedding_vector("Qu'est-ce que le RAG ?")

        assert vec is not None
        mock_embed.assert_called_once_with("passage hypothétique sur le RAG")

    @patch("app.services.hyde.generate_hypothetical_passage")
    @patch("app.services.hyde.settings")
    def test_empty_passage_returns_none(self, mock_settings, mock_gen):
        mock_settings.enable_hyde = True
        mock_gen.return_value = ""
        assert get_hyde_embedding_vector("q") is None

    @patch("app.services.llm.provider")
    def test_generate_returns_empty_without_chat_model(self, mock_provider):
        mock_provider._chat_model = None
        assert generate_hypothetical_passage("q") == ""


class TestHydeHybridSearch:
    @patch("app.services.hybrid_search.get_hyde_embedding_vector")
    @patch("app.services.hybrid_search.expand_queries")
    @patch("app.services.hybrid_search.bm25_search")
    @patch("app.services.hybrid_search.VectorStore")
    @patch("app.services.hybrid_search.get_embedding_vector")
    @patch("app.services.hybrid_search.settings")
    def test_hyde_adds_extra_vector_list(
        self,
        mock_settings,
        mock_embed,
        mock_vs_class,
        mock_bm25,
        mock_expand,
        mock_hyde,
    ):
        from app.services.hybrid_search import hybrid_search

        mock_settings.retrieval_top_k = 10
        mock_settings.rrf_k = 60
        mock_settings.enable_reranking = False
        mock_settings.enable_hyde = True

        mock_expand.return_value = ["q"]
        mock_embed.return_value = np.array([0.1] * 8)
        mock_hyde.return_value = np.array([0.9] * 8)

        mock_vs = Mock()
        mock_vs_class.return_value = mock_vs
        mock_vs.search.side_effect = [
            [{"chunk_id": "A", "text": "a", "score": 0.9, "metadata": {}}],
            [{"chunk_id": "B", "text": "b", "score": 0.8, "metadata": {}}],
        ]
        mock_bm25.search.return_value = [
            {"chunk_id": "C", "text": "c", "score": 0.7, "metadata": {}},
        ]

        results = hybrid_search(organization_id=1, query="q", top_k=10)

        assert mock_hyde.called
        assert mock_vs.search.call_count == 2
        ids = {r["chunk_id"] for r in results}
        assert ids == {"A", "B", "C"}
