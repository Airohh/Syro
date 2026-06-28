"""Tests grid-search RRF k (T2.3) — sans stack live."""

import sys
from pathlib import Path

import pytest

from evaluation.tune import collect_retrieval_items, score_rrf_k, select_best_rrf_k


def _fake_retrieve(question: str, domain: str | None, id_to_name: dict[str, str]) -> list[str]:
    del domain, id_to_name
    if "A" in question:
        return ["doc-a.md", "doc-b.md"]
    return ["doc-b.md", "doc-c.md"]


class TestSelectBestRrfK:
    def test_picks_highest_ndcg(self):
        reports = [
            {"rrf_k": 30, "ndcg@10": 0.55},
            {"rrf_k": 40, "ndcg@10": 0.72},
            {"rrf_k": 60, "ndcg@10": 0.68},
        ]
        best = select_best_rrf_k(reports, metric="ndcg@10")
        assert best["rrf_k"] == 40

    def test_raises_if_all_nan(self):
        with pytest.raises(ValueError):
            select_best_rrf_k([{"rrf_k": 30, "ndcg@10": float("nan")}])


class TestScoreRrfK:
    def test_patches_settings_rrf_k(self):
        from app.config import settings

        dataset = [
            {
                "question": "question A",
                "relevant_doc_ids": ["doc-a.md"],
                "intent": "lookup",
            },
        ]
        original = settings.rrf_k
        try:
            report = score_rrf_k(40, dataset, _fake_retrieve, {})
            assert report["rrf_k"] == 40
            assert settings.rrf_k == original
            assert report["recall@10"] == 1.0
        finally:
            settings.rrf_k = original

    def test_collect_retrieval_items(self):
        dataset = [
            {"question": "foo", "relevant_doc_ids": ["doc-b.md"], "intent": "lookup"},
        ]
        items = collect_retrieval_items(dataset, _fake_retrieve, {})
        assert items[0]["retrieved_ids"] == ["doc-b.md", "doc-c.md"]
