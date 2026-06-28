# Syro — Changements & pilotage

> **Documents de ce dossier**
> - **`ROADMAP_RAG.md`** — 📌 **Plan d'exécution team-ready** (diagnostic, archi cible, RACI, ways of working, 25 tickets, plan de sprints, chemin critique, risques, KPI, board de suivi). Document de référence pour piloter le travail.
> - `CHANGEMENTS.md` (ce fichier) — journal des changements de code par session.
> - `ADR-001-multidomaine.md` — *(à créer, ticket T0.4)* décision d'architecture multi-domaines.

---

## Session 2026-06-28 (PM) — Code review, fixes résilience & suite lean (T0.0 ✅, T0.2 ✅)

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

> Restant Phase 0 : **T0.3** (fusion ingestion dupliquée), **T0.4** (ADR multi-domaines, reco Option A).

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
