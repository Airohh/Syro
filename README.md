# Syro — Multi-Domain RAG Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Retrieval-Augmented Generation platform with hybrid search, cross-encoder reranking, multi-domain routing, async ingestion, and MLOps observability.**

[Quick Start](Syro/README.md#quick-start) • [Full Documentation](Syro/README.md) • [Architecture](docs/architecture.md) • [Evaluation](#evaluation)

</div>

---

## What is Syro?

Syro is a multi-tenant RAG API: organizations upload documents and query them with an LLM grounded strictly in their own knowledge base. Retrieval combines vector search (Qdrant) and lexical search (BM25), refined by a BGE cross-encoder reranker. Seven specialized domains (Tech, Medical, Legal, Finance, Education, MLOps, General) each get isolated vector collections and tuned prompts.

```
Query ──► Domain Router ──► Hybrid Search ──► BGE Reranker ──► LLM ──► Answer + cited sources
                            (Qdrant + BM25)   (cross-encoder)   (Ollama / OpenAI)
```

Detailed architecture: [docs/architecture.md](docs/architecture.md) and [Syro/README.md](Syro/README.md#architecture).

## Repository layout

| Path | Purpose |
|------|---------|
| [`Syro/`](Syro/) | The application (FastAPI API, Celery worker, React frontend, Docker infra, tests) — **start here** |
| [`docs/`](docs/) | Architecture and getting-started guides |

## Quick Start

Full instructions (Docker Compose, env configuration, API usage) live in **[Syro/README.md](Syro/README.md#quick-start)**. Short version:

```bash
git clone https://github.com/Airohh/Syro.git
cd Syro/Syro
cp .env.example .env   # set SECRET_KEY + LLM provider
docker-compose up -d   # API + Worker + Qdrant + Redis + MLflow
docker-compose exec api python scripts/init_db.py
```

API: `http://localhost:8000` — Swagger docs at `/docs`.

## Evaluation

Syro ships a reproducible RAGAS evaluation suite (20 Q/A pairs, Tech + MLOps domains) measuring faithfulness, answer relevancy, context recall, and context precision:

```bash
pip install -r Syro/evaluation/requirements-eval.txt
python Syro/evaluation/evaluate.py
```

## Tests

```bash
cd Syro
pytest tests/ -m unit -v        # no external services needed
pytest tests/ -m integration -v
```

## Known limitations

- **SQLite** for metadata: fine for a single-node deployment, not for horizontal scaling (Postgres compose profile exists in `infra/` but is not the default).
- **BM25 index is in-memory** and rebuilt per process: large corpora (>100k chunks) will increase startup time and RAM usage.
- **Multi-tenancy is logical** (organization-scoped queries), not physical isolation — no per-tenant quotas or billing.
- **Language**: chunking and BM25 tokenization are tuned for English/French prose; no CJK support.
- **LLM calls** are guarded by timeouts, automatic retries, and a circuit breaker (fail-fast when the backend is down); retrieval degrades to BM25-only if embeddings are unavailable. Answer quality in degraded mode is naturally lower.

## Contributing & License

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
