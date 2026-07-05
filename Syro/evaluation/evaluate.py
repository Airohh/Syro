"""RAGAS evaluation script for the Syro RAG pipeline.

Usage:
    cd Syro/Syro   (the directory containing the app/ folder)
    python evaluation/evaluate.py
    python evaluation/evaluate.py --retrieval-only   # retrieval metrics only (no LLM)

Requirements:
    pip install -r evaluation/requirements-eval.txt   # full RAGAS only

LLM judge:
    By default RAGAS uses OpenAI (set OPENAI_API_KEY env var).
    To use Ollama instead, set USE_OLLAMA=true in your env or .env file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allows importing from app/ without installing the package
# ---------------------------------------------------------------------------
EVAL_DIR = Path(__file__).resolve().parent
SYRO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(SYRO_ROOT))

# ---------------------------------------------------------------------------
# Pipeline imports
# ---------------------------------------------------------------------------
from app.services.rag import retrieve_chunks_with_metadata
from app.services.llm import answer_from_context
from app.config import settings
from app.db import db_session

import metrics as retrieval_metrics

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATASET_PATH = EVAL_DIR / "eval_dataset.json"
RESULTS_PATH = EVAL_DIR / "results.json"
ORGANIZATION_ID = 1  # default org created by init_db.py


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------
def _load_doc_filenames() -> dict[str, str]:
    """document_id (str) -> filename, pour relier les chunks récupérés aux
    `relevant_doc_ids` du golden set (qui sont des noms de fichiers)."""
    with db_session() as conn:
        rows = conn.execute("SELECT id, filename FROM documents").fetchall()
    return {str(r["id"]): r["filename"] for r in rows}


def _retrieved_doc_ids(results: list[dict], id_to_name: dict[str, str]) -> list[str]:
    """Noms de fichiers des docs récupérés, ordre préservé, dédupliqués.
    chunk_id = "{org}_{document_id}_{chunk}" (cf. rag.index_document_content)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for r in results:
        parts = str(r.get("chunk_id", "")).split("_")
        if len(parts) < 3:
            continue
        name = id_to_name.get(parts[1])
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def run_pipeline(
    question: str, domain: str | None = None, id_to_name: dict[str, str] | None = None
) -> tuple[str, list[str], list[str]]:
    """Call the Syro RAG pipeline and return (answer, contexts, retrieved_doc_ids)."""
    results = retrieve_chunks_with_metadata(
        organization_id=ORGANIZATION_ID,
        query=question,
        domain=domain,
    )
    contexts = [r["text"] for r in results]
    doc_ids = _retrieved_doc_ids(results, id_to_name or {})
    if not contexts:
        return "Aucun document indexé trouvé.", [], doc_ids
    answer, _ = answer_from_context(question, contexts, domain=domain)
    return answer, contexts, doc_ids


def run_retrieval_only(dataset_raw: list[dict]) -> dict:
    """Retrieval live sans LLM ni RAGAS — écrit report.json pour le gate T1.4."""
    id_to_name = _load_doc_filenames()
    retrieval_items: list[dict] = []
    times: list[float] = []

    for i, item in enumerate(dataset_raw):
        question = item["question"]
        domain = item.get("domain")
        print(f"[{i+1:02d}/{len(dataset_raw)}] {question[:70]}...")

        t0 = time.perf_counter()
        results = retrieve_chunks_with_metadata(
            organization_id=ORGANIZATION_ID,
            query=question,
            domain=domain,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)
        retrieved_ids = _retrieved_doc_ids(results, id_to_name)
        print(f"         → {len(results)} chunks, {elapsed_ms:.0f}ms")

        retrieval_items.append({
            "retrieved_ids": retrieved_ids,
            "relevant_ids": item.get("relevant_doc_ids", []),
            "intent": item.get("intent", "unlabeled"),
        })

    retrieval_report = retrieval_metrics.aggregate_retrieval(retrieval_items)
    avg_ms = sum(times) / len(times) if times else 0.0

    print("\n" + "=" * 44)
    print("Retrieval metrics (live, deterministic, no LLM)")
    print("=" * 44)
    for key in ("recall@5", "recall@10", "ndcg@10", "mrr", "hit@5", "oob_refusal_rate"):
        val = retrieval_report.get(key)
        if val is not None and val == val:
            print(f"  {key:<22} {val:.4f}")
    print(f"  ranked {retrieval_report['n_ranked']}/{retrieval_report['n_total']}  | avg {avg_ms:.0f} ms/q")
    print("=" * 44)

    output = {
        "retrieval_metrics": retrieval_report,
        "avg_pipeline_latency_ms": round(avg_ms, 1),
        "n_questions": len(dataset_raw),
        "mode": "retrieval_only",
    }
    report_path = EVAL_DIR / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved → {report_path}")
    return output


