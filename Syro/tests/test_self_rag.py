"""Tests Self-RAG (T3.2) — filtrage IsRel par chunk."""

from unittest.mock import patch

from app.services.self_rag import chunk_relevance_score, filter_relevant_chunks


def _chunk(cid: str, text: str, score: float) -> dict:
    return {"chunk_id": cid, "text": text, "score": score, "metadata": {}}


class TestChunkRelevanceScore:
    def test_high_overlap_scores_high(self):
        chunk = _chunk("1", "kubernetes deployment pods scaling", 0.04)
        assert chunk_relevance_score("kubernetes deployment pods", chunk) > 0.5

    def test_unrelated_scores_low(self):
        chunk = _chunk("1", "java spring boot microservices", 0.01)
        assert chunk_relevance_score("kubernetes deployment pods", chunk) < 0.2


class TestFilterRelevantChunks:
    @patch("app.services.self_rag.settings")
    def test_disabled_passthrough(self, mock_settings):
        mock_settings.enable_self_rag = False
        chunks = [_chunk("1", "x", 0.1), _chunk("2", "y", 0.05)]

        assert filter_relevant_chunks("query", chunks) is chunks

    @patch("app.services.self_rag.settings")
    def test_drops_irrelevant_keeps_relevant(self, mock_settings):
        mock_settings.enable_self_rag = True
        mock_settings.self_rag_min_relevance = 0.2
        mock_settings.self_rag_min_chunks = 1
        mock_settings.self_rag_max_chunks = 8

        chunks = [
            _chunk("1", "kubernetes deployment pods guide", 0.04),
            _chunk("2", "unrelated sql databases", 0.01),
            _chunk("3", "kubernetes pods autoscaling", 0.03),
        ]
        out = filter_relevant_chunks("kubernetes deployment pods", chunks)

        ids = {c["chunk_id"] for c in out}
        assert "2" not in ids
        assert "1" in ids

    @patch("app.services.self_rag.settings")
    def test_respects_min_chunks(self, mock_settings):
        mock_settings.enable_self_rag = True
        mock_settings.self_rag_min_relevance = 0.9
        mock_settings.self_rag_min_chunks = 3
        mock_settings.self_rag_max_chunks = 8

        chunks = [
            _chunk("1", "weak a", 0.01),
            _chunk("2", "weak b", 0.01),
            _chunk("3", "weak c", 0.01),
            _chunk("4", "weak d", 0.01),
        ]
        out = filter_relevant_chunks("kubernetes pods", chunks)

        assert len(out) == 3

    @patch("app.services.self_rag.settings")
    def test_respects_max_chunks(self, mock_settings):
        mock_settings.enable_self_rag = True
        mock_settings.self_rag_min_relevance = 0.05
        mock_settings.self_rag_min_chunks = 1
        mock_settings.self_rag_max_chunks = 2

        chunks = [
            _chunk(str(i), f"kubernetes pods topic {i}", 0.04 - i * 0.001)
            for i in range(6)
        ]
        out = filter_relevant_chunks("kubernetes pods", chunks)

        assert len(out) == 2

    @patch("app.services.self_rag.settings")
    def test_adds_relevance_metadata(self, mock_settings):
        mock_settings.enable_self_rag = True
        mock_settings.self_rag_min_relevance = 0.1
        mock_settings.self_rag_min_chunks = 1
        mock_settings.self_rag_max_chunks = 8

        chunks = [_chunk("1", "kubernetes deployment pods", 0.04)]
        out = filter_relevant_chunks("kubernetes deployment pods", chunks)

        assert "self_rag_relevance" in out[0]["metadata"]
