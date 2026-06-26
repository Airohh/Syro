# Syro — Multi-Domain RAG Platform

> Production-grade Retrieval-Augmented Generation platform with hybrid search, cross-encoder reranking, multi-domain routing, async ingestion, and full MLOps observability.

---

## Overview

Syro is a multi-tenant RAG API that lets organizations upload documents and query them with an LLM grounded strictly in their own knowledge base. It supports **7 independent domains** (Tech, Medical, Legal, Finance, Education, MLOps, General), each with domain-specific system prompts, isolated Qdrant collections, and fine-tuned retrieval parameters.

```
User query
    │
    ▼
Domain Router ──────────────────────────────────────────────────┐
    │                                                            │
    ▼                                                            │
BM25 Search ──┐                                                  │
              ├──► Score fusion (α·vector + (1-α)·BM25)         │
Vector Search ┘         │                                        │
    (Qdrant)            ▼                                        │
                   BGE Reranker                                  │
                (cross-encoder v2-m3)                            │
                        │                                        │
                        ▼                                        │
                  Top-K chunks ──► LLM (Ollama / OpenAI) ◄──────┘
                                        │
                                        ▼
                              Answer + cited sources
```

---

## Stack

| Layer | Technology |
|-------|------------|
| **API** | FastAPI 0.111, Pydantic v2, Uvicorn |
| **Auth** | JWT (PyJWT), bcrypt (passlib) |
| **Database** | SQLite (WAL mode, foreign keys) |
| **Vector DB** | Qdrant (per-domain collections, HNSW) |
| **Lexical search** | rank-bm25 (in-memory, per-org) |
| **Reranker** | BAAI/bge-reranker-v2-m3 (FlagEmbedding) |
| **Embeddings** | nomic-embed-text via Ollama / OpenAI |
| **LLM** | Ollama (llama3.2) or OpenAI (gpt-4o-mini) |
| **Async ingestion** | Celery + Redis |
| **MLOps** | MLflow experiment tracking + custom alerting |
| **Observability** | Prometheus metrics, OpenTelemetry tracing, structured JSON logs |
| **Frontend** | React + TypeScript + Vite + Electron |
| **Infra** | Docker Compose (API, Worker, Qdrant, Redis, MLflow) |
| **Evaluation** | RAGAS (faithfulness, answer relevancy, context recall, context precision) |
| **Tests** | pytest (28 test files, unit + integration markers) |

---

## Features

- **Hybrid search** — configurable α-weighted fusion of dense (Qdrant cosine) and sparse (BM25) retrieval
- **Cross-encoder reranking** — BGE-reranker-v2-m3, GPU/CPU auto-detection, combined score weighting
- **Multi-domain routing** — 7 domains with isolated vector collections and system prompts; auto-detection via ML classifier
- **Adaptive performance** — automatic fast/quality mode switching based on rolling latency window
- **Multi-tenant** — organization-scoped data, per-role permissions, document access levels, share links
- **Async ingestion** — Celery workers process uploads (chunking → embedding → indexing) without blocking the API
- **Streaming responses** — SSE streaming with citation sources
- **RAGAS evaluation** — reproducible benchmark on 20 Q/A pairs across Tech and MLOps domains
- **MLOps** — MLflow experiment tracking, alerting thresholds, benchmark endpoint
- **Security** — rate limiting (Redis or in-memory), CORS, security headers, file validation (MIME + size), HTTPS-ready
- **Resilience** — LLM timeouts + retries, circuit breaker (fail-fast when the backend is down), graceful degradation to BM25-only search if embeddings are unavailable

---

## Domains

| ID | Name | Description |
|----|------|-------------|
| `tech` | SyroTech | Data Engineering, Python, SQL, Cloud, Architecture |
| `medical` | SyroMed | Medicine, pathologies, diagnostics, pharmacology |
| `legal` | SyroLegal | Civil, commercial, and criminal law, jurisprudence |
| `finance` | SyroFinance | Finance, accounting, investments, markets |
| `education` | SyroEdu | Pedagogy, curriculum, learning psychology |
| `mlops` | SyroMLOps | MLOps, model deployment, monitoring, CI/CD |
| `general` | Syro | General-purpose polyvalent assistant |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Ollama running locally (or an OpenAI API key)

### 1. Clone and configure

```bash
git clone <repo-url>
cd Syro/Syro/Syro
cp .env.example .env
# Edit .env: set SECRET_KEY, and either OPENAI_API_KEY or OLLAMA_BASE_URL
```

### 2. Launch all services

