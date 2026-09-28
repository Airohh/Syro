# Graph Report - Syro  (2026-09-28)

## Corpus Check
- 146 files · ~66,661 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .Dockerfile 2, .example 1)

## Summary
- 1434 nodes · 3081 edges · 78 communities (69 shown, 9 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 98 edges (avg confidence: 0.91)
- Token cost: 115,198 input · 0 output

## Community Hubs (Navigation)
- Frontend React UI
- DB Sessions & Celery Client
- BM25 & Qdrant Stores
- LLM Provider & Circuit Breaker
- Document Extraction & Chunking
- MLOps Tracking & Alerts
- Semantic Cache
- Hybrid Search & CRAG Orchestration
- Core Python Dependencies
- Cross-Encoder Reranker
- SQLite Schema
- Document Upload API
- CRAG Quality Assessment
- JWT Auth & Dependencies
- Document Permissions
- Langfuse Tracing
- Profile API & DB Access
- LLM Query Rewriting
- Chat RAG Service
- Retrieval Metrics
- HyDE Embeddings
- RAGAS Evaluation Script
- Security Middleware & Rate Limit
- Query Decomposition
- Pydantic Schemas
- RRF k Tuning
- Frontend Package Deps
- TypeScript Config
- Chat HTTP Endpoints
- Self-RAG Filtering
- Architecture Decisions (ADR)
- Retrieval Design Fixes
- RAG Roadmap
- Hybrid Search Tests
- App Entry & Health
- Domain Classification
- Golden Set Gate
- Org Admin API
- Frontend Dev Tooling
- Test Fixtures
- Retrieval Threshold Gate
- Docker Stack & Simplification
- Demo Corpus Loader
- CI Pipeline
- Settings & Secret Key
- DB Init & Migration
- End-to-End API Test
- Latency Benchmark
- Domain Personas
- Keyword Domain Detector
- Golden Set Builder
- Prometheus Gauges
- Relevance Scoring
- Frontend Runtime Deps
- OpenTelemetry Setup
- Evaluation Docs
- Smoke Test
- HTTP Metrics Middleware
- Vite Node TS Config
- Observability Stack
- Logging Package
- Conversation Ownership
- Tracing Span API
- SSE Framing
- Ranking Metric Tests
- JSON Log Formatter
- CORS Settings
- Correlation ID Middleware
- Chat 500 Diagnostic
- Frontend npm Scripts
- Prometheus Histograms
- Qdrant Error Handler
- Vite Build Config
- Test Package

## God Nodes (most connected - your core abstractions)
1. `db_session()` - 35 edges
2. `hybrid_search()` - 25 edges
3. `VectorStoreError` - 24 edges
4. `VectorStore` - 23 edges
5. `getDomainConfig()` - 23 edges
6. `ROADMAP_RAG plan d'execution RAG` - 20 edges
7. `README principal Syro` - 20 edges
8. `ingest_document()` - 19 edges
9. `react` - 19 edges
10. `BM25Search` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Une collection Qdrant, filtres de payload` --semantically_similar_to--> `Une collection Qdrant, domain comme filtre de payload indexe`  [INFERRED] [semantically similar]
  README.md → CHANGEMENTS/ADR-002-collection-unique.md
- `T4.4 Coherence DB-Qdrant (outbox + reconciliation)` --semantically_similar_to--> `Indexation transactionnelle SQLite + Qdrant`  [INFERRED] [semantically similar]
  CHANGEMENTS/ROADMAP_RAG.md → docs/architecture.md
- `Robustesse (fallback BM25, circuit breaker 503, abstention)` --semantically_similar_to--> `Degradation BM25-only si embedding KO`  [INFERRED] [semantically similar]
  docs/architecture.md → CHANGEMENTS/diagnostic-chat-500.md
- `requirements-ml.txt (reranker torch)` --implements--> `Cross-encoder bge-reranker-v2-m3 apres fusion`  [INFERRED]
  Syro/requirements-ml.txt → README.md
- `requirements.txt (runtime)` --conceptually_related_to--> `Observabilite (Prometheus /metrics, MLflow, Langfuse, logs JSON)`  [INFERRED]
  Syro/requirements.txt → docs/architecture.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Hybrid retrieval pipeline: permissions -> dense+BM25 -> RRF -> cross-encoder -> abstention** — readme_permissions_before_search, readme_hybrid_search, readme_rrf_fusion, readme_cross_encoder_reranker, readme_abstention_threshold, docs_architecture_question_flow [EXTRACTED 1.00]
- **Optional opt-in RAG layers (off by default)** — changements_roadmap_rag_query_rewriting, changements_roadmap_rag_hyde, changements_roadmap_rag_crag, changements_roadmap_rag_self_rag, changements_roadmap_rag_query_decomposition, changements_roadmap_rag_semantic_cache [EXTRACTED 1.00]
- **Docker backend stack sharing syro-backend image and its dependencies** — syro_docker_compose_backend_anchor, syro_docker_compose_syro_api, syro_docker_compose_syro_worker, syro_docker_compose_qdrant, syro_docker_compose_redis, syro_docker_compose_ollama_init, syro_docker_compose_mlflow [EXTRACTED 1.00]

## Communities (78 total, 9 thin omitted)

### Community 0 - "Frontend React UI"
Cohesion: 0.05
Nodes (78): ADR-0001, lucide-react, react, react-router-dom, App(), NOTE: Avec l'architecture multi-domaines, un seul login suffit, ChatBubble(), ChatBubbleProps (+70 more)

### Community 1 - "DB Sessions & Celery Client"
Cohesion: 0.05
Nodes (51): celery, object, pytest, db_session(), get_connection(), Connection, enqueue_document_ingestion(), get_celery_app() (+43 more)

### Community 2 - "BM25 & Qdrant Stores"
Cohesion: 0.06
Nodes (38): BM25Okapi, Exception, Filter, QdrantClient, BM25Search, Any, Minuscules, sans accents, sans mots vides (« Évaluer » → « evaluer »)., (nombre, id max) des chunks actifs de l'org. L'index vit en mémoire par… (+30 more)

### Community 3 - "LLM Provider & Circuit Breaker"
Cohesion: 0.06
Nodes (30): RuntimeError, CircuitBreaker, Breaker thread-safe à trois états implicites : closed / open / half-open. -…, True si l'appel peut être tenté maintenant., build_messages(), build_system_prompt(), _EmbeddingCache, _estimate_tokens() (+22 more)

### Community 4 - "Document Extraction & Chunking"
Cohesion: 0.06
Nodes (38): docx, docx_oxml_ns, docx_table, docx_text_paragraph, io, Paragraph, pypdf, _chunk_simple() (+30 more)

### Community 5 - "MLOps Tracking & Alerts"
Cohesion: 0.08
Nodes (24): email_mime_multipart, email_mime_text, Enum, httpx, mlflow, mlflow_tracking, smtplib, export_metrics() (+16 more)

### Community 6 - "Semantic Cache"
Cohesion: 0.12
Nodes (22): CacheScopeKey, _CacheEntry, _copy_chunks(), _cosine_similarity(), _filters_key(), _history_key(), _pipeline_key(), Any (+14 more)

### Community 7 - "Hybrid Search & CRAG Orchestration"
Cohesion: 0.11
Nodes (32): atexit, concurrent_futures, ndarray, Retrieval hybride avec passe corrective optionnelle si pertinence faible., retrieve_with_crag(), Any, ndarray, Query decomposition multi-hop (T3.3). Décompose les questions composées en… (+24 more)

### Community 8 - "Core Python Dependencies"
Cohesion: 0.11
Nodes (21): langchain_core_messages, langchain_openai, pydantic_settings, qdrant_client, qdrant_client_models, rank_bm25, re, Middleware pour logging structuré avec correlation IDs. (+13 more)

### Community 9 - "Cross-Encoder Reranker"
Cohesion: 0.09
Nodes (15): Any, Charge le modèle à la demande ; un échec de chargement est mémorisé (sinon…, Pré-charge le modèle (appelé au démarrage dans un thread)., Probabilités de pertinence [0, 1] (sigmoïde des logits), ou None., Trie par score cross-encoder et écarte les passages sous le seuil. Retourne…, Reranker, _sigmoid(), FlagReranker (+7 more)

### Community 10 - "SQLite Schema"
Cohesion: 0.14
Nodes (30): api_keys, conversations, doc_chunks, document_access_levels, document_quality_levels, document_shares, documents, events (+22 more)

### Community 11 - "Document Upload API"
Cohesion: 0.15
Nodes (29): BackgroundTasks, delete, normalize_domain(), Domaine valide en minuscules, ou None si absent/inconnu., _check_upload_permission(), delete_document(), get_document_status(), get_document_status_domain() (+21 more)

### Community 12 - "CRAG Quality Assessment"
Cohesion: 0.12
Nodes (17): assess_retrieval_quality(), lexical_overlap(), _merge_chunk_lists(), Any, _query_terms(), Fraction des termes significatifs de la question présents dans les chunks., Pertinence (0–1) du meilleur chunk : cross-encoder, sinon RRF normalisé., Évaluateur léger sans LLM : overlap lexical + pertinence du meilleur chunk.… (+9 more)

### Community 13 - "JWT Auth & Dependencies"
Cohesion: 0.11
Nodes (21): datetime, FastAPI, fastapi_security, jwt, OAuth2PasswordRequestForm, passlib_context, create_access_token(), decode_token() (+13 more)

### Community 14 - "Document Permissions"
Cohesion: 0.14
Nodes (26): check_document_access(), get_my_permissions(), get_user_permissions_endpoint(), list_access_levels(), list_quality_levels(), Connection, get, put (+18 more)

### Community 15 - "Langfuse Tracing"
Cohesion: 0.15
Nodes (16): flush(), _get_client(), log_event(), log_generation(), log_retrieval(), _NoOpHandle, Any, rag_trace() (+8 more)

### Community 16 - "Profile API & DB Access"
Cohesion: 0.13
Nodes (21): sqlite3, get_db(), get_my_profile(), get_profile_documents(), get_profile_stats(), Connection, get, put (+13 more)

### Community 17 - "LLM Query Rewriting"
Cohesion: 0.14
Nodes (15): collections_abc, _llm_decompose(), Sous-requêtes via LLM (fallback si heuristiques insuffisantes)., _llm_rewrite_variants(), _parse_rewrite_lines(), Query rewriting / expansion avant retrieval (T2.1)., Extrait des variantes une réponse LLM (une reformulation par ligne)., Appelle le chat LLM pour produire 1–2 reformulations (sans l'originale). (+7 more)

### Community 18 - "Chat RAG Service"
Cohesion: 0.14
Nodes (22): build_answer(), build_answer_stream(), format_sources(), _history_strings(), Any, Service de chat RAG : conversation → retrieval → génération → sources., Sources renvoyées à l'UI : numérotées comme dans le prompt ([Source N])., Domaine explicite → filtre + persona. Sinon : tous les documents, persona… (+14 more)

### Community 19 - "Retrieval Metrics"
Cohesion: 0.12
Nodes (18): collections, math, aggregate_retrieval(), hit_at_k(), _mean(), ndcg_at_k(), precision_at_k(), Métriques de retrieval déterministes (ticket T1.2). Séparées des métriques de… (+10 more)

### Community 20 - "HyDE Embeddings"
Cohesion: 0.15
Nodes (15): numpy, generate_hypothetical_passage(), get_hyde_embedding_vector(), ndarray, HyDE — Hypothetical Document Embeddings (T2.2). Génère un passage hypothétique…, Produit un court passage plausible répondant à la question ('' si échec)., Embedding du passage hypothétique, ou None si HyDE désactivé / échec., complete() (+7 more)

### Community 21 - "RAGAS Evaluation Script"
Cohesion: 0.14
Nodes (20): parametrize, _build_ragas_embeddings(), _build_ragas_llm(), main(), RAGAS evaluation script for the Syro RAG pipeline. Usage: cd Syro/Syro (the…, Return a LangchainLLMWrapper configured for the active provider., Return a LangchainEmbeddingsWrapper configured for the active provider., Noms de fichiers des documents récupérés (ordre conservé, dédupliqués). Le… (+12 more)

### Community 22 - "Security Middleware & Rate Limit"
Cohesion: 0.11
Nodes (14): redis, starlette_middleware_base, BaseHTTPMiddleware, Request, Headers de sécurité HTTP., Middleware pour ajouter des headers de sécurité HTTP., SecurityHeadersMiddleware, Sécurité HTTP : rate limiting et en-têtes. (+6 more)

### Community 23 - "Query Decomposition"
Cohesion: 0.15
Nodes (13): decompose(), Découpe « Q1? Q2? » en sous-questions distinctes., Découpe les clauses séparées par « ; »., Retourne la question originale ou une liste de sous-requêtes., _split_multi_question(), _split_semicolon_clauses(), _chunk(), patch (+5 more)

### Community 24 - "Pydantic Schemas"
Cohesion: 0.18
Nodes (20): BaseModel, pydantic, AccessLevel, DocumentClassification, DocumentShare, DocumentStats, DocumentTextUpload, DocumentUploadResponse (+12 more)

### Community 25 - "RRF k Tuning"
Cohesion: 0.18
Nodes (15): pathlib, RetrieveFn, collect_retrieval_items(), main(), Grid-search du paramètre RRF k sur le golden set (T2.3). La fusion dense/sparse…, Évalue un ``rrf_k`` en patchant settings le temps du run., Choisit le rrf_k maximisant ``metric`` (ignore NaN)., run_grid_search() (+7 more)

### Community 26 - "Frontend Package Deps"
Cohesion: 0.10
Nodes (20): autoprefixer, axios, clsx, dompurify, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, postcss (+12 more)

### Community 27 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+10 more)

### Community 28 - "Chat HTTP Endpoints"
Cohesion: 0.31
Nodes (17): _answer(), _answer_stream(), generate(), _check_domain(), _open_conversation(), Connection, post, Endpoints de chat. POST /chat/message réponse JSON complète (+ sources) POST… (+9 more)

### Community 29 - "Self-RAG Filtering"
Cohesion: 0.24
Nodes (10): chunk_relevance_score(), filter_relevant_chunks(), Any, Proxy IsRel [0–1] : overlap question↔chunk + score retrieval normalisé., Filtre les chunks peu pertinents avant injection dans le prompt LLM. - Drop si…, _chunk(), patch, Tests Self-RAG (T3.2) — filtrage IsRel par chunk. (+2 more)

### Community 30 - "Architecture Decisions (ADR)"
Cohesion: 0.18
Nodes (17): ADR-001 Modele multi-domaines, Option A: multi-domaines mono-API, Multi-instances par port (alternative ecartee), ADR-002 Une collection Qdrant, domaine comme filtre, Bug BM25 vide ('domain:tech' vs 'tech'), Une collection Qdrant, domain comme filtre de payload indexe, CHANGEMENTS.md journal des changements, Session 2026-09-28 audit + remise a plat (+9 more)

### Community 31 - "Retrieval Design Fixes"
Cohesion: 0.15
Nodes (17): Reranker: sigmoide + tri + seuil (fin du melange RRF/min-max), RRF remplace normalisation min-max + alpha, Flux question (permissions -> dense/BM25 -> RRF -> cross-encoder -> LLM), README principal Syro, Seuil d'abstention RERANK_MIN_SCORE, Ingestion asynchrone Celery + Redis, Chunks de 400 tokens + titre de section, Reponses citees [Source N] (+9 more)

### Community 32 - "RAG Roadmap"
Cohesion: 0.18
Nodes (16): ROADMAP_RAG plan d'execution RAG, T3.1 CRAG corrective retrieval, Epics E0-E5 (stabilisation, mesure, retrieval, agentique, prod, multimodal), T3.4 GraphRAG (optionnel), T2.2 HyDE, Regle d'or: delta mesure sur golden set avant merge, T4.2 SQLite -> PostgreSQL, T3.3 Query decomposition multi-hop (+8 more)

### Community 33 - "Hybrid Search Tests"
Cohesion: 0.21
Nodes (10): patch, Non-régression retrieval : fusion RRF + dégradation BM25-only., Un chunk présent dans les deux listes doit remonter via la somme RRF, sans…, Embedding KO ne doit pas lever : on tombe sur BM25 seul, jamais de recherche…, Qdrant KO (VectorStoreError) ne doit pas lever : le chemin vectoriel est…, Plusieurs variantes → listes BM25/vector fusionnées par RRF (T2.1)., TestEmbeddingReuse, TestRRFFusion (+2 more)

### Community 34 - "App Entry & Health"
Cohesion: 0.17
Nodes (13): contextlib, fastapi_middleware_cors, fastapi_responses, healthcheck(), healthcheck_domain(), lifespan(), metrics(), get (+5 more)

### Community 35 - "Domain Classification"
Cohesion: 0.16
Nodes (8): classify_text(), Any, Classe un texte : {domain, confidence, alternatives}. `general` si aucun…, patch, Prompt RAG et préfixes d'embedding., TestBuildMessages, TestDomainDetector, TestPrefixes

### Community 36 - "Golden Set Gate"
Cohesion: 0.19
Nodes (9): corpus_filenames(), main(), Gate d'intégrité du golden set (ticket T1.4, volet déterministe sans LLM). «…, validate_dataset(), _load(), T1.4 (gate déterministe) : le golden set reste intègre à chaque merge., test_golden_set_is_valid(), test_golden_set_meets_minimums() (+1 more)

### Community 37 - "Org Admin API"
Cohesion: 0.27
Nodes (13): hash_password(), adjust_credits(), create_user(), get_my_organization(), list_users(), Connection, get, post (+5 more)

### Community 38 - "Frontend Dev Tooling"
Cohesion: 0.14
Nodes (14): devDependencies, autoprefixer, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, postcss, tailwindcss, @types/react (+6 more)

### Community 39 - "Test Fixtures"
Cohesion: 0.22
Nodes (12): app(), clear_dependency_overrides(), client(), mock_org(), mock_user(), fixture, Configuration globale pour pytest. Les markers (unit, integration, security,…, Vraie base SQLite (schéma complet) dans un dossier temporaire. Org 1 :… (+4 more)

### Community 40 - "Retrieval Threshold Gate"
Cohesion: 0.22
Nodes (10): argparse, check_thresholds(), load_json(), main(), Path, Gate seuils retrieval (T1.4) — compare report.json aux seuils configurables.…, Retourne la liste des violations (vide = gate OK)., Tests gate seuils retrieval (T1.4). (+2 more)

### Community 41 - "Docker Stack & Simplification"
Cohesion: 0.33
Nodes (12): Simplification (suppression agents, fan-out multi-domaines, mode adaptatif, compose multiples), docker-compose.yml stack complete, x-backend anchor (image syro-backend partagee), Service mlflow v2.14.0, Service ollama (LLM local), Service ollama-init (pull modeles), Service qdrant v1.11.0, Service redis (broker Celery) (+4 more)

### Community 42 - "Demo Corpus Loader"
Cohesion: 0.29
Nodes (11): existing_filenames(), login(), main(), Path, Charge le corpus de démo (evaluation/corpus) dans Syro via l'API HTTP. Passe…, Requête JSON ; attend et réessaie si l'API limite le débit (HTTP 429)., _request(), upload() (+3 more)

### Community 43 - "CI Pipeline"
Cohesion: 0.22
Nodes (10): CI workflow (ci.yml), CI job frontend (npm ci + build), CI job lint (ruff + black), CI job test (pytest + golden set integrity), T1.4 Eval en CI (gate seuils), T0.0 Suite de tests lean, CONTRIBUTING guide, Frontend index.html (Vite entry) (+2 more)

### Community 44 - "Settings & Secret Key"
Cohesion: 0.24
Nodes (5): BaseSettings, Garantit un secret JWT fort sans configuration manuelle. Si SECRET_KEY n'est…, Settings, Garde-fous sécurité : secret JWT + CORS wildcard/credentials., TestSecretKey

### Community 45 - "DB Init & Migration"
Cohesion: 0.20
Nodes (10): bcrypt, os, secrets, _backfill_domains(), _db_path(), Connection, Path, Initialise (ou met à niveau) la base SQLite. Idempotent. Appelé automatiquement… (+2 more)

### Community 46 - "End-to-End API Test"
Cohesion: 0.20
Nodes (7): fastapi_testclient, hashlib, api(), _bow_embed(), fixture, Parcours complet via l'API : login → upload → ingestion → chat avec sources.…, Sac de mots haché → vecteur normalisé (similarité ≈ recouvrement lexical).

### Community 47 - "Latency Benchmark"
Cohesion: 0.24
Nodes (9): statistics, answer_from_context(), Réponse complète. Lève LLMUnavailableError si le LLM est indisponible., main(), _percentiles(), Latency benchmark for the Syro RAG pipeline. Complements evaluate.py (RAGAS…, p50/p95/p99 + min/max/mean in milliseconds, rounded., Return (retrieval_ms, end_to_end_ms, n_chunks) for one query. (+1 more)

### Community 48 - "Domain Personas"
Cohesion: 0.24
Nodes (9): dataclasses, DomainConfig, get_domain_config(), list_domains(), Any, Domaines Syro : une persona par domaine. Un domaine sert à deux choses : (1) la…, Config du domaine ; `general` si inconnu ou absent., get_domains() (+1 more)

### Community 49 - "Keyword Domain Detector"
Cohesion: 0.27
Nodes (9): functools, Pattern, _fold(), _patterns(), Détection de domaine par mots-clés (FR + EN), sans modèle ML. Utilisée pour (1)…, Minuscules + suppression des accents (« Médecine » → « medecine »)., Nombre de mots-clés distincts trouvés par domaine., score_domains() (+1 more)

### Community 50 - "Golden Set Builder"
Cohesion: 0.22
Nodes (5): json, Counter, main(), _norm(), Construit/étend le golden set d'évaluation (ticket T1.1). Le golden set étendu…

### Community 51 - "Prometheus Gauges"
Cohesion: 0.22
Nodes (6): prometheus_client, Gauge, generate_latest(), get_metrics_response(), Middleware pour métriques Prometheus., Générer la réponse Prometheus pour /metrics.

### Community 52 - "Relevance Scoring"
Cohesion: 0.29
Nodes (7): chunk_relevance(), Any, Score RRF d'un chunk classé 1er par le dense ET par BM25 (= pertinence 1.0)., Score cross-encoder s'il existe (déjà une probabilité), sinon RRF normalisé., rrf_strong_score(), Reranker : score absolu (sigmoïde), tri, seuil d'abstention, repli RRF., TestRelevance

### Community 53 - "Frontend Runtime Deps"
Cohesion: 0.20
Nodes (10): dependencies, axios, clsx, dompurify, lucide-react, react, react-dom, react-router-dom (+2 more)

### Community 54 - "OpenTelemetry Setup"
Cohesion: 0.22
Nodes (8): opentelemetry, opentelemetry_exporter_otlp_proto_grpc_trace_exporter, opentelemetry_instrumentation_fastapi, opentelemetry_instrumentation_httpx, opentelemetry_sdk_resources, opentelemetry_sdk_trace, opentelemetry_sdk_trace_export, Middleware pour traces OpenTelemetry.

### Community 55 - "Evaluation Docs"
Cohesion: 0.25
Nodes (8): Evaluation (make test, eval-gate, eval-retrieval, eval RAGAS), requirements-eval.txt (RAGAS), Syro reference technique (README), API endpoints (chat, documents, domains, health), Organisation des services (rag, hybrid_search, vector_store, bm25_search, reranker, llm...), Variables de configuration (.env / app/config.py), Commandes make (up, demo, reindex, test, eval), Streaming SSE /chat/message/stream (sources avant tokens)

### Community 56 - "Smoke Test"
Cohesion: 0.32
Nodes (7): socket, check_http(), check_tcp(), main(), Smoke test post-deploiement : verifie que tous les services repondent. Usage…, urllib_error, urllib_request

### Community 57 - "HTTP Metrics Middleware"
Cohesion: 0.29
Nodes (6): MetricsMiddleware, BaseHTTPMiddleware, Request, Response, Middleware pour collecter les métriques HTTP., Normaliser le path pour éviter le cardinality explosion. Exemples:…

### Community 58 - "Vite Node TS Config"
Cohesion: 0.25
Nodes (7): compilerOptions, allowSyntheticDefaultImports, composite, module, moduleResolution, skipLibCheck, include

### Community 59 - "Observability Stack"
Cohesion: 0.33
Nodes (5): T1.3 Langfuse tracing RAG, Observabilite (Prometheus /metrics, MLflow, Langfuse, logs JSON), Service langfuse v2 (:3000), Service langfuse-db (postgres 16), Scrape job syro-api /metrics

### Community 60 - "Logging Package"
Cohesion: 0.29
Nodes (6): Logger, Middlewares pour observabilité., get_logger(), Obtenir un logger avec support du correlation ID. Usage: logger =…, Configurer OpenTelemetry tracing. Args: service_name: Nom du service…, setup_tracing()

### Community 61 - "Conversation Ownership"
Cohesion: 0.29
Nodes (7): LookupError, ConversationNotFound, get_or_create_conversation(), load_conversation_history(), Connection, Conversation existante APPARTENANT à l'utilisateur, ou nouvelle. Vérifier…, Derniers messages, du plus ancien au plus récent : [{role, content}].

### Community 63 - "SSE Framing"
Cohesion: 0.43
Nodes (6): Évènement SSE valide : un champ `data:` par ligne (sinon un `\\n` dans un…, _sse(), Non-régression cadrage SSE : un fragment multi-ligne reste un évènement valide., test_sse_empty_chunk_still_framed(), test_sse_multiline_prefixes_each_line(), test_sse_single_line()

### Community 65 - "JSON Log Formatter"
Cohesion: 0.33
Nodes (5): LogRecord, JSONFormatter, Formatter pour logs JSON structurés., Configurer le logging structuré. Args: log_level: Niveau de log (DEBUG, INFO,…, setup_logging()

### Community 66 - "CORS Settings"
Cohesion: 0.47
Nodes (3): Parse les origines CORS et neutralise la combinaison invalide…, resolve_cors_settings(), TestCorsSettings

### Community 67 - "Correlation ID Middleware"
Cohesion: 0.33
Nodes (5): CorrelationIDMiddleware, BaseHTTPMiddleware, Request, Response, Middleware pour ajouter un correlation ID à chaque requête.

### Community 68 - "Chat 500 Diagnostic"
Cohesion: 0.50
Nodes (5): Diagnostic erreur 500 /chat/message, Degradation BM25-only si embedding KO, LLM_TIMEOUT / EMBEDDING_TIMEOUT / LLM_MAX_RETRIES, Cause racine: get_embedding_vector non protege dans hybrid_search, Robustesse (fallback BM25, circuit breaker 503, abstention)

### Community 69 - "Frontend npm Scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, lint, preview

### Community 71 - "Qdrant Error Handler"
Cohesion: 0.67
Nodes (3): exception_handler, Request, vector_store_error_handler()

## Knowledge Gaps
- **110 isolated node(s):** `name`, `version`, `type`, `dev`, `build` (+105 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 501 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Reranker` connect `Cross-Encoder Reranker` to `Core Python Dependencies`, `Relevance Scoring`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `db_session()` connect `DB Sessions & Celery Client` to `BM25 & Qdrant Stores`, `Core Python Dependencies`, `Document Permissions`, `Profile API & DB Access`, `Chat HTTP Endpoints`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `hybrid_search()` connect `Hybrid Search & CRAG Orchestration` to `Core Python Dependencies`, `Hybrid Search Tests`, `HyDE Embeddings`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `VectorStoreError` (e.g. with `vector_store_error_handler()` and `delete_document()`) actually correct?**
  _`VectorStoreError` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _110 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend React UI` be split into smaller, more focused modules?**
  _Cohesion score 0.053958177744585514 - nodes in this community are weakly interconnected._
- **Should `DB Sessions & Celery Client` be split into smaller, more focused modules?**
  _Cohesion score 0.05413469735720375 - nodes in this community are weakly interconnected._