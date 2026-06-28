# Syro — Changements & pilotage

> **Documents de ce dossier**
> - **`ROADMAP_RAG.md`** — 📌 **Plan d'exécution team-ready** (diagnostic, archi cible, RACI, ways of working, 25 tickets, plan de sprints, chemin critique, risques, KPI, board de suivi). Document de référence pour piloter le travail.
> - `CHANGEMENTS.md` (ce fichier) — journal des changements de code par session.
> - `ADR-001-multidomaine.md` — décision d'architecture multi-domaines (ticket T0.4, statut **Proposed** — à valider TL).

---

## Session 2026-06-28 — T5.1 extraction tableaux

### T5.1 ✅ — DOCX/PDF tableaux → Markdown
- `file_extractor.py` : `doc.tables` + `pdfplumber` pour PDF ; helper `_rows_to_markdown_table`.
- `chunker.py` : blocs tableau Markdown préservés (pas de découpe au milieu des lignes).
- Dépendance : `pdfplumber==0.11.4`.
- Tests : +3 dans `test_extraction.py`. **108 tests verts.**

---

## Session 2026-06-28 — T4.5 cache sémantique

### T4.5 ✅ — semantic cache retrieval
- `semantic_cache.py` : hit si similarité embedding ≥ 0.95 ; TTL + max entries ; invalidation par domaine à l'ingestion.
- Branché dans `retrieve_chunks_with_metadata` (lookup avant retrieval, store après).
- Tests : `test_semantic_cache.py` (6). **105 tests verts.**

---

## Session 2026-06-28 — T1.3 Langfuse + T1.4 gate retrieval

### T1.3 ✅ — tracing Langfuse
- `app/services/langfuse_tracer.py` : trace racine + spans retrieval/generation ; no-op si off.
- `build_answer` unifié (multi-domaine + single) avec instrumentation Langfuse.
- `infra/docker-compose.langfuse.yml` : profil `--profile langfuse` (Postgres + Langfuse v2).
- `langfuse>=2,<3` dans requirements ; tests `test_langfuse_tracer.py` (4).

### T1.4 ✅ — gate seuils retrieval
- `evaluation/validate_retrieval_thresholds.py` + `retrieval_thresholds.json`.
- `make eval-retrieval-gate` (skip si pas de report.json).
- Tests `test_retrieval_gate.py` (3).

**99 tests verts.**

---

## Session 2026-06-28 — Vérification globale + T3.3 decomposition

### Vérification (audit session)
- **92 tests verts** (`pytest tests/ -q`)
- **Golden set** : 100 paires, `make eval-gate` OK
- **Imports** : smoke OK ; flags opt-in tous `false` par défaut
- **Pipeline chat** : router → history → scope permissions → retrieval → Self-RAG → LLM
- **Pipeline eval** : `retrieve_chunks_with_metadata` direct (pas Self-RAG/history — intentionnel pour métriques retrieval)
- **Lint** : 1 fix F841 `chat.py` ; E402 pré-existants dans `rag.py` (imports après logger)
- **Non commité** : ~15 fichiers nouveaux/modifiés sur branche locale

### T3.3 ✅ — query decomposition multi-hop
- `app/services/decompose.py` : split `?` / `;` + LLM fallback ; retrieval parallèle ; fusion RRF ; rerank.
- `rag.py` : `enable_query_decomposition` prioritaire sur CRAG.
- Tests : `test_decompose.py` (7).

---

## Session 2026-06-28 — T3.2 Self-RAG

### T3.2 ✅ — filtrage IsRel par chunk
- `app/services/self_rag.py` : score heuristique (overlap lexical + force retrieval) ; drop sous `self_rag_min_relevance` ; garde 3–8 chunks.
- `chat.py` : `_filter_chunk_results` après retrieval (multi-domaine, sync, stream) ; chemins unifiés sur `retrieve_chunks_with_metadata`.
- `config.py` : `ENABLE_SELF_RAG=false`, seuils min/max chunks.
- Tests : `test_self_rag.py` (7).

