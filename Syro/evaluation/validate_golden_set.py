"""Gate d'intégrité du golden set (ticket T1.4, volet déterministe sans LLM).

« Eval as continuous engineering » : bloquer au merge toute régression du jeu
d'évaluation lui-même (R1 — un golden set cassé = mesures non fiables). Ce
contrôle est pur (pas de stack, pas de LLM) → exécutable en CI via la suite lean.

Vérifie :
    - schéma minimal (question, ground_truth, domain) ;
    - domaine ∈ {tech, mlops} ;
    - intent (si présent) ∈ buckets connus ;
    - relevant_doc_ids pointent vers des fichiers corpus existants ;
    - out_of_corpus ⇒ relevant_doc_ids vide ; sinon non-vide pour les paires annotées ;
    - pas de question dupliquée ;
    - taille mini et nombre de buckets mini.

Le seuil qualité sur Recall@10/nDCG (retrieval live) reste un gate séparé qui
demande Qdrant + embeddings (job nightly ou CI avec services), cf. T1.4 suite.
"""

from __future__ import annotations

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "eval_dataset.json"
CORPUS_DIR = EVAL_DIR / "corpus"

VALID_DOMAINS = {"tech", "mlops"}
VALID_INTENTS = {"factual_lookup", "exact_identifier", "multi_hop", "out_of_corpus"}
MIN_PAIRS = 100
MIN_BUCKETS = 4


def corpus_filenames() -> set[str]:
    return {p.name for p in CORPUS_DIR.rglob("*.md") if p.name != "README.md"}


def validate_dataset(dataset: list[dict], corpus: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    buckets: set[str] = set()

    for i, item in enumerate(dataset):
        tag = f"[{i}] {str(item.get('question', '?'))[:50]}"
        for field in ("question", "ground_truth", "domain"):
            if not item.get(field):
                errors.append(f"{tag}: champ manquant '{field}'")

        if item.get("domain") not in VALID_DOMAINS:
            errors.append(f"{tag}: domaine invalide {item.get('domain')!r}")

        norm = " ".join(str(item.get("question", "")).lower().split())
        if norm in seen:
            errors.append(f"{tag}: question dupliquée")
        seen.add(norm)

        intent = item.get("intent")
        if intent is not None:
            buckets.add(intent)
            if intent not in VALID_INTENTS:
                errors.append(f"{tag}: intent invalide {intent!r}")

        ids = item.get("relevant_doc_ids")
        if ids is not None:
            if intent == "out_of_corpus":
                if ids:
                    errors.append(f"{tag}: out_of_corpus doit avoir relevant_doc_ids vide")
            for doc in ids:
                if doc not in corpus:
                    errors.append(f"{tag}: relevant_doc_id absent du corpus: {doc}")

    if len(dataset) < MIN_PAIRS:
        errors.append(f"taille golden set {len(dataset)} < {MIN_PAIRS}")
    if len(buckets) < MIN_BUCKETS:
        errors.append(f"buckets d'intention {len(buckets)} < {MIN_BUCKETS} ({sorted(buckets)})")

    return errors


def main() -> None:
    import sys

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    errors = validate_dataset(dataset, corpus_filenames())
    if errors:
        print(f"Golden set INVALIDE ({len(errors)} erreurs):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"Golden set OK: {len(dataset)} paires, intégrité validée.")


if __name__ == "__main__":
    main()