```bash
# Quick start (dev/demo): API + Worker + Qdrant + Redis + MLflow
docker-compose up -d

# Production (full stack): + Frontend + Postgres + Prometheus/Grafana
docker-compose -f infra/docker-compose.yml up -d

# With local Ollama LLM
docker-compose -f infra/docker-compose.yml -f infra/docker-compose.local-llm.yml up -d
```

Quick-start services:
- **API** → http://localhost:8000 (Swagger at `/docs`)
- **Celery Worker** → async document ingestion
- **Qdrant** → http://localhost:6333
- **Redis** → localhost:6379 (Celery broker)
- **MLflow** → http://localhost:5000

### 3. Initialize the database

```bash
docker-compose exec api python scripts/init_db.py
```

### 4. Create your first organization and user

```bash
# Create organization (owner token required — see docs)
curl -X POST http://localhost:8000/admin/organizations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "credit_balance": 1000}'

# Create a user
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"organization_id": 1, "email": "alice@acme.com", "password": "secret", "role": "member"}'
```

### 5. Login and get a token

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=alice@acme.com&password=secret"
```

### 6. Upload a document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@my_doc.pdf"
```

### 7. Chat

```bash
# General chat (auto-detects domain)
curl -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "What does the document say about X?"}'

# Domain-specific chat
curl -X POST http://localhost:8000/domains/tech/chat/message \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "How do I optimize a Spark join?"}'
```

---

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start Redis (for Celery)
docker run -p 6379:6379 redis:7-alpine

# Initialize DB
python scripts/init_db.py

# Run API
uvicorn app.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A app.worker worker --loglevel=info
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Get JWT token |
| POST | `/chat/message` | Chat (auto domain detection) |
| POST | `/chat/stream` | SSE streaming chat |
| POST | `/domains/{domain}/chat/message` | Chat on specific domain |
| POST | `/domains/{domain}/chat/stream` | SSE streaming on specific domain |
| POST | `/documents/upload` | Upload document (async ingestion) |
| GET | `/documents` | List documents |
| DELETE | `/documents/{id}` | Delete document |
| POST | `/domains/{domain}/documents/upload` | Upload to specific domain |
| GET | `/domains` | List all domains |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/mlops/metrics` | MLflow experiment metrics |
| POST | `/mlops/benchmark` | Run latency benchmark across modes |
| GET | `/admin/organizations` | List orgs (owner only) |
| POST | `/admin/users` | Create user (owner/admin) |
| GET | `/admin/organizations/{id}/users` | List users in org |
| GET | `/profile/me` | Get current user profile |
| PUT | `/profile/me` | Update profile |
| GET | `/permissions/{user_id}` | Get user permissions |

Full interactive docs: http://localhost:8000/docs

---

## RAGAS Evaluation

Syro ships with a reproducible evaluation suite (20 Q/A pairs across Tech and MLOps domains).

```bash
# Install eval dependencies
pip install -r evaluation/requirements-eval.txt

# Run with OpenAI judge (default)
export OPENAI_API_KEY=sk-...
python evaluation/evaluate.py

# Run with Ollama judge
USE_OLLAMA=true python evaluation/evaluate.py
```

Results are written to `evaluation/results.json`.

| Metric | Score |
|--------|-------|
| Faithfulness | — |
| Answer Relevancy | — |
| Context Recall | — |
| Context Precision | — |

> Run `python evaluation/evaluate.py` to populate scores.

---

## Configuration

All settings are read from environment variables or `.env` file. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-change-me` | **Change in production** |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `CHAT_MODEL` | `llama3.2` | Model name |
| `EMBEDDINGS_MODEL` | `nomic-embed-text` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `768` | Must match the embedding model |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint |
| `LLM_TIMEOUT` | `60` | Chat LLM call timeout (seconds) |
| `EMBEDDING_TIMEOUT` | `30` | Embedding call timeout (seconds) |
| `LLM_MAX_RETRIES` | `2` | Automatic retries on transient LLM errors |
| `CIRCUIT_BREAKER_THRESHOLD` | `5` | Consecutive failures before the breaker opens |
| `CIRCUIT_BREAKER_RESET_SECONDS` | `30` | Cool-down before a half-open trial call |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant endpoint |
| `DB_PATH` | `db/syro.db` | SQLite database path |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis for Celery |
| `PERFORMANCE_MODE` | `quality` | `fast`, `quality`, or `adaptive` |
| `ENABLE_RERANKING` | `true` | Enable BGE cross-encoder reranker |
| `HYBRID_SEARCH_ALPHA` | `0.7` | Vector weight in hybrid search (0=BM25, 1=vector) |
| `RETRIEVAL_TOP_K` | `10` | Candidates before reranking |
| `RERANK_TOP_K` | `5` | Final chunks sent to LLM |
| `RERANK_WEIGHT` | `0.7` | Reranker score weight in final score |
| `MLOPS_ENABLED` | `true` | Enable MLflow tracking |
| `TRACING_ENABLED` | `false` | Enable OpenTelemetry tracing |
| `CORS_ALLOW_ORIGINS` | `*` | Comma-separated origins in production |

