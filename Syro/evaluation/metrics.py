"""Métriques de retrieval déterministes (ticket T1.2).

Séparées des métriques de génération (RAGAS, dans evaluate.py) : si la
faithfulness baisse, c'est presque toujours le retrieval — il faut le mesurer
indépendamment. Ces métriques ne demandent pas de LLM.

Toutes prennent :
    retrieved : list[str]  -- doc ids récupérés, ordonnés (rang 0 = meilleur)
    relevant  : set[str]   -- doc ids pertinents (ground truth)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Proportion des docs pertinents retrouvés dans le top-k."""
    if not relevant:
        return float("nan")  # non défini sans pertinents (cf. out_of_corpus)
    top = set(retrieved[:k])
    return len(top & relevant) / len(relevant)


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Proportion de docs pertinents parmi le top-k (dénominateur = k)."""
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    hits = sum(1 for d in top if d in relevant)
    return hits / k


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """1 / rang (1-indexé) du premier doc pertinent ; 0 si aucun."""
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """nDCG@k en pertinence binaire."""
    if not relevant:
        return float("nan")
    dcg = 0.0
    for i, doc in enumerate(retrieved[:k]):
        if doc in relevant:
            dcg += 1.0 / math.log2(i + 2)  # i=0 -> log2(2)=1
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """1.0 si au moins un doc pertinent dans le top-k, sinon 0.0."""
    if not relevant:
        return float("nan")
    return 1.0 if set(retrieved[:k]) & relevant else 0.0


def _mean(values: Iterable[float]) -> float:
    vals = [v for v in values if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def aggregate_retrieval(items: list[dict], ks: tuple[int, ...] = (5, 10)) -> dict:
    """Agrège les métriques de retrieval sur le golden set.

    Chaque item : {"retrieved_ids": [...], "relevant_ids": [...], "intent": str?}.
    Les questions sans pertinents (out_of_corpus) sont exclues du ranking et
    comptées à part via le taux de refus si `retrieved_ids` est vide.
    """
    ranked = [it for it in items if it.get("relevant_ids")]
    report: dict = {"n_total": len(items), "n_ranked": len(ranked)}

    for k in ks:
        report[f"recall@{k}"] = _mean(
            recall_at_k(it["retrieved_ids"], set(it["relevant_ids"]), k) for it in ranked
        )
        report[f"precision@{k}"] = _mean(
            precision_at_k(it["retrieved_ids"], set(it["relevant_ids"]), k) for it in ranked
        )
        report[f"ndcg@{k}"] = _mean(
            ndcg_at_k(it["retrieved_ids"], set(it["relevant_ids"]), k) for it in ranked
        )
        report[f"hit@{k}"] = _mean(
            hit_at_k(it["retrieved_ids"], set(it["relevant_ids"]), k) for it in ranked
        )
    report["mrr"] = _mean(
        reciprocal_rank(it["retrieved_ids"], set(it["relevant_ids"])) for it in ranked
    )

    # out_of_corpus : refus correct = aucun doc récupéré.
    oob = [it for it in items if not it.get("relevant_ids")]
    if oob:
        correct_refusals = sum(1 for it in oob if not it.get("retrieved_ids"))
        report["oob_refusal_rate"] = correct_refusals / len(oob)
        report["n_oob"] = len(oob)

    by_intent = Counter(it.get("intent", "unlabeled") for it in items)
    report["by_intent"] = dict(by_intent)

    # Alias plats pour validate_retrieval_thresholds.py (recall_at_10 vs recall@10).
    for k in ks:
        if f"recall@{k}" in report:
            report[f"recall_at_{k}"] = report[f"recall@{k}"]
        if f"ndcg@{k}" in report:
            report[f"ndcg_at_{k}"] = report[f"ndcg@{k}"]
        if f"hit@{k}" in report:
            report[f"hit_at_{k}"] = report[f"hit@{k}"]

    return report
