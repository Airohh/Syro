"""Retrieval lexical (BM25) de bout en bout sur le corpus d'évaluation.

Pas de Qdrant ni de LLM : corpus réel → chunker réel → SQLite → BM25 réel →
métriques du golden set. Garde-fou contre les régressions silencieuses
(ex. filtre de domaine qui vidait tous les résultats, mapping doc → fichier).
"""

import json
from pathlib import Path

import pytest

from app.services.bm25_search import BM25Search
from app.services.chunker import chunk_text_hierarchical
from evaluation import metrics
from evaluation.evaluate import _retrieved_doc_ids
from tests.conftest import add_document

EVAL_DIR = Path(__file__).resolve().parent.parent / "evaluation"


@pytest.fixture
def corpus_db(syro_db):
    for md in sorted((EVAL_DIR / "corpus").rglob("*.md")):
        if md.parent.name == "corpus":
            continue
        text = md.read_text(encoding="utf-8")
        chunks = [c["text"] for c in chunk_text_hierarchical(text)]
        add_document(syro_db, 1, md.name, text, domain=md.parent.name, chunks=chunks)
    return syro_db


def _run(domain_filter: bool) -> dict:
    dataset = json.loads((EVAL_DIR / "eval_dataset.json").read_text(encoding="utf-8"))
    bm25 = BM25Search()
    items = []
    for item in dataset:
        domain = item["domain"] if domain_filter else None
        results = bm25.search(1, item["question"], top_k=10, domain=domain)
        items.append(
            {
                "retrieved_ids": _retrieved_doc_ids(results),
                "relevant_ids": item.get("relevant_doc_ids", []),
                "intent": item.get("intent"),
            }
        )
    return metrics.aggregate_retrieval(items)


@pytest.mark.parametrize("domain_filter", [False, True])
def test_bm25_golden_set_floor(corpus_db, domain_filter):
    report = _run(domain_filter)
    assert report["recall@10"] >= 0.9
    assert report["mrr"] >= 0.75
