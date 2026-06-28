"""Grid-search du paramètre RRF k sur le golden set (T2.3).

La fusion dense/sparse utilise désormais RRF pur (pas de pondération α) ;
seul ``rrf_k`` est tunable ici. Nécessite une stack live (Qdrant + embeddings)
et le corpus d'éval ingéré.

Usage:
    cd Syro
    python evaluation/tune.py
    python evaluation/tune.py --rrf-grid 30,40,60 --metric ndcg@10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

EVAL_DIR = Path(__file__).resolve().parent
SYRO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(SYRO_ROOT))
sys.path.insert(0, str(EVAL_DIR))

from app.config import settings  # noqa: E402
from app.services.rag import retrieve_chunks_with_metadata  # noqa: E402

import metrics as retrieval_metrics  # noqa: E402

from evaluate import (  # noqa: E402
    DATASET_PATH,
    ORGANIZATION_ID,
    _load_doc_filenames,
    _retrieved_doc_ids,
)

DEFAULT_RRF_GRID = (30, 40, 60)
DEFAULT_METRIC = "ndcg@10"


RetrieveFn = Callable[[str, str | None, dict[str, str]], list[str]]


def default_retrieve(question: str, domain: str | None, id_to_name: dict[str, str]) -> list[str]:
    """Retrieval-only : noms de fichiers ordonnés (sans génération LLM)."""
    results = retrieve_chunks_with_metadata(
        organization_id=ORGANIZATION_ID,
        query=question,
        domain=domain,
    )
    return _retrieved_doc_ids(results, id_to_name)


def collect_retrieval_items(
    dataset: list[dict],
    retrieve_fn: RetrieveFn,
    id_to_name: dict[str, str],
) -> list[dict]:
    items: list[dict] = []
    for item in dataset:
        question = item["question"]
        domain = item.get("domain")
        retrieved_ids = retrieve_fn(question, domain, id_to_name)
        items.append(
            {
                "retrieved_ids": retrieved_ids,
                "relevant_ids": item.get("relevant_doc_ids", []),
                "intent": item.get("intent", "unlabeled"),
            }
        )
    return items


def score_rrf_k(
    rrf_k: int,
    dataset: list[dict],
    retrieve_fn: RetrieveFn,
    id_to_name: dict[str, str],
) -> dict:
    """Évalue un ``rrf_k`` en patchant settings le temps du run."""
    previous = settings.rrf_k
    settings.rrf_k = rrf_k
    try:
        items = collect_retrieval_items(dataset, retrieve_fn, id_to_name)
        report = retrieval_metrics.aggregate_retrieval(items)
        report["rrf_k"] = rrf_k
        return report
    finally:
        settings.rrf_k = previous


def select_best_rrf_k(
    grid_reports: list[dict],
    metric: str = DEFAULT_METRIC,
) -> dict:
    """Choisit le rrf_k maximisant ``metric`` (ignore NaN)."""
    best: dict | None = None
    best_value = float("-inf")
    for report in grid_reports:
        value = report.get(metric)
        if value is None or (isinstance(value, float) and value != value):
            continue
        if value > best_value:
            best_value = value
            best = report
    if best is None:
        raise ValueError(f"Aucun score valide pour la métrique {metric!r}")
    return best


def run_grid_search(
    dataset: list[dict],
    rrf_grid: tuple[int, ...] = DEFAULT_RRF_GRID,
    metric: str = DEFAULT_METRIC,
    retrieve_fn: RetrieveFn | None = None,
    id_to_name: dict[str, str] | None = None,
) -> dict:
    id_to_name = id_to_name or _load_doc_filenames()

    def _default(q: str, d: str | None, names: dict[str, str]) -> list[str]:
        return default_retrieve(q, d, names)

    retrieve = retrieve_fn or _default
    grid_reports = [
        score_rrf_k(k, dataset, retrieve, id_to_name) for k in rrf_grid
    ]
    best = select_best_rrf_k(grid_reports, metric=metric)
    return {
        "metric": metric,
        "rrf_grid": list(rrf_grid),
        "best": best,
        "all": grid_reports,
        "note": (
            "Fusion dense/sparse = RRF pur (α déprécié). "
            "Seul rrf_k est tuné ; appliquer le gagnant dans config.py / .env."
        ),
    }


def main() -> dict:
    parser = argparse.ArgumentParser(description="Grid-search RRF k (T2.3)")
    parser.add_argument(
        "--rrf-grid",
        default=",".join(str(k) for k in DEFAULT_RRF_GRID),
        help="Valeurs rrf_k séparées par des virgules (défaut: 30,40,60)",
    )
    parser.add_argument(
        "--metric",
        default=DEFAULT_METRIC,
        help="Métrique à maximiser (défaut: ndcg@10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVAL_DIR / "tune_report.json",
        help="Fichier JSON de sortie",
    )
    args = parser.parse_args()
    rrf_grid = tuple(int(x.strip()) for x in args.rrf_grid.split(",") if x.strip())

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Golden set: {len(dataset)} questions")
    print(f"Grid rrf_k: {rrf_grid}  |  metric: {args.metric}\n")

    result = run_grid_search(dataset, rrf_grid=rrf_grid, metric=args.metric)

    print("=" * 44)
    print("RRF k grid-search (retrieval-only)")
    print("=" * 44)
    for report in result["all"]:
        k = report["rrf_k"]
        score = report.get(args.metric, float("nan"))
        mark = " <-- best" if k == result["best"]["rrf_k"] else ""
        print(f"  rrf_k={k:<4}  {args.metric}={score:.4f}{mark}")
    print("=" * 44)
    print(f"\nRecommandation: RRF_K={result['best']['rrf_k']} "
          f"({args.metric}={result['best'].get(args.metric):.4f})")

    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport → {args.output}")
    return result


if __name__ == "__main__":
    main()