**85 tests verts.**

> Prochaine : **T3.3 query decomposition** ou finition E1 (T1.3 Langfuse, T1.4 gate live).

---

## Session 2026-06-28 (nuit) — T3.1 CRAG

### T3.1 ✅ — corrective retrieval
- `app/services/crag.py` : évaluateur léger (overlap lexical + score RRF top-1) → verdict correct/ambiguous/incorrect.
- Si faible : retry `hybrid_search` avec `top_k×2`, `expand_queries(force=True)` (reformulations même si T2.1 off).
- `rag.py` : branche `enable_crag` ; `hybrid_search` accepte `queries` explicites.
- `config.py` : `ENABLE_CRAG=false`, seuils `crag_retry_threshold` / `crag_incorrect_threshold`.
- Tests : `test_crag.py` (10).

**78 tests verts** (suite complète).

> Prochaine : **T3.2 Self-RAG** ou finition E1 (T1.3 Langfuse, T1.4 gate live, revue DA T1.1).

---

## Session 2026-06-28 (nuit) — T2.4 filtrage retrieval + T2.5 historique conversationnel

### T2.4 ✅ — metadata filtering avant ANN
- `app/services/retrieval_filters.py` : `RetrievalScope`, `build_retrieval_scope(user_id, org_id, domain)` ; `user_id=None` pour l'éval (pas de filtre permissions).
- `vector_store.py` : `allowed_document_ids` → filtre Qdrant `MatchAny` ; set vide → `[]` sans appel Qdrant.
- `bm25_search.py` : filtre document + domain **avant** scoring BM25.
- `hybrid_search.py`, `rag.py`, `multi_domain_rag.py`, `chat.py` : propagation scope + history.
- `routers/chat.py` : `user_id` passé à `build_answer` / stream (4 endpoints).
- Tests : `test_retrieval_filters.py` (7).

### T2.5 ✅ — historique dans retrieval + prompt
- `load_conversation_history(db, conversation_id, limit=6)` ; router charge l'historique avant le message user.
- `llm.py` : `conversation_history` dans `chat` / `chat_stream` / `answer_from_context*`.
- Tests : `test_conversation_history.py` (1) ; fix mock BM25 hybrid (`allowed_document_ids` kwarg).

**68 tests verts.** E2 (T2.1–T2.5) code complet — mesures live via `make tune` / `make eval` quand stack dispo.

> Prochaine : **T3.1 CRAG** ou finition E1 (T1.3 Langfuse, T1.4 gate live, revue DA T1.1).

---

## Session 2026-06-28 (soir) — T2.2 HyDE + T2.3 tuning RRF

### T2.2 ✅ — HyDE
- `app/services/hyde.py` : passage hypothétique LLM → embedding → liste vectorielle additionnelle fusionnée par RRF.
- `enable_hyde=false` par défaut (`ENABLE_HYDE=true` pour activer).
- Tests : `test_hyde.py` (5).

### T2.3 ✅ — grid-search `rrf_k`
- `evaluation/tune.py` : compare `rrf_k ∈ {30,40,60}` sur golden set (retrieval-only), sortie `tune_report.json`.
- `make tune` ; tests `test_tune.py` (4).
- Note : fusion α abandonnée → seul `rrf_k` est tunable.

**60 tests verts.**

> Prochaine : **T2.4** (metadata filtering Qdrant/BM25) ou **T2.5** (historique conversationnel) ; mesures T2.1–T2.3 via `make tune` / `make eval` quand stack dispo.

---

## Session 2026-06-28 (soir) — T2.1 query rewriting

### T2.1 ✅ — query rewriting (`feat(retrieval)`)
- `app/services/query_rewriter.py` : reformulations LLM (1–2 variantes + question originale), déduplication, fallback gracieux si LLM KO.
- `hybrid_search.py` : retrieval multi-variantes fusionné par RRF ; batch embeddings ; param `history` optionnel.
- `config.py` : `enable_query_rewriting=false` (opt-in via `ENABLE_QUERY_REWRITING=true`), `query_rewrite_max_variants=2`.
- Tests : **51 verts** (+6 `test_query_rewriter`, +1 hybrid multi-variante).

