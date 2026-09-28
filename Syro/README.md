# Syro — référence technique

Présentation, démarrage et scénario de démo : [README principal](../README.md).
Cette page sert au développement : API, configuration, commandes.

## Démarrer

```bash
docker compose up -d --build                                # stack complète
docker compose exec syro-api python scripts/load_demo.py    # documents de démo
```

Aucun `.env` n'est nécessaire : Ollama local, secret JWT généré, compte démo `demo@syro.local` / `syro-demo`.

### Développement local (API avec hot reload)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt                     # + requirements-ml.txt pour le reranker
cp .env.example .env    # décommenter QDRANT_URL / OLLAMA_BASE_URL (localhost) et CELERY_TASK_ALWAYS_EAGER=true
make dev                # Qdrant + Redis + Ollama en Docker, API sur :8000
cd frontend && npm install && npm run dev               # UI sur :5173
```

## Commandes

| Commande | Rôle |
|---|---|
| `make up` / `make down` | Démarrer / arrêter la stack (données conservées) |
| `make demo` | Charger les 19 documents de démo |
| `make logs` | Logs API + worker |
| `make reindex` | Réindexer tout (après un changement de modèle d'embedding ou de chunking) |
| `make test` | 147 tests, sans aucun service externe |
| `make lint` / `make format` | Ruff + Black (comme la CI) |
| `make eval-retrieval` | Recall/nDCG/MRR sur la stack réelle → `evaluation/report.json` |
| `make eval` | + RAGAS (`pip install -r evaluation/requirements-eval.txt`) |

## API

Swagger interactif : http://localhost:8000/docs. Authentification : `POST /auth/login` (form `username`, `password`), puis `Authorization: Bearer <token>`.

| Endpoint | Description |
|---|---|
| `POST /chat/message` | `{content, conversation_id?, domain?}` → `{message, sources[], conversation_id, usage}` |
| `POST /chat/message/stream` | SSE : `event: sources` (JSON), puis les fragments `data:`, puis `data: [DONE]` (`event: error` en cas d'échec) |
| `POST /domains/{domain}/chat/message` | Idem, domaine imposé dans l'URL |
| `POST /documents/files` | Multipart `file`, `domain?`, `tags?` → `queued` |
| `POST /documents/text` | `{title, content, domain?, tags?}` |
| `POST /documents/upload-with-classification` | Upload + domaine détecté renvoyé immédiatement |
| `GET /documents` · `GET /documents/{id}` · `DELETE /documents/{id}` | Liste, statut d'ingestion, suppression |
| `GET /health` · `GET /health/ready` | Liveness · état de Qdrant, du LLM et du reranker |
| `GET /domains` | Domaines disponibles |
| `/admin/*` | Organisation de l'appelant uniquement : utilisateurs, crédits |
| `/permissions/*`, `/profile/*`, `/mlops/*` | Permissions documentaires, profil, métriques MLflow |

`domain` absent ou `general` : recherche dans tous les documents autorisés. Sinon, filtre sur ce domaine et persona dédiée.

Codes d'erreur du chat : `404` (conversation d'un autre utilisateur, domaine inconnu), `503` (LLM indisponible), `402` (crédits épuisés), `429` (limite de débit).

## Configuration

Toutes les variables sont dans [`.env.example`](.env.example) (source : `app/config.py`). Les principales :

| Variable | Défaut | Effet |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` ou `openai` |
| `CHAT_MODEL` / `EMBEDDINGS_MODEL` | `llama3.2` / `nomic-embed-text` | Modèles |
| `EMBEDDING_DIMENSIONS` | `768` | Doit correspondre au modèle (1536 pour `text-embedding-3-small`) |
| `PERFORMANCE_MODE` | `quality` | `quality` = reranker ; `fast` = sans reranker, moins de candidats |
| `RETRIEVAL_TOP_K` / `RERANK_TOP_K` | `20` / `5` | Candidats par retriever / chunks envoyés au LLM |
| `RERANK_MIN_SCORE` | `0.02` | Seuil d'abstention du cross-encoder |
| `CHUNK_SIZE_TOKENS` / `CHUNK_OVERLAP_TOKENS` | `400` / `60` | Chunking (réindexer après modification) |
| `ENABLE_QUERY_REWRITING`, `ENABLE_HYDE`, `ENABLE_CRAG`, `ENABLE_SELF_RAG`, `ENABLE_QUERY_DECOMPOSITION`, `ENABLE_SEMANTIC_CACHE` | `false` | Couches optionnelles |
| `SECRET_KEY` | *(généré)* | Vide : généré puis stocké dans le volume de données |
| `SYRO_ADMIN_EMAIL` / `SYRO_ADMIN_PASSWORD` | compte démo | Créé au premier démarrage |
| `WITH_RERANKER` (build) | `true` | `false` : image sans torch (plus légère), ordre RRF seul |

**Changer de modèle d'embedding** : les dimensions changent, donc utilisez une nouvelle `QDRANT_COLLECTION_NAME` puis lancez `make reindex`. L'API refuse explicitement une collection dont la dimension ne correspond pas.

## Organisation du code

| Module | Rôle |
|---|---|
| `services/rag.py` | Indexation transactionnelle ; point d'entrée du retrieval (cache → décomposition / CRAG / hybride) |
| `services/hybrid_search.py` | Dense + BM25 en parallèle, `fuse_rrf`, `rerank_or_truncate` |
| `services/vector_store.py` | Qdrant : une collection, filtres `organization_id` / `domain` / `document_id` indexés |
| `services/bm25_search.py` | Index BM25 par organisation, invalidé par empreinte SQL (ingestion faite par le worker) |
| `services/reranker.py` | Cross-encoder, sigmoïde, seuil d'abstention |
| `services/llm.py` | Ollama/OpenAI, préfixes d'embedding, cache, circuit breaker, prompt RAG |
| `services/chunker.py` | Découpe par titres puis par fenêtres de tokens ; tableaux Markdown préservés |
| `services/ingestion.py` | Extraction → domaine → indexation, statut `queued/processing/complete/failed` |
| `services/chat.py` | Conversations (contrôle de propriété), retrieval, génération, sources |
| `services/domain_detector.py` | Classement FR/EN par mots-clés |
| `services/crag.py`, `self_rag.py`, `decompose.py`, `hyde.py`, `query_rewriter.py`, `semantic_cache.py` | Couches optionnelles |

Base de données : `db/schema.sql`, créée et mise à niveau automatiquement au démarrage (`scripts/init_db.py`).
