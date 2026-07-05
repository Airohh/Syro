"""T1.2 — métriques de retrieval déterministes."""

import math

from evaluation import metrics


class TestRankingMetrics:
    def test_recall_at_k(self):
        assert metrics.recall_at_k(["a", "b", "c"], {"a", "c"}, 2) == 0.5
        assert metrics.recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0

    def test_precision_at_k(self):
        assert metrics.precision_at_k(["a", "b"], {"a", "c"}, 2) == 0.5
        assert metrics.precision_at_k([], {"a"}, 5) == 0.0

    def test_reciprocal_rank(self):
        assert metrics.reciprocal_rank(["x", "a", "y"], {"a"}) == 0.5
        assert metrics.reciprocal_rank(["x", "y"], {"a"}) == 0.0

    def test_ndcg_rewards_top_position(self):
        top = metrics.ndcg_at_k(["a", "b"], {"a"}, 2)
        lower = metrics.ndcg_at_k(["b", "a"], {"a"}, 2)
        assert top == 1.0
        assert lower < top
        assert math.isclose(lower, 1.0 / math.log2(3), rel_tol=1e-9)

    def test_hit_at_k(self):
        assert metrics.hit_at_k(["a", "b"], {"b"}, 2) == 1.0
        assert metrics.hit_at_k(["a", "b"], {"z"}, 2) == 0.0

    def test_empty_relevant_is_nan(self):
        assert math.isnan(metrics.recall_at_k(["a"], set(), 5))
        assert math.isnan(metrics.ndcg_at_k(["a"], set(), 5))


class TestAggregate:
    def test_aggregate_excludes_oob_from_ranking_and_scores_refusal(self):
        items = [
            {"retrieved_ids": ["d1", "x"], "relevant_ids": ["d1"], "intent": "factual_lookup"},
            {"retrieved_ids": ["y", "d2"], "relevant_ids": ["d2"], "intent": "multi_hop"},
            {"retrieved_ids": [], "relevant_ids": [], "intent": "out_of_corpus"},
            {"retrieved_ids": ["z"], "relevant_ids": [], "intent": "out_of_corpus"},
        ]
        rep = metrics.aggregate_retrieval(items, ks=(5,))

        assert rep["n_total"] == 4
        assert rep["n_ranked"] == 2
        assert rep["recall@5"] == 1.0  # les 2 pertinents sont dans le top-5
        # mrr : rang 1 (1.0) et rang 2 (0.5) -> 0.75
        assert math.isclose(rep["mrr"], 0.75, rel_tol=1e-9)
        # 2 oob : un refus correct (retrieved vide), un raté -> 0.5
        assert rep["oob_refusal_rate"] == 0.5
        assert rep["n_oob"] == 2
        assert rep["by_intent"]["out_of_corpus"] == 2

    def test_aggregate_emits_gate_aliases(self):
        items = [
            {"retrieved_ids": ["d1"], "relevant_ids": ["d1"], "intent": "factual_lookup"},
        ]
        rep = metrics.aggregate_retrieval(items, ks=(5, 10))
        assert rep["recall@10"] == rep["recall_at_10"]
        assert rep["ndcg@10"] == rep["ndcg_at_10"]
        assert rep["hit@5"] == rep["hit_at_5"]