See `.env.example` for the full list.

---

## Architecture

```
Syro/
├── app/
│   ├── main.py              # FastAPI app, middleware, routers
│   ├── config.py            # Pydantic settings
│   ├── domains.py           # Domain configs (7 domains)
│   ├── auth.py              # JWT + bcrypt
│   ├── dependencies.py      # FastAPI Depends (auth, db, rate limit)
│   ├── schemas.py           # Pydantic request/response models
│   ├── db.py                # SQLite connection, db_session context manager
│   ├── routers/
│   │   ├── auth.py          # POST /auth/login
│   │   ├── chat.py          # Chat endpoints (standard + domain)
│   │   ├── documents.py     # Upload, list, delete
│   │   ├── admin.py         # Org/user management (owner/admin)
│   │   ├── permissions.py   # Per-user permission management
│   │   ├── profile.py       # User profile CRUD
│   │   ├── agents.py        # Agent-mode endpoints
│   │   └── mlops.py         # MLflow metrics, benchmark, alerts
│   ├── services/
│   │   ├── chat.py          # build_answer, conversation management
│   │   ├── rag.py           # Hybrid retrieval orchestration
│   │   ├── vector_store.py  # Qdrant client (reconnect-safe)
│   │   ├── bm25_search.py   # In-memory BM25 index
│   │   ├── reranker.py      # BGE cross-encoder reranker
│   │   ├── llm.py           # LLM + embedding calls
│   │   ├── ingestion.py     # Document chunking + indexing pipeline
│   │   ├── celery_client.py # Celery task dispatch + BackgroundTasks fallback
│   │   ├── domain_detector.py  # ML-based domain auto-detection
│   │   ├── multi_domain_rag.py # Cross-domain search
│   │   ├── permissions_service.py  # Access level + quality level gates
│   │   ├── stats_service.py    # Usage statistics
│   │   ├── adaptive_performance.py  # Latency-based mode switching
│   │   ├── mlops_tracker.py    # MLflow wrapper
│   │   └── mlops_alerts.py     # Threshold-based alerting
│   ├── middleware/
│   │   ├── logging.py       # Structured JSON logging
│   │   ├── metrics.py       # Prometheus middleware
│   │   └── tracing.py       # OpenTelemetry setup
│   └── security/
│       ├── rate_limiter.py  # Redis/in-memory rate limiting
│       └── upload_validator.py  # MIME + size validation
├── db/
│   ├── schema.sql           # Full schema with indexes, triggers, seed data
│   └── migration_profiles_permissions.sql  # Incremental migration
├── scripts/
│   └── init_db.py           # DB init + migration runner
├── evaluation/
│   ├── eval_dataset.json    # 20 Q/A pairs (Tech + MLOps)
│   ├── evaluate.py          # RAGAS evaluation script
│   ├── requirements-eval.txt
│   └── results.json         # Scores (generated by evaluate.py)
├── tests/                   # 28 test files (pytest)
├── docker-compose.yml       # Quick-start (API + Worker + Qdrant + Redis + MLflow)
├── Dockerfile
├── requirements.txt
└── infra/
    ├── docker-compose.yml               # Production (+ Frontend + Postgres + Prometheus/Grafana)
    ├── docker-compose.local-llm.yml     # Override: Ollama sidecar
    ├── docker-compose.openai.yml        # Override: OpenAI provider
    └── docker/                          # Per-service Dockerfiles
```

---

## Performance Modes

| Mode | top_k | rerank_top_k | Reranking | α (hybrid) | Use case |
|------|-------|--------------|-----------|------------|----------|
| `fast` | 5 | 3 | ✗ | 0.8 | High-throughput, latency-sensitive |
| `quality` | 15 | 5 | ✓ | 0.7 | Best answer quality |
| `adaptive` | 15 | 5 | ✓ | 0.7 | Auto-switch based on rolling latency |

Switch mode: `PERFORMANCE_MODE=fast` in `.env`, or via `/mlops/benchmark` to compare modes.

---

## Running Tests

```bash
pytest tests/ -v

# Only unit tests (no external services needed)
pytest tests/ -m unit -v

# Only integration tests
pytest tests/ -m integration -v
```

---

## License

MIT
