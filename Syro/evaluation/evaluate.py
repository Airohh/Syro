"""RAGAS evaluation script for the Syro RAG pipeline.

Usage:
    cd Syro/Syro   (the directory containing the app/ folder)
    python evaluation/evaluate.py

Requirements:
    pip install -r evaluation/requirements-eval.txt

LLM judge:
    By default RAGAS uses OpenAI (set OPENAI_API_KEY env var).
    To use Ollama instead, set USE_OLLAMA=true in your env or .env file.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATASET_PATH = EVAL_DIR / "eval_dataset.json"
RESULTS_PATH = EVAL_DIR / "results.json"
ORGANIZATION_ID = 1  # default org created by init_db.py


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------
def run_pipeline(question: str, domain: str | None = None) -> tuple[str, list[str]]:
    """Call the Syro RAG pipeline and return (answer, contexts)."""
    results = retrieve_chunks_with_metadata(
        organization_id=ORGANIZATION_ID,
        query=question,
        domain=domain,
    )
    contexts = [r["text"] for r in results]
    if not contexts:
        return "Aucun document indexé trouvé.", []
    answer, _ = answer_from_context(question, contexts, domain=domain)
    return answer, contexts


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
    try:
        from ragas import evaluate, EvaluationDataset
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision
    except ImportError:
        print("ERROR: ragas is not installed. Run: pip install -r evaluation/requirements-eval.txt")
        sys.exit(1)

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset_raw = json.load(f)

    print(f"Dataset loaded: {len(dataset_raw)} questions\n")

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

    for i, item in enumerate(dataset_raw):
        question: str = item["question"]
        ground_truth: str = item["ground_truth"]
        domain: str | None = item.get("domain")

        print(f"[{i+1:02d}/{len(dataset_raw)}] {question[:70]}...")

        t0 = time.perf_counter()
        answer, contexts = run_pipeline(question, domain=domain)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_times.append(elapsed_ms)

        print(f"         → {len(contexts)} chunks, {elapsed_ms:.0f}ms")

        samples.append({
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts,
            "reference": ground_truth,
        })

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
        "scores": scores,
        "avg_pipeline_latency_ms": round(sum(pipeline_times) / len(pipeline_times), 1),
        "n_questions": len(samples),
        "per_question": df.to_dict(orient="records"),
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved → {RESULTS_PATH}")
    return scores


if __name__ == "__main__":
    main()
