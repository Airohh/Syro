"""Latency benchmark for the Syro RAG pipeline.

Complements evaluate.py (RAGAS *quality*) by measuring *performance*:
retrieval-only vs end-to-end latency percentiles (p50/p95/p99), per domain.

Usage:
    cd Syro/Syro   (the directory containing the app/ folder)
    python evaluation/benchmark.py                 # 3 repeats over the eval dataset
    python evaluation/benchmark.py --repeats 10     # tighter percentiles
    python evaluation/benchmark.py --retrieval-only # skip the LLM generation call

Requirements:
    The Syro stack must be reachable (Qdrant + embeddings backend, and the LLM
    backend unless --retrieval-only). Documents must already be indexed for
    ORGANIZATION_ID (run the ingestion path first), otherwise latencies reflect
    the empty-corpus short-circuit and a warning is printed.

Stdlib only (statistics + time). No extra pip install beyond the app deps.
Reproducible: fixed dataset, fixed org id, seedless (timing only).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — mirror evaluate.py so app/ imports work without installing
# ---------------------------------------------------------------------------
EVAL_DIR = Path(__file__).resolve().parent
SYRO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(SYRO_ROOT))

from app.services.rag import retrieve_chunks_with_metadata  # noqa: E402
from app.services.llm import answer_from_context  # noqa: E402

DATASET_PATH = EVAL_DIR / "eval_dataset.json"
RESULTS_PATH = EVAL_DIR / "benchmark_results.json"
ORGANIZATION_ID = 1  # default org created by init_db.py


def _percentiles(values: list[float]) -> dict[str, float]:
    """p50/p95/p99 + min/max/mean in milliseconds, rounded."""
    if not values:
        return {}
    ordered = sorted(values)

    def pct(p: float) -> float:
        # nearest-rank percentile (no interpolation) — robust for small N
        k = max(0, min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1)))))
        return ordered[k]

    return {
        "n": len(values),
        "min_ms": round(ordered[0], 1),
        "p50_ms": round(pct(50), 1),
        "p95_ms": round(pct(95), 1),
        "p99_ms": round(pct(99), 1),
        "max_ms": round(ordered[-1], 1),
        "mean_ms": round(statistics.fmean(values), 1),
    }


def _time_one(question: str, domain: str | None, retrieval_only: bool) -> tuple[float, float, int]:
    """Return (retrieval_ms, end_to_end_ms, n_chunks) for one query."""
    t0 = time.perf_counter()
    results = retrieve_chunks_with_metadata(
        organization_id=ORGANIZATION_ID,
        query=question,
        domain=domain,
    )
    retrieval_ms = (time.perf_counter() - t0) * 1000
    contexts = [r["text"] for r in results]

    if retrieval_only or not contexts:
        return retrieval_ms, retrieval_ms, len(contexts)

    answer_from_context(question, contexts, domain=domain)
    end_to_end_ms = (time.perf_counter() - t0) * 1000
    return retrieval_ms, end_to_end_ms, len(contexts)


def main() -> dict:
    parser = argparse.ArgumentParser(description="Syro RAG latency benchmark")
    parser.add_argument("--repeats", type=int, default=3, help="passes over the dataset")
    parser.add_argument("--retrieval-only", action="store_true", help="skip LLM generation")
    parser.add_argument("--warmup", type=int, default=1, help="warmup queries excluded from stats")
    args = parser.parse_args()

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Dataset: {len(dataset)} questions × {args.repeats} repeats "
          f"({'retrieval-only' if args.retrieval_only else 'end-to-end'})\n")

    retrieval_ms: list[float] = []
    end_to_end_ms: list[float] = []
    per_domain: dict[str, list[float]] = {}
    empty_corpus = 0
    total = 0

    # Warmup — first calls pay model/connection cold-start; exclude from stats.
    for item in dataset[: args.warmup]:
        _time_one(item["question"], item.get("domain"), args.retrieval_only)

    for r in range(args.repeats):
        for item in dataset:
            question = item["question"]
            domain = item.get("domain")
            ret, e2e, n_chunks = _time_one(question, domain, args.retrieval_only)
            total += 1
            if n_chunks == 0:
                empty_corpus += 1
            retrieval_ms.append(ret)
            end_to_end_ms.append(e2e)
            per_domain.setdefault(domain or "general", []).append(e2e)
        print(f"  pass {r + 1}/{args.repeats} done")

    if empty_corpus:
        print(f"\n⚠️  {empty_corpus}/{total} queries returned 0 chunks — corpus likely "
              f"not indexed for org {ORGANIZATION_ID}. Latencies are NOT representative.")

    report = {
        "config": {
            "repeats": args.repeats,
            "retrieval_only": args.retrieval_only,
            "n_questions": len(dataset),
            "organization_id": ORGANIZATION_ID,
        },
        "retrieval": _percentiles(retrieval_ms),
        "end_to_end": _percentiles(end_to_end_ms),
        "per_domain_end_to_end": {d: _percentiles(v) for d, v in sorted(per_domain.items())},
        "empty_corpus_queries": empty_corpus,
    }

    print("\n" + "=" * 48)
    print("Latency (ms)        p50      p95      p99     mean")
    print("=" * 48)
    for label, stats in (("retrieval", report["retrieval"]), ("end_to_end", report["end_to_end"])):
        if stats:
            print(f"  {label:<14} {stats['p50_ms']:>8} {stats['p95_ms']:>8} "
                  f"{stats['p99_ms']:>8} {stats['mean_ms']:>8}")
    print("=" * 48)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved → {RESULTS_PATH}")
    return report


if __name__ == "__main__":
    main()
