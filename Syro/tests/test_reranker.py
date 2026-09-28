"""Reranker : score absolu (sigmoïde), tri, seuil d'abstention, repli RRF."""

from unittest.mock import patch

from app.services.hybrid_search import rerank_or_truncate
from app.services.reranker import Reranker
from app.services.retrieval_scoring import chunk_relevance, rrf_strong_score


class _FakeModel:
    def __init__(self, logits):
        self.logits = logits

    def compute_score(self, pairs):
        return self.logits[: len(pairs)]


def _passages(n):
    return [{"chunk_id": i, "text": f"t{i}", "score": 0.01} for i in range(n)]


def _reranker(logits):
    r = Reranker()
    r._model = _FakeModel(logits)
    return r


class TestRerank:
    @patch("app.services.reranker.settings")
    def test_sorts_by_cross_encoder_probability(self, s):
        s.rerank_min_score = 0.0
        out = _reranker([-2.0, 3.0, 0.0]).rerank("q", _passages(3), top_k=3)
        assert [p["chunk_id"] for p in out] == [1, 2, 0]
        assert 0.95 < out[0]["rerank_score"] < 0.96  # sigmoid(3)
        assert out[0]["score"] == out[0]["rerank_score"]

    @patch("app.services.reranker.settings")
    def test_drops_passages_below_threshold(self, s):
        s.rerank_min_score = 0.05
        out = _reranker([4.0, -6.0]).rerank("q", _passages(2), top_k=5)
        assert [p["chunk_id"] for p in out] == [0]

    @patch("app.services.reranker.settings")
    def test_nothing_relevant_returns_empty_list(self, s):
        """Question hors corpus : aucun contexte → le chat répond « je ne sais pas »."""
        s.rerank_min_score = 0.05
        assert _reranker([-8.0, -9.0]).rerank("q", _passages(2), top_k=5) == []

    def test_single_pair_scalar_output(self):
        r = Reranker()

        class _Scalar:
            def compute_score(self, pairs):
                return 1.5

        r._model = _Scalar()
        assert len(r.score("q", ["t"])) == 1

    def test_load_failure_is_remembered(self):
        r = Reranker()
        with patch.dict("sys.modules", {"FlagEmbedding": None}):
            assert r.rerank("q", _passages(2), top_k=2) is None
            assert r._load_failed
            assert r.rerank("q", _passages(2), top_k=2) is None


class TestRerankOrTruncate:
    @patch("app.services.hybrid_search.reranker")
    @patch("app.services.hybrid_search.settings")
    def test_falls_back_to_rrf_order_when_unavailable(self, s, reranker):
        s.enable_reranking = True
        reranker.rerank.return_value = None
        out = rerank_or_truncate("q", _passages(4), top_k=2)
        assert [p["chunk_id"] for p in out] == [0, 1]


class TestRelevance:
    def test_prefers_rerank_score(self):
        assert chunk_relevance({"rerank_score": 0.42, "score": 0.42}) == 0.42

    def test_rrf_normalised_on_top_of_both_lists(self):
        assert chunk_relevance({"rrf_score": rrf_strong_score()}) == 1.0
        assert 0.4 < chunk_relevance({"rrf_score": rrf_strong_score() / 2}) < 0.6
