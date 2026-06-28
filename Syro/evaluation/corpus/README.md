# Evaluation corpus

Curated knowledge base used by the reproducible RAGAS benchmark
(`evaluation/evaluate.py`). Each Markdown file is a focused reference document;
the folder name (`tech/`, `mlops/`) is the domain the document is ingested under.

The corpus covers exactly the topics probed by `eval_dataset.json` (20 Q/A
pairs across Tech and MLOps), so the benchmark measures retrieval + generation
on content that is actually indexed — not on an empty store.

## Usage

```bash
cd Syro/Syro
python scripts/init_db.py          # create org 1 + schema (once)
python evaluation/ingest_corpus.py # chunk -> embed -> Qdrant
python evaluation/evaluate.py      # run RAGAS (USE_OLLAMA=true for Ollama judge)
```

Prerequisites: Qdrant running and an embeddings backend reachable
(Ollama `nomic-embed-text` or OpenAI).
