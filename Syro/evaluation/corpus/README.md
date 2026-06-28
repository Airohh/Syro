# Evaluation corpus

Curated knowledge base used by the reproducible RAGAS benchmark
(`evaluation/evaluate.py`). Each Markdown file is a focused reference document;
the folder name (`tech/`, `mlops/`) is the domain the document is ingested under.

The corpus covers exactly the topics probed by `eval_dataset.json`, so the
benchmark measures retrieval + generation on content that is actually indexed —
not on an empty store.

## Golden set (`eval_dataset.json`)

100 paires Q/A étendues (ticket T1.1). Schéma par paire :

| champ | rôle |
|-------|------|
| `question` / `ground_truth` | requête + réponse de référence |
| `domain` | `tech` \| `mlops` |
| `intent` | bucket : `factual_lookup`, `exact_identifier`, `multi_hop`, `out_of_corpus` |
| `relevant_doc_ids` | fichiers corpus pertinents (= `documents.filename`) ; `[]` si hors-corpus (refus attendu) |

Les 20 paires historiques n'ont pas encore `intent`/`relevant_doc_ids` (à
annoter). Les questions `out_of_corpus` servent à mesurer le taux de refus.

### Régénérer / étendre

```bash
python evaluation/build_golden_set.py   # idempotent : merge les paires curées, dédup par question
```

> Qualité (risque R1) : `ground_truth` et `relevant_doc_ids` sont rédigés
> depuis le corpus mais demandent une relecture annotateur (DA) avant d'être
> traités comme vérité de référence à 100 %.

## Usage

```bash
cd Syro/Syro
python scripts/init_db.py          # create org 1 + schema (once)
python evaluation/ingest_corpus.py # chunk -> embed -> Qdrant
python evaluation/evaluate.py      # run RAGAS (USE_OLLAMA=true for Ollama judge)
```

Prerequisites: Qdrant running and an embeddings backend reachable
(Ollama `nomic-embed-text` or OpenAI).