# ---------------------------------------------------------------------------
# RAGAS LLM/Embeddings configuration
# ---------------------------------------------------------------------------
def _build_ragas_llm():
    """Return a LangchainLLMWrapper configured for the active provider."""
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    use_ollama = os.getenv("USE_OLLAMA", "").lower() in ("1", "true", "yes")
    provider = settings.llm_provider.lower()

    if use_ollama or (provider == "ollama" and not settings.openai_api_key):
        base_url = settings.ollama_base_url or "http://localhost:11434/v1"
        llm = ChatOpenAI(
            model=settings.chat_model,
            base_url=base_url,
            api_key="ollama",
            temperature=0,
        )
        print(f"RAGAS judge: Ollama ({settings.chat_model} @ {base_url})")
    else:
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Either set it or use Ollama (USE_OLLAMA=true)."
            )
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
        print("RAGAS judge: OpenAI (gpt-4o-mini)")

    return LangchainLLMWrapper(llm)


def _build_ragas_embeddings():
    """Return a LangchainEmbeddingsWrapper configured for the active provider."""
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import OpenAIEmbeddings

    use_ollama = os.getenv("USE_OLLAMA", "").lower() in ("1", "true", "yes")
    provider = settings.llm_provider.lower()

    if use_ollama or (provider == "ollama" and not settings.openai_api_key):
        base_url = settings.ollama_base_url or "http://localhost:11434/v1"
        embedder = OpenAIEmbeddings(
            model=settings.embeddings_model,
            base_url=base_url,
            api_key="ollama",
        )
    else:
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        embedder = OpenAIEmbeddings(api_key=api_key)

    return LangchainEmbeddingsWrapper(embedder)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> dict:
    parser = argparse.ArgumentParser(description="Syro RAG evaluation (RAGAS + retrieval metrics)")
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Mesure retrieval live uniquement (pas de LLM/RAGAS) → report.json",
    )
    args = parser.parse_args()

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset_raw = json.load(f)

    print(f"Dataset loaded: {len(dataset_raw)} questions\n")

    if args.retrieval_only:
        return run_retrieval_only(dataset_raw)

    try:
        from ragas import evaluate, EvaluationDataset
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision
    except ImportError:
        print("ERROR: ragas is not installed. Run: pip install -r evaluation/requirements-eval.txt")
        sys.exit(1)

    ragas_llm = _build_ragas_llm()
    ragas_embeddings = _build_ragas_embeddings()

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
        ContextRecall(llm=ragas_llm),
        ContextPrecision(llm=ragas_llm),
    ]

    samples = []
    pipeline_times = []
    retrieval_items = []  # pour les métriques de retrieval déterministes (T1.2)
    id_to_name = _load_doc_filenames()

    for i, item in enumerate(dataset_raw):
        question: str = item["question"]
        ground_truth: str = item["ground_truth"]
        domain: str | None = item.get("domain")

        print(f"[{i+1:02d}/{len(dataset_raw)}] {question[:70]}...")

        t0 = time.perf_counter()
        answer, contexts, retrieved_ids = run_pipeline(question, domain=domain, id_to_name=id_to_name)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_times.append(elapsed_ms)

        print(f"         → {len(contexts)} chunks, {elapsed_ms:.0f}ms")

        samples.append({
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts,
            "reference": ground_truth,
        })
        retrieval_items.append({
            "retrieved_ids": retrieved_ids,
            "relevant_ids": item.get("relevant_doc_ids", []),
            "intent": item.get("intent", "unlabeled"),
        })

    # Métriques de retrieval déterministes (sur les paires annotées relevant_doc_ids)
    retrieval_report = retrieval_metrics.aggregate_retrieval(retrieval_items)
    print("\n" + "=" * 40)
    print("Retrieval metrics (deterministic)")
    print("=" * 40)
    for key in ("recall@5", "recall@10", "ndcg@10", "mrr", "oob_refusal_rate"):
        if key in retrieval_report:
            print(f"  {key:<22} {retrieval_report[key]:.4f}")
    print(f"  (ranked {retrieval_report['n_ranked']}/{retrieval_report['n_total']})")

    print(f"\nAll {len(samples)} questions processed.")
    print(f"Avg pipeline latency: {sum(pipeline_times)/len(pipeline_times):.0f}ms\n")

    eval_dataset = EvaluationDataset.from_list(samples)

    print("Running RAGAS evaluation (this calls the LLM judge for each sample)...")
    result = evaluate(eval_dataset, metrics=metrics)

    df = result.to_pandas()

    scores: dict[str, float] = {}
    for col in ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]:
        if col in df.columns:
            scores[col] = round(float(df[col].dropna().mean()), 4)

    print("\n" + "=" * 40)
    print("RAGAS Scores")
    print("=" * 40)
    for metric, score in scores.items():
        bar = "█" * int(score * 20)
        print(f"  {metric:<22} {score:.4f}  {bar}")
    print("=" * 40)

    output = {
        "generation_metrics": scores,  # RAGAS (LLM judge)
        "retrieval_metrics": retrieval_report,  # déterministe (T1.2)
        "scores": scores,  # rétro-compat
        "avg_pipeline_latency_ms": round(sum(pipeline_times) / len(pipeline_times), 1),
        "n_questions": len(samples),
        "per_question": df.to_dict(orient="records"),
    }

    for path in (RESULTS_PATH, EVAL_DIR / "report.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved → {RESULTS_PATH} and report.json")
    return scores


if __name__ == "__main__":
    main()
