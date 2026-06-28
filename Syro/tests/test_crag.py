"""Tests CRAG (T3.1) — évaluateur + retrieval correctif, sans stack live."""

from unittest.mock import patch

from app.services.crag import (
    assess_retrieval_quality,
    lexical_overlap,
    retrieve_with_crag,
    top_retrieval_strength,
)


def _chunk(cid: str, text: str, score: float) -> dict:
    return {"chunk_id": cid, "text": text, "score": score, "metadata": {}}


class TestLexicalOverlap:
    def test_full_overlap(self):
        assert lexical_overlap(
            "kubernetes deployment pods",
            ["kubernetes deployment guide for pods"],
        ) == 1.0

    def test_no_overlap(self):
        assert lexical_overlap("python asyncio", ["java spring boot"]) == 0.0

    def test_empty_query_returns_zero(self):
        assert lexical_overlap("??", ["some chunk text"]) == 0.0


class TestTopRetrievalStrength:
    def test_empty(self):
        assert top_retrieval_strength([]) == 0.0

    def test_capped_at_one(self):
        assert top_retrieval_strength([_chunk("1", "x", 0.2)]) == 1.0


class TestAssessRetrievalQuality:
    @patch("app.services.crag.settings")
    def test_empty_is_incorrect(self, mock_settings):
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25

        result = assess_retrieval_quality("kubernetes pods", [])

        assert result["verdict"] == "incorrect"
        assert result["score"] == 0.0

    @patch("app.services.crag.settings")
    def test_strong_match_is_correct(self, mock_settings):
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25

        chunks = [
            _chunk("1", "kubernetes deployment pods scaling guide", 0.04),
        ]
        result = assess_retrieval_quality("kubernetes deployment pods", chunks)

        assert result["verdict"] == "correct"
        assert result["score"] >= 0.25

    @patch("app.services.crag.settings")
    def test_weak_match_is_ambiguous(self, mock_settings):
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25

        chunks = [_chunk("1", "unrelated topic about databases", 0.02)]
        result = assess_retrieval_quality("kubernetes deployment pods", chunks)

        assert result["verdict"] in ("ambiguous", "incorrect")


class TestRetrieveWithCrag:
    @patch("app.services.crag.hybrid_search")
    @patch("app.services.crag.settings")
    def test_skips_retry_when_correct(self, mock_settings, mock_hybrid):
        mock_settings.rerank_top_k = 5
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25

        good = [_chunk("1", "kubernetes deployment pods guide", 0.04)]
        mock_hybrid.return_value = good

        out = retrieve_with_crag(organization_id=1, query="kubernetes deployment pods")

        assert out == good
        mock_hybrid.assert_called_once()

    @patch("app.services.crag.expand_queries")
    @patch("app.services.crag.hybrid_search")
    @patch("app.services.crag.settings")
    def test_retries_on_weak_retrieval(self, mock_settings, mock_hybrid, mock_expand):
        mock_settings.rerank_top_k = 5
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25
        mock_settings.crag_retry_top_k_multiplier = 2
        mock_settings.retrieval_top_k = 10

        weak = [_chunk("1", "unrelated databases sql", 0.01)]
        better = [_chunk("2", "kubernetes deployment pods scaling", 0.04)]
        mock_hybrid.side_effect = [weak, better]
        mock_expand.return_value = ["kubernetes deployment pods", "k8s pod deploy"]

        out = retrieve_with_crag(organization_id=1, query="kubernetes deployment pods")

        assert out == better
        assert mock_hybrid.call_count == 2
        mock_expand.assert_called_once_with(
            "kubernetes deployment pods", history=None, force=True
        )

    @patch("app.services.crag.expand_queries")
    @patch("app.services.crag.hybrid_search")
    @patch("app.services.crag.settings")
    def test_merges_when_retry_not_better(self, mock_settings, mock_hybrid, mock_expand):
        mock_settings.rerank_top_k = 5
        mock_settings.crag_incorrect_threshold = 0.12
        mock_settings.crag_retry_threshold = 0.25
        mock_settings.crag_retry_top_k_multiplier = 2
        mock_settings.retrieval_top_k = 10

        first = [_chunk("1", "weak match topic", 0.015)]
        retry = [_chunk("2", "also weak content", 0.01)]
        mock_hybrid.side_effect = [first, retry]
        mock_expand.return_value = ["q", "q variant"]

        out = retrieve_with_crag(organization_id=1, query="kubernetes deployment pods")

        assert len(out) == 2
        assert out[0]["chunk_id"] == "1"
        assert mock_hybrid.call_count == 2