> Prochaine : T2.3 (tuning RRF, sans stack) ou T2.2 (HyDE) ; mesure T2.1 sur golden set quand stack dispo. E1 : T1.3 Langfuse (infra), finition T1.1 DA.

---

Branche : `fix/chat-500-resilience` · **9 commits, pushés** (`454a2aa..e7d31d6`).

### Code review du diff de branche
- 3 findings retenus ; 1 réfuté (`httpx` toujours pinné L9 de `requirements.txt`, le diff n'avait retiré qu'un doublon du bloc tests).

### Fixes résilience chat (`fix(chat)` 181a2c8)
- `routers/chat.py` : `send_message_for_domain` enveloppé en try/except + `db.rollback()` + 500 générique (parité avec `send_message`, qui était durci mais pas son jumeau domaine).
- `routers/chat.py` : helper `_sse()` — un fragment multi-ligne (markdown/code) ne casse plus le cadrage SSE (`data:` par ligne).
- `services/chat.py` : `detect_domain` gardé en try/except → fallback domaine défaut (était appelé hors du try de `build_answer`).

### Corpus d'éval idempotent (`fix(eval)` a53d81e)
- `evaluation/ingest_corpus.py` : `clear_previous_corpus()` purge les docs `source_type='corpus'` (chunks Qdrant via `delete_chunks_by_document` + lignes DB) avant ré-ingestion. Re-runs reproductibles, plus de doublons. Helper `_domain_from_tags`.

### Docs
- `docs/architecture.md` **archivé** : bannière « pas un backlog » + pointeur vers `ROADMAP_RAG.md` ; table d'état réel avec corrections (détection = mots-clés pas ML ; pas de colonne `organizations.domains` ; fusion multi-domaine = score×confiance, pas un rerank cross-encoder global).
- `ROADMAP_RAG.md` : ajout **T2.5** (historique conversationnel dans le RAG — stocké mais jamais réinjecté) et **T4.5** (cache sémantique) ; tables SP/board/sprints/total MAJ (23→25 tickets).

### T0.0 ✅ — suite de tests lean (`test(t0.0)` ed19791 + a674d71)
- `tests/conftest.py` (gardes GPU `CUDA_VISIBLE_DEVICES=""` + HF offline + stub `FlagEmbedding` → pas de download 20 Go), `pytest.ini` lean.
- **26 tests** : RRF par rang, fallback BM25 (embedding KO + Qdrant KO), résilience domain endpoint (500 sans fuite + rollback, 404 domaine inconnu), `_sse` multi-ligne, idempotence ingestion, extraction texte, secret prod + CORS wildcard.
- `requirements.txt` : `pytest`/`pytest-mock`/`pytest-cov` remis ; `Makefile` : `test`/`test-cov` ; `ci.yml` : job `test` **bloquant** (lint reste `|| true`, trou connu).
- Refactor testabilité : `resolve_cors_settings()` extrait de `main.py`.

### T0.2 ✅ — bug 500 chat clôturé (`test(t0.2)` e7d31d6)
- Non-régression : embedding KO + Qdrant KO (`VectorStoreError`) → BM25-only, jamais 500.

### Git
- Historique réécrit (les 3 commits de session avaient avalé les suppressions déjà staged) → 4 commits propres + chirurgie : `refactor` dé-scope / `fix(chat)` / `fix(eval)` / `docs`. Rien n'était pushé → sûr.

### T0.3 ✅ — fusion ingestion dupliquée (`refactor(ingestion)`)
- `app/services/ingestion.py` : nouveaux `run_ingestion()` (extract → métadonnées → index, lève en cas d'échec) et `infer_metadata()` (type/difficulté). `worker/tasks.py` (garde processing/complete/failed + metrics + retry) et `process_document` (BackgroundTasks) délèguent → ~80 lignes dupliquées supprimées. Edge `doc_row` manquant unifié sur `raise`. Tests : `tests/test_ingestion_pipeline.py`.

### T0.4 ✅ — ADR-001 multi-domaines Accepted (`docs(adr)` + `refactor(frontend)`)
- ADR-001 statut **Accepted** (Option A : mono-API + filtres Qdrant par domaine ; le code y était déjà de facto).
- `frontend/src/utils/domainPorts.ts` réduit à une source unique pilotée par `VITE_API_URL` ; constante morte `DOMAIN_PORTS` supprimée ; signatures conservées (aucun call-site cassé), `tsc --noEmit` clean.

> **Phase 0 (E0) complète** : T0.0–T0.4 tous ✅.

### T1.1 🟡 — golden set étendu (`feat(eval)`)
- `eval_dataset.json` porté à **100 paires** (schéma + `intent` + `relevant_doc_ids`). Buckets : factual 36, exact_identifier 28, multi_hop 8, out_of_corpus 8 (+ 20 legacy à annoter). `relevant_doc_ids` sur 72/100.
- Générateur reproductible `evaluation/build_golden_set.py` (paires curées depuis le corpus, dédup par question, idempotent). `corpus/README.md` documente le schéma + process.
- Reste : relecture annotateur (R1), annotation des 20 legacy, viser ~150. Débloque T1.2 (métriques retrieval Recall@K/nDCG via `relevant_doc_ids`).

### T1.2 ✅ — éval retrieval vs génération (`feat(eval)`)
- `evaluation/metrics.py` : métriques de ranking déterministes (Recall@K, Precision@K, nDCG@K, MRR, hit@K) + `oob_refusal_rate` + agrégation par bucket. Sans LLM. Tests : `tests/test_eval_metrics.py` (7).
- `evaluate.py` : mappe les chunks récupérés → `documents.filename` (via `chunk_id` `{org}_{doc}_{chunk}`), compare aux `relevant_doc_ids`, et écrit `report.json` séparant `retrieval_metrics` (déterministe) et `generation_metrics` (RAGAS). Scores réels = run avec stack.

### T1.4 🟡 — gate d'intégrité golden set en CI (`feat(eval)`)
- `evaluation/validate_golden_set.py` + `tests/test_golden_set.py` (5) + cible `make eval-gate` : vérifie schéma, domaines, intents, `relevant_doc_ids` existants, OOB vide, doublons, tailles mini — déterministe, sans LLM, exécuté par le job CI `test`. Bloque toute régression du jeu d'éval au merge.
- Reste (T1.4 suite) : gate seuil qualité (Recall@10/nDCG retrieval-live → job avec Qdrant) et seuils RAGAS (coût LLM judge).

> Prochaine : E1 — T1.3 (Langfuse, infra), seuil qualité T1.4. Suite : 44 tests verts.

---

## Session 2026-06-28 — Diagnostic, roadmap, nettoyage & recheck

- Analyse graphify du dépôt (1593 nœuds) + diagnostic architectural complet.
- Rédaction du **plan d'exécution team-ready** → `ROADMAP_RAG.md`.
- **T0.1 ✅** : suppression `storage/mlruns/` (1387 fichiers), `__pycache__/`, `*.pyc`, `.pytest_cache/`, logo doublon ; `htmlcov/` déjà ignoré.
- Suppression de la copie OneDrive redondante (`OneDrive\Desktop\Contexte\Syro`) + du `PLAN_MERGE.md` (merge clos, rien à porter).
- **Recheck roadmap vs code réel** : confirmé golden set = 20 paires, duplication ingestion réelle, 22 services, `agent.py` = persona (pas agentique).
- **Décision** : suite de tests supprimée volontairement → reconstruction **lean** (nouveau ticket **T0.0**) ; DoD + T0.2/T0.3/T1.4 réalignés.

---

## Session 2026-06-27 — Résilience chat (7 changements)

Branche : `fix/chat-500-resilience`
Copie principale : `Desktop\TOUT\Contexte\projets\syro`
Statut : changements **non commités** (dans le working tree).

---

## Résumé des 7 changements

### 1. Fusion hybride → RRF (`app/services/hybrid_search.py`, `app/config.py`)
- Remplace normalisation min-max + pondération `alpha` par **Reciprocal Rank Fusion** :
  `score = Σ 1 / (rrf_k + rang)`, avec `rrf_k = 60` (standard).
- `hybrid_search_alpha` déprécié + ignoré. Fonction `normalize_scores()` supprimée.
- **Pourquoi** : RRF n'utilise que le rang, jamais les scores bruts.
  - Immune aux outliers (un score BM25 extrême n'écrase plus le reste).
  - Plus de problème d'échelles incompatibles (cosinus vs BM25).
- Lève l'archi qui était notée "différée" en mémoire.

### 2. Sécurité prod — refus du secret par défaut (`app/config.py`, `app/main.py`)
- `validate_production_secrets()` : refuse de démarrer si `debug=False` ET
  `secret_key == "dev-secret-change-me"`.
- Appelé dans `lifespan` (boot serveur), **pas à l'import** → pytest/CLI pas cassés.

### 3. Fix CORS credentials (`app/main.py`)
- Wildcard `*` + `allow_credentials=True` = invalide côté navigateur
  (toute requête credentialed rejetée).
- Si `*` présent dans les origines → force `allow_credentials=False` + warning log.

### 4. Simplification config performance (`app/config.py`)
- Profils fast/quality extraits dans la constante `_PERFORMANCE_MODE_CONFIGS`.
- `apply_performance_mode()` réduit à une boucle ; "adaptive" démarre sur "quality".

### 5. GPU detect allégé (`app/services/llm.py`)
- Vire les sondes subprocess `nvidia-smi` + `ollama ps` (coûteuses).
- Garde uniquement un check `torch.cuda` cosmétique pour le log.

### 6. Déduplication retrieve (`app/services/rag.py`)
- `retrieve_chunks_with_metadata()` devient la source unique.
- `retrieve_chunks()` = simple projection texte-seul de la précédente.
- Vire `import numpy` inutile.

### 7. Robustesse reranker (`app/services/reranker.py`)
- Détection scalaire propre (`np.float32` n'est PAS sous-classe de `float`).
- Garde-fou : si nb scores ≠ nb passages → retourne l'ordre d'origine.
- Log warning au lieu d'un `except` muet.

---

## Fichiers touchés (session 2026-06-27, par heure)

| Heure | Fichier |
|---|---|
| 23:05 | `app/services/hybrid_search.py`, `app/config.py` (RRF — dernière édition) |
| 23:06 | `tests/test_hybrid_search.py` |
| 23:01 | `tests/test_chat_endpoint.py`, `requirements.txt`, `requirements-base.txt` |
| 22:27 | `tests/test_config.py` |
| 22:15 | `tests/test_worker_tasks.py` |
| 21:21 | `app/main.py` (CORS + validate secret) |
| 19:34 | `app/security/upload_validator.py` |
| 19:26 | `app/services/reranker.py` |
| 17:59 | `app/services/rag.py` |
| 17:58 | `app/services/llm.py` |

htmlcov régénéré à 23:43 → pytest + coverage lancés après le dernier code.

---

## Todo / état (depuis la mémoire de projet)

- [x] **CORS credentials** — fixé (main.py)
- [x] **RRF** (était différé) — fait (hybrid_search + config)
- [ ] **magic dead + test RED** — `upload_validator.py` touché (−9 lignes), à vérifier
- [ ] **sparse-vectors** — toujours différé, non touché
- [ ] Relancer la suite de tests et confirmer le vert
- [ ] Vérifier 2 fichiers tests (`test_documents_endpoint.py`,
      `test_security_upload_validator.py`) — supprimés puis recréés
