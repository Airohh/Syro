# Syro — Plan d'exécution RAG (team-ready)

> **Nature du document** : plan d'exécution opérationnel, prêt à être pris en main par une équipe (Tech Lead + 2-3 ingénieurs). Contient le diagnostic, l'architecture cible, la gouvernance, les tickets détaillés, le plan de sprints, le chemin critique, le registre des risques et les KPI.
>
> **Sources** : analyse du graphe graphify (1593 nœuds), lecture du code, doc d'architecture interne, best practices RAG 2026 (Pramana, Ultra-RAG, Onyx, WeKnora, NVIDIA RAG Blueprint).
>
> **Dernière mise à jour** : 2026-06-28 · **Statut global** : 🟢 E0 complète · E1 en cours · **E2** T2.1–T2.3 ✅ code

> **Journal de progression**
> - `2026-06-28` — **T2.3 ✅** : `evaluation/tune.py` grid-search `rrf_k` (30/40/60) sur golden set ; `make tune` ; tests `test_tune.py` (4).
> - `2026-06-28` — **T2.2 ✅** : HyDE (`hyde.py`, flag `enable_hyde`, vecteur additionnel dans `hybrid_search`) ; tests `test_hyde.py` (5).
> - `2026-06-28` — **T1.2 ✅** : métriques retrieval déterministes (`evaluation/metrics.py` : Recall@K, nDCG, MRR, Precision@K, refus OOB) testées ; `evaluate.py` sépare retrieval/génération dans `report.json`.
> - `2026-06-28` — **T1.1 🟡** : golden set étendu à 100 paires (4 buckets, `relevant_doc_ids` sur 72), générateur `build_golden_set.py`. Reste relecture DA + annotation des 20 legacy.
> - `2026-06-28` — **Phase 0 (E0) complète** : T0.0–T0.4 tous ✅.
> - `2026-06-28` — **T0.4 ✅** : ADR-001 multi-domaines **Accepted** (Option A). Indirection ports retirée (`domainPorts.ts` → source unique `VITE_API_URL`, `tsc` clean).
> - `2026-06-28` — **T0.3 ✅** : ingestion dédupliquée → `run_ingestion()` + `infer_metadata()` partagés dans `app/services/ingestion.py` ; `worker/tasks.py` et `process_document` délèguent (~80 lignes dupliquées supprimées). Couvert par `tests/test_ingestion_pipeline.py`.
> - `2026-06-28` — **T0.2 ✅ terminé** : bug 500 chat clôturé par non-régression (embedding KO + Qdrant KO → BM25-only ; domain endpoint panne aval → 500 sans fuite + rollback). Diagnostic déjà marqué résolu.
> - `2026-06-28` — **T0.0 ✅ terminé** : suite lean reconstruite (25 tests verts) — `conftest` (gardes GPU/HF offline + stub FlagEmbedding), non-régression RRF + fallback BM25, résilience chat (domain endpoint, pas de fuite/rollback), idempotence ingestion corpus, extraction texte, garde-fous secret prod + CORS wildcard. `pytest*` remis en deps, job CI `test` bloquant, cibles `make test`/`test-cov`. Helper `resolve_cors_settings` extrait pour testabilité.
> - `2026-06-28` — **T0.1 ✅ terminé** : `storage/mlruns/`, `__pycache__/`, `*.pyc`, `.pytest_cache/` supprimés ; `htmlcov/` déjà ignoré ; logo doublon supprimé ; copie OneDrive redondante supprimée.
> - `2026-06-28` — **Décision** : suite de tests historique supprimée volontairement → reconstruction **lean** actée (nouveau ticket **T0.0**) ; DoD et T0.2/T0.3/T1.4 réalignés en conséquence.

---

## Sommaire

1. [Synthèse exécutive](#1-synthèse-exécutive)
2. [Diagnostic de l'existant](#2-diagnostic-de-lexistant)
3. [Comparaison avec l'état de l'art](#3-comparaison-avec-létat-de-lart-2026)
4. [Architecture cible](#4-architecture-cible)
5. [Organisation de l'équipe & RACI](#5-organisation-de-léquipe--raci)
6. [Ways of working](#6-ways-of-working-règles-déquipe)
7. [Epics & roadmap par phases](#7-epics--roadmap-par-phases)
8. [Backlog détaillé (tickets)](#8-backlog-détaillé-tickets)
9. [Plan de sprints](#9-plan-de-sprints)
10. [Chemin critique & dépendances](#10-chemin-critique--dépendances)
11. [Registre des risques](#11-registre-des-risques)
12. [KPI & définition du succès](#12-kpi--définition-du-succès)
13. [Board de suivi](#13-board-de-suivi)

---

## 1. Synthèse exécutive

Syro est un **RAG hybride production-grade** dont le cœur retrieval (chunking hiérarchique + vector/BM25 + RRF k=60 + cross-encoder `bge-reranker-v2-m3`) est **aligné sur l'état de l'art 2026**. Il dépasse la plupart des projets portfolio sur la **gouvernance** (permissions, multi-tenant) et l'**ops** (Prometheus, OTel, circuit breaker, RAGAS).

L'écart avec les références « agentic RAG » n'est pas dans la qualité de l'existant mais dans **trois couches absentes** :
1. **Query understanding** (rewriting / HyDE / expansion) avant le retrieval ;
2. **Orchestration agentique / corrective** (CRAG, Self-RAG, éventuellement GraphRAG) ;
3. **Tracing RAG-spécifique** (Langfuse) et **discipline d'éval à l'échelle** (golden set 100–200).

S'y ajoute une **dette technique ciblée** : duplication ingestion (worker vs service), double stratégie multi-domaines non tranchée, services en dossier plat, SQLite + stockage fichiers local, hygiène repo.

**Stratégie : évolution, pas rewrite.** On stabilise → on mesure → on améliore le retrieval → on ajoute l'agentique guidé par la mesure → on durcit pour la prod.

**Effort total estimé** : ~150 SP (~6 sprints de 2 semaines, équipe de 3). MVP « mesurable + 1 cran de qualité » atteignable en 3 sprints.

---

## 2. Diagnostic de l'existant

Échelle : 🟢 au niveau des meilleurs · 🟡 correct, dette · 🔴 manquant / à risque.

| Axe | État | Constat |
|-----|------|---------|
| Retrieval core (hybrid/RRF/rerank) | 🟢 | Paramètres conformes au standard 2026. RRF immune aux outliers, fallback BM25 si embedding KO. |
| Chunking | 🟢 | Hiérarchique, 400 tok / 60 overlap / respect headers. |
| Gouvernance (permissions, multi-tenant) | 🟢 | `permissions_service`, access/quality levels, isolation par org. |
| Résilience | 🟢 | Circuit breaker, retries, dégradation gracieuse, fallback Celery→BackgroundTasks. |
| Observabilité infra | 🟢 | Prometheus + OpenTelemetry + correlation IDs + logs JSON. |
| Éval | 🟡 | RAGAS + bench latence présents, mais golden set ~20 paires (cible 100–200). |
| Query understanding | 🟡 | Rewriting/HyDE livrés (opt-in, T2.1–T2.2) ; mesure golden set en attente stack. |
| Historique conversationnel | 🟢 | T2.5 ✅ : `load_conversation_history` → retrieval (`history`) + prompt LLM ; flag rewriting réutilisable. |
| Agentic / corrective | 🟡 | T3.1–T3.3 livrés (opt-in) ; T3.4 GraphRAG backlog. |
| Tests | 🟡 | Suite lean **105 tests** (T0.0 ✅). |
| Tracing RAG | 🟡 | T1.3 Langfuse livré (opt-in) ; validation UI avec stack `--profile langfuse`. |
| Ingestion multimodale | 🔴 | Texte seul. `_extract_docx` ignore tableaux/images. |
| Structure code | 🟡 | `app/services/` plat (22 fichiers), 247 micro-communautés = couplage transversal. |
| Duplication ingestion | 🟢 | Résolu (T0.3) : `run_ingestion()` + `infer_metadata()` partagés ; worker et BackgroundTasks délèguent. |
| Modèle multi-domaines | 🟢 | Tranché (T0.4, ADR-001 Accepted) : Option A mono-API ; indirection ports retirée. |
| Couche données | 🟡 | SQLite (OK dev) ; fichiers en disque local ; désync possible SQLite↔Qdrant. |
| Hygiène repo | 🟢 | Nettoyé (2026-06-28) : `mlruns/`, `__pycache__/`, `*.pyc`, `.pytest_cache/` supprimés ; `htmlcov/` ignoré ; copie OneDrive redondante supprimée. |
| Bug 500 chat (historique) | 🟢 | Déjà mitigé : embedding KO → dégradation BM25-only (`hybrid_search.py`). À clôturer formellement. |

---

## 3. Comparaison avec l'état de l'art (2026)

| Capacité | Syro | Références (Pramana, Onyx, NVIDIA, WeKnora, Ultra-RAG) | Verdict |
|----------|------|--------------------------------------------------------|---------|
| Hybrid + RRF + rerank | ✅ | ✅ | À parité |
| Chunking hiérarchique | ✅ | ✅ | À parité |
| Multi-tenant / permissions | ✅ (fort) | partiel | **Au-dessus** |
| Observabilité infra | ✅ | ✅ | À parité |
| Query understanding | ❌ | ✅ | **Retard** |
| Agentique (CRAG/Self-RAG) | ❌ | ✅ | **Retard** |
| Tracing RAG (Langfuse) | ❌ | ✅ | **Retard** |
| Golden set ≥ 100 + éval CI | ❌ (~20) | ✅ | **Retard** |
| Multimodal (tables/images) | ❌ | ✅ | **Retard** |

**Lecture** : la base est solide et même différenciante sur la gouvernance. Les écarts sont concentrés sur les couches « intelligence de requête + mesure + agentique », qui sont précisément le sujet des 3 premières phases.

---

## 4. Architecture cible

```
                    ┌─────────────────────────────────────────────┐
                    │                  FRONTEND                     │
                    │        React + TS (1 base URL + domaine)      │
                    └───────────────────────┬─────────────────────┘
                                            │ REST / SSE
                    ┌───────────────────────▼─────────────────────┐
                    │                  API FastAPI                  │
                    │  auth · chat · documents · agents · mlops     │
                    └───────┬───────────────────────────┬─────────┘
                            │                           │
        ┌───────────────────▼──────────┐   ┌────────────▼─────────────────┐
        │   INGESTION (package)        │   │   RETRIEVAL (package)         │
        │  extract → chunk → index     │   │  query_rewriter · hyde        │
        │  (tables/OCR en Phase 5)     │   │  vector · bm25 · hybrid(RRF)  │
        │  pipeline unique             │   │  rerank · crag · self_rag     │
        └───────┬──────────────────────┘   └────────────┬─────────────────┘
                │ Celery (async)                         │
        ┌───────▼─────────┐   ┌──────────┐   ┌───────────▼──────┐
        │  PostgreSQL     │   │  Qdrant  │   │  CHAT (package)   │
        │  (meta/auth)    │   │ (vecteurs)│  │  build_answer ·   │
        └─────────────────┘   └──────────┘   │  agents · stream  │
        ┌─────────────────┐   ┌──────────┐   └──────────────────┘
        │  Object store    │   │  Redis   │
        │  (MinIO/S3)      │   │ (broker) │   ── Observabilité : Prometheus
        └─────────────────┘   └──────────┘      + OTel + **Langfuse (RAG)**
```

Changements clés vs aujourd'hui : packages métier (Phase 4), PostgreSQL, object store, Langfuse, et les couches query-understanding + agentique insérées dans le package `retrieval`.

---

## 5. Organisation de l'équipe & RACI

**Effectif cible** : 3 ETP + appoint annotation.

| Rôle | Code | Périmètre |
|------|------|-----------|
| Tech Lead / RAG Engineer | **TL** | Architecture, retrieval, agentique, revues, arbitrages |
| Backend Engineer | **BE** | FastAPI, ingestion, DB, refactor packages |
| MLOps / Platform Engineer | **PE** | Éval, Langfuse, CI/CD, infra, observabilité, stockage |
| Frontend Engineer (appoint) | **FE** | UI (affichage métadonnées, sélecteur domaine) |
| Domain Expert / Annotateur (appoint) | **DA** | Labelling golden set, validation réponses |

**RACI par epic** (R=Réalise, A=Approuve, C=Consulté, I=Informé)

| Epic | TL | BE | PE | FE | DA |
|------|----|----|----|----|----|
| E0 Stabilisation | A | R | C | I | — |
| E1 Socle de mesure | A | C | R | I | C/R (labelling) |
| E2 Qualité retrieval | R/A | C | C | I | C |
| E3 Agentique | R/A | C | C | I | C |
| E4 Durcissement prod | A | R | C | I | — |
| E5 Multimodal | A | R | C | I | — |

---

## 6. Ways of working (règles d'équipe)

**Cadence** : sprints de 2 semaines. Cérémonies : planning (J1), daily async, review + démo (J10), rétro.

**Branching** : trunk-based léger. `main` protégée ; branches `feat/<id>-slug`, `fix/<id>-slug`. 1 PR = 1 ticket. Pas de force-push sur `main`.

**Definition of Ready (DoR)** — un ticket est prenable si :
- objectif + critères d'acceptation clairs ;
- dépendances résolues ou identifiées ;
- estimation posée ; feature-flag prévu si comportement runtime modifié.

**Definition of Done (DoD)** — globale, s'applique à TOUT ticket :
- code + tests de la **suite lean** (smoke + non-régression) verts en CI ;
- lint/format OK (`make lint`, `make format`) ;
- pas de secret commité ; feature-flag par défaut sûr ;
- doc à jour (README/ADR/CHANGEMENTS) ;
- revue par ≥ 1 pair (TL pour les changements d'archi) ;
- **toute amélioration retrieval/agentique fournit le delta mesuré sur le golden set** (sinon non mergée).

> **Note état actuel (2026-06-28)** : la suite de tests historique a été **supprimée volontairement**. La stratégie retenue est une **suite lean reconstruite** (ticket **T0.0**) : smoke test + non-régression ciblée sur retrieval/ingestion, pas un re-portage des ~32 fichiers de tests. Tant que T0.0 n'est pas livré, le critère « tests verts » de la DoD est suspendu et remplacé par `scripts/smoke_test.py` + lint.

**Revue de code** : bloquante pour archi/sécurité ; non-bloquante pour nits de style.

**Tests** : approche lean — chaque nouveau service critique (retrieval/ingestion) a un test ciblé ; toute correction de bug ajoute un test de non-régression. Pas d'objectif de couverture chiffré tant que la suite est en reconstruction.

---

## 7. Epics & roadmap par phases

```
Phase 0  E0 Stabiliser & assainir       (~1 sem)    prérequis propreté
Phase 1  E1 Socle de mesure             (~1-2 sem)  DÉBLOQUE tout le reste
Phase 2  E2 Qualité retrieval           (~2 sem)    ROI le plus direct
Phase 3  E3 Agentique (guidé mesure)    (~2-3 sem)  différenciation
Phase 4  E4 Durcissement prod           (~2-3 sem)  scalabilité
Phase 5  E5 Multimodal                  (~1-2 sem)  extension
```

Principe directeur 2026 : *« fix chunking → hybrid → reranker → eval set »* puis *« n'ajoute l'agentique que quand l'éval montre que le pipeline simple échoue »*. Syro a fait les 3 premiers ; **la prochaine marche est l'eval set**, ensuite tout est piloté par la mesure.

| Epic | Tickets | SP | Sprint cible |
|------|---------|----|----|
| E0 Stabilisation | T0.0–T0.4 | 16 | S1 |
| E1 Socle de mesure | T1.1–T1.4 | 21 | S1-S2 |
| E2 Qualité retrieval | T2.1–T2.5 | 21 | S3-S4 |
| E3 Agentique | T3.1–T3.4 | 31 | S4-S5 |
| E4 Durcissement prod | T4.1–T4.5 | 42 | S6+ |
| E5 Multimodal | T5.1–T5.2 | 13 | S6+ |

---

## 8. Backlog détaillé (tickets)

> Format : **priorité** (P0 critique → P3 nice-to-have) · **type** · **SP** · **sprint** · **owner (R)** · **dépendances**. La DoD globale (§6) s'applique en plus des critères d'acceptation.

### EPIC E0 — Stabiliser & assainir

#### T0.0 — Reconstruire une suite de tests lean
- **P0 · Story · 5 SP · S1 · BE · dépend : —** · Statut : ✅ **FAIT (2026-06-28)** — 25 tests verts ; couvre RRF, fallback BM25, résilience chat (domain endpoint + pas de fuite/rollback), idempotence ingestion, extraction, secret prod + CORS wildcard. `pytest*` deps, job CI `test` bloquant, cibles `make test`/`test-cov`.
- **Pourquoi** : la suite historique (~32 fichiers) a été supprimée volontairement ; la CI est réduite à lint. On veut un filet de sécurité **minimal et ciblé** (pas un re-portage), sur lequel s'appuieront T0.2, T0.3 et le gate T1.4.
- **Périmètre (ce qu'on teste)** :
  1. `scripts/smoke_test.py` opérationnel (API + Qdrant + Redis + MLflow up) en cible `make smoke`.
  2. Non-régression **retrieval** : RRF (fusion par rang), fallback BM25-only si embedding KO.
  3. Non-régression **ingestion** : `extract_text_from_bytes` (formats clés) + le futur `run_ingestion` (T0.3).
  4. Garde-fous **config/sécurité** : `validate_production_secrets`, CORS wildcard→credentials off.
- **Ce qu'on ne fait pas** : re-créer les ~32 fichiers ni viser un % de couverture. Tests rapides, sans téléchargement de modèle (réutiliser le garde-fou HF déjà en place).
- **Étapes** : recréer `Syro/tests/` minimal + `conftest.py` ; remettre `pytest*` dans `requirements.txt` (section dev) ; réintroduire un job `test` léger dans `ci.yml` ; remettre les cibles `make test`/`test-cov`.
- **Fichiers** : `Syro/tests/**` (nouveau, lean), `requirements.txt`, `.github/workflows/ci.yml`, `Syro/Makefile`.
- **Acceptation** : `make test` vert en local et en CI ; couvre RRF, fallback BM25, extraction, secrets/CORS.

#### T0.1 — Assainir le repo (artefacts générés + doublons)
- **P0 · Tâche · 1 SP · S1 · PE · dépend : —** · Statut : ✅ **FAIT (2026-06-28)**
- **Pourquoi** : artefacts générés (couverture HTML, runs MLflow) + doublons polluent git, le graphe et les reviews.
- **Étapes** :
  1. ✅ Supprimer sur disque `storage/mlruns/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`.
  2. ✅ `Syro/htmlcov/` déjà présent dans `.gitignore` (mlruns couvert par `Syro*/storage/*`).
  3. ✅ Suppression du logo doublon `Syro/assets/image/logo.png` (staged). *(reste : retirer le dossier coquille vide `assets/image/`)*.
  4. ⬜ (optionnel) Régénérer la couverture en CI comme artefact non versionné — rattaché à T0.0.
- **Fichiers** : `.gitignore`, `Syro/assets/`.
- **Acceptation** : ✅ `git status` ne liste plus d'artefacts ; `graphify` ne les voit plus.

#### T0.2 — Clôturer le bug 500 chat (non-régression)
- **P1 · Tâche · 3 SP · S1 · BE · dépend : T0.0** · Statut : ✅ **FAIT (2026-06-28)** — tests : embedding KO → BM25-only, Qdrant KO (`VectorStoreError`) → BM25-only, domain endpoint panne aval → 500 sans fuite + rollback. Diagnostic marqué résolu (`docs/diagnostic-chat-500.md`).
- **Pourquoi** : le code dégrade déjà en BM25-only (`hybrid_search.py`) avec handler `VectorStoreError`→503 (`main.py`) ; il manque le test qui fige ce comportement.
- **Étapes** :
  1. Test : Qdrant indisponible → `/chat/message` renvoie une réponse BM25-only, pas 500.
  2. Test : embedding provider en exception → même résultat.
  3. Marquer le diagnostic résolu (`docs/diagnostic-chat-500.md`).
- **Fichiers** : nouveaux tests lean (chat + hybrid_search) issus de T0.0, `docs/diagnostic-chat-500.md`.
- **Acceptation** : tests verts avec Qdrant/embedding simulés KO ; aucun 500.

#### T0.3 — Fusionner l'ingestion dupliquée
- **P1 · Story · 5 SP · S1 · BE · dépend : T0.0** · Statut : ✅ **FAIT (2026-06-28)** — `run_ingestion()` + `infer_metadata()` centralisés dans `app/services/ingestion.py` ; `worker/tasks.py` (metrics/retry) et `process_document` (BackgroundTasks) délèguent. ~80 lignes dupliquées supprimées, edge `doc_row` manquant unifié (raise). Tests : `test_ingestion_pipeline.py`.
- **Pourquoi** : `worker/tasks.py` et `ingestion.process_document` partagent la même séquence (`extract_text_from_bytes` + `index_document_content`, vérifié L65/124 vs L77/133) → risque de drift.
- **Étapes** :
  1. Créer `app/services/ingestion/pipeline.py` avec `run_ingestion(document_id, org_id, storage_path, mime, domain)` (extraction → métadonnées → `index_document_content` → maj statut).
  2. `worker/tasks.py` : wrapper fin (métriques + retry) appelant `run_ingestion`.
  3. `ingestion.process_document` : wrapper `BackgroundTasks` appelant `run_ingestion`.
  4. Centraliser l'inférence métadonnées dans `infer_metadata(filename, tags, domain)` testable.
- **Fichiers** : `app/services/ingestion/pipeline.py` (nouveau), `worker/tasks.py`, `app/services/ingestion.py`, tests lean (T0.0).
- **Acceptation** : tests ingestion/worker lean verts sans duplication ; `run_ingestion` couvert par un test.

#### T0.4 — Trancher le modèle multi-domaines (ADR)
- **P1 · Décision · 2 SP · S1 · TL · dépend : —** · Statut : ✅ **FAIT (2026-06-28)** — ADR-001 **Accepted** (Option A : mono-API + filtres Qdrant par domaine). Indirection ports retirée : `domainPorts.ts` réduit à une source unique pilotée par `VITE_API_URL` (`tsc` clean).
- **Pourquoi** : Docker = 1 API (`DOMAIN=general`), frontend = N ports (`domainPorts.ts`) ; incohérence produit.
- **Étapes** :
  1. Rédiger `CHANGEMENTS/ADR-001-multidomaine.md` (contexte, options, décision, conséquences).
  2. Reco **Option A** : 1 API, collections/filtres Qdrant par domaine, frontend sur 1 base URL + header `domain`.
  3. Lister les changements induits (sortir `domainPorts` du chemin critique ou le réserver au déploiement avancé).
- **Fichiers** : `CHANGEMENTS/ADR-001-multidomaine.md`.
- **Acceptation** : ADR validé par TL ; les tickets E4 s'y réfèrent.

### EPIC E1 — Socle de mesure

#### T1.1 — Étendre le golden set à 100–200 paires
- **P0 · Story · 8 SP · S1-S2 · DA + PE · dépend : —** · Statut : 🟡 **Première passe livrée (2026-06-28)** — `eval_dataset.json` à **100 paires**, 4 buckets (`factual_lookup` 36, `exact_identifier` 28, `multi_hop` 8, `out_of_corpus` 8 ; + 20 legacy à annoter), `relevant_doc_ids` sur 72/100. Générateur reproductible `evaluation/build_golden_set.py`. **Reste** : relecture DA (R1), annoter les 20 paires legacy, viser ~150.
- **Pourquoi** : prérequis de **toute** mesure d'amélioration. Standard 2026 = 100–200.
- **Étapes** :
  1. Couvrir les buckets d'intention : lookup factuel, multi-hop, identifiants exacts (codes/SKU), hors-corpus (doit refuser).
  2. Par paire : `question`, `ground_truth`, `relevant_doc_ids`, `domain`, `intent`.
  3. Étendre `evaluation/eval_dataset.json` ; documenter le process d'ajout.
- **Fichiers** : `Syro/evaluation/eval_dataset.json`, `Syro/evaluation/corpus/README.md`.
- **Acceptation** : ≥ 100 paires, ≥ 4 buckets, `relevant_doc_ids` renseignés.

#### T1.2 — Séparer éval retrieval vs génération
- **P0 · Story · 5 SP · S2 · PE · dépend : T1.1** · Statut : ✅ **FAIT (2026-06-28)** — `evaluation/metrics.py` (Recall@K, Precision@K, nDCG@K, MRR, hit@K + `oob_refusal_rate`, déterministe) couvert par `tests/test_eval_metrics.py` ; `evaluate.py` mappe chunks→`documents.filename` via `relevant_doc_ids` et écrit `report.json` séparant `retrieval_metrics` (déterministe) et `generation_metrics` (RAGAS). *(Scores réels = run avec stack, comme RAGAS.)*
- **Pourquoi** : si faithfulness baisse, c'est presque toujours le retrieval ; il faut le distinguer.
- **Étapes** :
  1. Ajouter `Recall@K`, `nDCG@K`, `Coverage` (retrieval) via `relevant_doc_ids`.
  2. Garder RAGAS (faithfulness, answer relevance, context precision/recall) pour la génération.
  3. Sortie `evaluation/report.json` avec les deux familles.
- **Fichiers** : `Syro/evaluation/evaluate.py`, `Syro/evaluation/metrics.py` (nouveau).
- **Acceptation** : rapport séparant retrieval-metrics et generation-metrics.

#### T1.3 — Intégrer Langfuse (tracing RAG)
- **P1 · Story · 5 SP · S2 · PE · dépend : —** · Statut : ✅ **Code livré (2026-06-28)** — `LANGFUSE_ENABLED=false` par défaut. **Reste** : valider trace complète dans UI Langfuse avec stack live.
- **Pourquoi** : MLflow ne montre pas le détail par requête ; Langfuse est le standard 2026.
- **Livré** : `langfuse_tracer.py` (no-op si off) ; spans retrieval + generation dans `build_answer` ; `docker-compose.langfuse.yml` (profil optionnel) ; `langfuse` dans requirements.
- **Fichiers** : `app/services/langfuse_tracer.py`, `chat.py`, `config.py`, `infra/docker-compose.langfuse.yml`.
- **Acceptation** : ✅ tests `test_langfuse_tracer.py` (4) ; trace UI = stack + clés Langfuse.

#### T1.4 — Éval en CI (gate sur seuils)
- **P1 · Tâche · 3 SP · S3 · PE · dépend : T0.0, T1.1, T1.2** · Statut : ✅ **Gates livrés (2026-06-28)** — intégrité golden set (CI) + seuils retrieval (`validate_retrieval_thresholds.py`, `make eval-retrieval-gate`). **Reste** : job nightly avec stack live ; seuils RAGAS (coût LLM judge).
- **Pourquoi** : « eval as continuous engineering » — bloquer les régressions au merge.
- **Étapes** :
  1. Job CI sur un sous-ensemble rapide.
  2. Seuils configurables : faithfulness ≥ 0.9, answer relevance ≥ 0.85, context precision ≥ 0.8, Recall@10 baseline.
  3. Échec CI sous le seuil ; rapport en artefact.
- **Fichiers** : `.github/workflows/ci.yml`, `evaluation/evaluate.py`.
- **Acceptation** : PR sous le seuil → CI rouge avec le détail.

### EPIC E2 — Qualité retrieval

#### T2.1 — Query rewriting / expansion
- **P1 · Story · 5 SP · S3 · TL · dépend : T1.2** · Statut : ✅ **Code livré (2026-06-28)** — flag `ENABLE_QUERY_REWRITING=false` par défaut. **Reste** : run `evaluate.py` avec/sans flag pour prouver le delta Recall@10 sur golden set (stack live).
- **Pourquoi** : étape standard 2026 manquante ; gain de recall sur questions mal formulées.
- **Livré** :
  1. `app/services/query_rewriter.py` : `rewrite(query, history) -> list[str]` (originale + 1–2 reformulations LLM, dédupliquées).
  2. `hybrid_search.py` : retrieval sur chaque variante, fusion RRF globale ; param `history` optionnel ; batch `get_embedding_vectors`.
  3. `config.py` : `enable_query_rewriting`, `query_rewrite_max_variants`.
  4. Tests : `tests/test_query_rewriter.py` (6), `test_hybrid_search.test_query_rewriting_merges_variants_via_rrf`.
- **Fichiers** : `app/services/query_rewriter.py`, `hybrid_search.py`, `config.py`.
- **Acceptation** : ✅ code + tests ; delta Recall@10 mesuré = run evaluate avec stack.

#### T2.2 — HyDE
- **P2 · Story · 3 SP · S4 · TL · dépend : T2.1** · Statut : ✅ **Code livré (2026-06-28)** — `ENABLE_HYDE=false` par défaut. **Reste** : delta nDCG@10 mesuré sur golden set (stack live).
- **Pourquoi** : efficace sur questions courtes/abstraites.
- **Livré** : `hyde.py` (`generate_hypothetical_passage`, `get_hyde_embedding_vector`) ; vecteur HyDE fusionné via RRF dans `hybrid_search` ; tests `test_hyde.py` (5).
- **Fichiers** : `app/services/hyde.py`, `hybrid_search.py`, `config.py`.
- **Acceptation** : ✅ code + tests ; delta nDCG@10 = run evaluate/tune avec stack.

#### T2.3 — Tuning RRF k
- **P2 · Tâche · 3 SP · S3 · PE · dépend : T1.2** · Statut : ✅ **Code livré (2026-06-28)** — α déprécié, seul `rrf_k` est tuné.
- **Pourquoi** : l'optimum de `rrf_k` (30–60) dépend du corpus ; impact top-1 vs recall.
- **Livré** : `evaluation/tune.py` (grid-search, `tune_report.json`) ; `make tune` ; tests `test_tune.py` (4).
- **Fichiers** : `evaluation/tune.py`, `Makefile`.
- **Acceptation** : ✅ script + tests ; valeur gagnante = `make tune` avec stack + corpus ingéré.

#### T2.4 — Metadata filtering avant ANN
- **P1 · Story · 5 SP · S4 · BE · dépend : —** · Statut : ✅ **Code livré (2026-06-28)**
- **Pourquoi** : éviter de reranker des chunks hors-scope ; précision + sécurité.
- **Livré** : `retrieval_filters.py` (`build_retrieval_scope`, permissions via `filter_documents_by_permissions`) ; Qdrant `MatchAny` sur `document_id` ; BM25 filtre **avant** scoring (domain + droits) ; `chat` passe `user_id` → scope ; eval `user_id=None` = pas de filtre permissions.
- **Fichiers** : `retrieval_filters.py`, `vector_store.py`, `bm25_search.py`, `hybrid_search.py`, `chat.py`, `routers/chat.py`, `rag.py`, `multi_domain_rag.py`.
- **Acceptation** : ✅ tests `test_retrieval_filters.py` (7) ; isolation live = stack + corpus multi-user.

#### T2.5 — Historique conversationnel dans le RAG
- **P1 · Story · 5 SP · S4 · TL · dépend : T1.2, T2.1** · Statut : ✅ **Code livré (2026-06-28)**
- **Pourquoi** : questions de suivi retrievent mal sans contexte des tours précédents.
- **Livré** : `load_conversation_history` (6 tours) ; router charge l'historique **avant** le message courant ; `history` passé au rewriting/hybrid search ; bloc « Historique récent » dans le prompt LLM (`llm.py`).
- **Fichiers** : `app/services/chat.py`, `routers/chat.py`, `app/services/llm.py`, `hybrid_search.py`.
- **Acceptation** : ✅ tests `test_conversation_history.py` ; delta follow-up golden set = run evaluate quand stack dispo.

### EPIC E3 — Agentique (piloté par la mesure)

#### T3.1 — CRAG (corrective retrieval)
- **P1 · Story · 5 SP · S4 · TL · dépend : T1.3, T2.1** · Statut : ✅ **Code livré (2026-06-28)** — `ENABLE_CRAG=false` par défaut. **Reste** : trace Langfuse (T1.3) + delta faithfulness sur golden set.
- **Pourquoi** : premier pas agentique simple, fort impact faithfulness.
- **Livré** : `crag.py` — évaluateur léger (overlap lexical + force RRF) ; si verdict incorrect/ambiguous → retry avec `top_k×2` + `expand_queries(force=True)` ; fusion si retry partiel ; branché dans `rag.py` via `enable_crag`.
- **Fichiers** : `app/services/crag.py`, `rag.py`, `hybrid_search.py` (`queries` override), `query_rewriter.py` (`force`), `config.py`.
- **Acceptation** : ✅ tests `test_crag.py` (10) ; faithfulness mesurée = run evaluate avec stack.

#### T3.2 — Self-RAG (filtrage par chunk)
- **P2 · Story · 5 SP · S5 · TL · dépend : T3.1** · Statut : ✅ **Code livré (2026-06-28)** — `ENABLE_SELF_RAG=false` par défaut.
- **Pourquoi** : réduit le bruit dans le prompt → moins d'hallucination.
- **Livré** : `self_rag.py` — score IsRel heuristique (overlap + retrieval) ; drop sous seuil ; garde 3–8 chunks ; metadata `self_rag_relevance` ; branché dans `build_answer`/`build_answer_stream` via `_filter_chunk_results`.
- **Fichiers** : `app/services/self_rag.py`, `chat.py`, `config.py`.
- **Acceptation** : ✅ tests `test_self_rag.py` (7) ; context precision mesurée = run evaluate avec stack.

#### T3.3 — Query decomposition multi-hop
- **P2 · Story · 8 SP · S5 · TL · dépend : T2.1** · Statut : ✅ **Code livré (2026-06-28)** — `ENABLE_QUERY_DECOMPOSITION=false` par défaut.
- **Pourquoi** : questions composées mal servies par un seul retrieval.
- **Livré** : `decompose.py` — heuristiques (`?` multiples, `;`) + fallback LLM ; retrieval parallèle par sous-requête ; fusion RRF globale + rerank ; branché dans `rag.py` (prioritaire sur CRAG si activé).
- **Fichiers** : `app/services/decompose.py`, `rag.py`, `config.py`.
- **Acceptation** : ✅ tests `test_decompose.py` (7) ; gain bucket multi-hop = run evaluate avec stack.

#### T3.4 — (Optionnel) GraphRAG
- **P3 · Spike/Story · 13 SP · backlog · TL · dépend : T3.3**
- **Pourquoi** : seulement si l'éval montre que le multi-hop simple échoue.
- **Étapes** : extraction entités/relations à l'ingestion ; stockage graphe + résumés de communautés ; mode `kg_global`/`kg_local`.
- **Fichiers** : nouveau sous-système `app/services/graph/`.
- **Acceptation** : gain mesuré sur questions globales, sinon **non mergé**.

### EPIC E4 — Durcissement prod

#### T4.1 — Refactor services en packages
- **P2 · Story · 13 SP · S6 · BE · dépend : T0.3**
- **Pourquoi** : 247 micro-communautés = couplage transversal ; lisibilité + testabilité.
- **Étapes** : regrouper `ingestion/`, `retrieval/`, `chat/`, `platform/` ; migration par lots avec imports rétro-compat temporaires ; `graphify update .` pour vérifier.
- **Fichiers** : `app/services/**`.
- **Acceptation** : tests verts, imports nettoyés, graphe plus lisible.

#### T4.2 — SQLite → PostgreSQL
- **P2 · Story · 13 SP · backlog · BE · dépend : T4.1**
- **Pourquoi** : SQLite limite la concurrence API+worker ; `postgres` déjà dans le compose.
- **Étapes** : couche d'accès compatible PG ; migrations Alembic ; bascule config + tests d'intégration PG.
- **Fichiers** : `app/db.py`, `db/`, `scripts/init_db.py`, config.
- **Acceptation** : suite verte sur PostgreSQL ; charge worker concurrente OK.

#### T4.3 — Stockage objet (MinIO/S3)
- **P2 · Story · 5 SP · S6 · PE · dépend : —**
- **Pourquoi** : prod multi-nœuds, durabilité.
- **Étapes** : abstraction `storage` (local | S3/MinIO) ; `documents.upload_*` via l'abstraction ; chemins en DB.
- **Fichiers** : `app/services/storage.py` (nouveau), `routers/documents.py`, `worker/tasks.py`.
- **Acceptation** : upload/lecture OK sur MinIO local.

#### T4.4 — Cohérence DB ↔ Qdrant
- **P2 · Story · 8 SP · backlog · BE · dépend : T4.2**
- **Pourquoi** : un échec Qdrant laisse la DB en avance (logué dans `rag.py`).
- **Étapes** : pattern outbox (état d'indexation) + tâche de réconciliation ; job de ré-indexation des orphelins.
- **Fichiers** : `rag.py`, `worker/tasks.py`, schéma.
- **Acceptation** : panne Qdrant simulée → réconciliation automatique au retour.

#### T4.5 — Cache sémantique des requêtes
- **P3 · Story · 3 SP · backlog · PE · dépend : T1.3** · Statut : ✅ **Code livré (2026-06-28)** — `ENABLE_SEMANTIC_CACHE=false` par défaut.
- **Livré** : `semantic_cache.py` (in-process, cosine ≥ 0.95) ; lookup/store dans `rag.py` ; invalidation domaine à l'ingestion.
- **Acceptation** : ✅ tests `test_semantic_cache.py` (6).

### EPIC E5 — Multimodal

#### T5.1 — Extraction tableaux (DOCX/PDF)
- **P2 · Story · 5 SP · S6 · BE · dépend : T0.3**
- **Pourquoi** : beaucoup d'info en tableaux, aujourd'hui perdue.
- **Étapes** : DOCX `doc.tables` + paragraphs ; PDF → markdown ; chunking conscient des tableaux.
- **Fichiers** : `app/services/file_extractor.py`, `chunker.py`.
- **Acceptation** : un DOCX/PDF avec tableau produit des chunks contenant les cellules.

#### T5.2 — Images-with-text (OCR)
- **P3 · Story · 8 SP · backlog · BE · dépend : T5.1**
- **Pourquoi** : couverture documentaire complète.
- **Étapes** : détecter images DOCX/PDF ; OCR (Tesseract/service) → texte indexé avec provenance.
- **Fichiers** : `file_extractor.py`, dépendances OCR.
- **Acceptation** : une image-texte produit des chunks recherchables.

---

## 9. Plan de sprints

Hypothèse : équipe 3 ETP, vélocité ~22 SP/sprint, sprints de 2 semaines.

| Sprint | Objectif (outcome) | Tickets | SP |
|--------|--------------------|---------|----|
| **S1** | Filet de sécurité (tests lean) + repo propre + ingestion saine + démarrage mesure | T0.0, ✅T0.1, T0.2, T0.3, T0.4, T1.1 (début) | ~19 |
| **S2** | Mesure opérationnelle (retrieval/génération séparés + tracing) | T1.1 (fin), T1.2, T1.3 | ~18 |
| **S3** | Éval en CI + premiers gains retrieval | T1.4, T2.1, T2.3 | ~11 |
| **S4** | Retrieval avancé + conversationnel + 1er cran agentique | T2.2, T2.4, T2.5, T3.1 | ~18 |
| **S5** | Agentique complète | T3.2, T3.3 | ~13 |
| **S6** | Durcissement + multimodal v1 | T4.1, T4.3, T5.1 | ~23 |
| **Backlog** | Selon mesure / priorités | T3.4, T4.2, T4.4, T4.5, T5.2 | ~45 |

**Jalons (milestones)** :
- **M1 (fin S2)** — « Mesurable » : tout changement futur est prouvable sur le golden set. ✅ débloque E2/E3.
- **M2 (fin S4)** — « Qualité retrieval +1 cran » : query understanding + CRAG actifs, gains mesurés.
- **M3 (fin S6)** — « Prod-ready v1 » : packages, stockage objet, multimodal v1.

---

## 10. Chemin critique & dépendances

```
✅T0.1
T0.0 ─► T0.2
   └──► T0.3 ─► (T4.1 ─► T4.2 ─► T4.4)
T0.4         └─► T5.1 ─► T5.2
        T1.1 ─► T1.2 ─► T1.4 ◄── T0.0
        T1.3 ─────────────┐
        T2.3 ◄── T1.2     ├─► T2.1 ─► T2.2
        T2.4              │
                          └─► T3.1 ─► T3.2 ─► T3.3 ─► (T3.4 si mesuré utile)
                          T4.3 (indépendant)
```

**Chemin critique** : `T0.0 → (T0.2/T0.3) ` en parallèle de `T1.1 → T1.2 → T2.1 → T3.1 → T3.2/T3.3`. T0.0 (tests lean) débloque T0.2/T0.3/T1.4 ; tout retard sur le golden set (T1.1) décale la chaîne qualité/agentique.

**Règle d'or** : ne jamais merger une amélioration retrieval/agentique (E2-E3) sans le delta mesuré sur le golden set (E1).

---

## 11. Registre des risques

| # | Risque | Prob. | Impact | Mitigation | Owner |
|---|--------|-------|--------|------------|-------|
| R1 | Golden set trop petit/biaisé → mesures non fiables | M | Élevé | ≥ 100 paires, buckets d'intention, revue DA | DA/PE |
| R2 | Coût/latence LLM des couches agentiques (CRAG/Self-RAG/HyDE) | M | Moyen | feature-flags, budgets latence p95, A/B mesuré | TL |
| R3 | Drift entre worker et service d'ingestion pendant le refactor | M | Moyen | T0.3 d'abord (pipeline unique), tests de non-régression | BE |
| R4 | Migration PostgreSQL casse la concurrence/tests | F | Élevé | Alembic + tests d'intégration PG, bascule feature-flag | BE |
| R5 | Désync DB ↔ Qdrant en prod | M | Élevé | T4.4 outbox + réconciliation | BE |
| R6 | Sur-ingénierie (GraphRAG « par mode ») sans gain | M | Moyen | T3.4 conditionné à la mesure, sinon non mergé | TL |
| R7 | Indécision multi-domaines bloque E4 | F | Moyen | ADR T0.4 en S1 | TL |
| R8 | Secrets/CORS en prod | F | Élevé | garde déjà en place (`validate_production_secrets`) ; couvert par tests lean (T0.0) | PE |
| R9 | Filet de tests absent (suite supprimée) → régressions silencieuses avant T0.0 | M | Élevé | prioriser T0.0 en S1 ; `make smoke` + lint en attendant | BE |

---

## 12. KPI & définition du succès

| Métrique | Cible 2026 | Mesure |
|----------|-----------|--------|
| Faithfulness | ≥ 0.90 | RAGAS |
| Answer relevancy | ≥ 0.85 | RAGAS |
| Context precision | ≥ 0.80 | RAGAS |
| Context recall | ≥ 0.80 | RAGAS |
| Recall@10 | baseline + amélioration mesurée | golden set hand-labeled |
| nDCG@10 | maximisé par tuning (T2.3) | golden set |
| Latence e2e p95 | sous budget défini | `benchmark.py` |
| Suite de tests lean | verte en CI | `make test` (après T0.0) |
| Régressions qualité au merge | 0 (gate CI) | T1.4 |

---

## 13. Board de suivi

Légende : ⬜ à faire · 🟡 en cours · ✅ fait · ⛔ bloqué

| ID | Titre | Epic | SP | Sprint | Owner | Statut |
|----|-------|------|----|--------|-------|--------|
| T0.0 | Suite de tests lean | E0 | 5 | S1 | BE | ✅ |
| T0.1 | Assainir le repo | E0 | 1 | S1 | PE | ✅ |
| T0.2 | Clôturer bug 500 chat | E0 | 3 | S1 | BE | ✅ |
| T0.3 | Fusionner ingestion | E0 | 5 | S1 | BE | ✅ |
| T0.4 | ADR multi-domaines | E0 | 2 | S1 | TL | ✅ |
| T1.1 | Golden set 100–200 | E1 | 8 | S1-S2 | DA/PE | 🟡 |
| T1.2 | Éval retrieval vs génération | E1 | 5 | S2 | PE | ✅ |
| T1.3 | Langfuse | E1 | 5 | S2 | PE | ✅ |
| T1.4 | Éval en CI | E1 | 3 | S3 | PE | ✅ |
| T2.1 | Query rewriting | E2 | 5 | S3 | TL | ✅ |
| T2.2 | HyDE | E2 | 3 | S4 | TL | ✅ |
| T2.3 | Tuning rrf_k | E2 | 3 | S3 | PE | ✅ |
| T2.4 | Metadata filtering | E2 | 5 | S4 | BE | ✅ |
| T2.5 | Historique conversationnel | E2 | 5 | S4 | TL | ✅ |
| T3.1 | CRAG | E3 | 5 | S4 | TL | ✅ |
| T3.2 | Self-RAG | E3 | 5 | S5 | TL | ✅ |
| T3.3 | Query decomposition | E3 | 8 | S5 | TL | ✅ |
| T3.4 | GraphRAG (opt.) | E3 | 13 | backlog | TL | ⬜ |
| T4.1 | Refactor packages | E4 | 13 | S6 | BE | ⬜ |
| T4.2 | PostgreSQL | E4 | 13 | backlog | BE | ⬜ |
| T4.3 | Stockage objet | E4 | 5 | S6 | PE | ⬜ |
| T4.4 | Cohérence DB↔Qdrant | E4 | 8 | backlog | BE | ⬜ |
| T4.5 | Cache sémantique | E4 | 3 | backlog | PE | ✅ |
| T5.1 | Extraction tableaux | E5 | 5 | S6 | BE | ⬜ |
| T5.2 | OCR images | E5 | 8 | backlog | BE | ⬜ |

**Total** : 25 tickets · ~163 SP · **17 tickets code ✅** (E0, E2, E3, T1.2–T1.4, T3.1–T3.3) · T1.1 🟡 (revue DA) · E4/E5 + T3.4 backlog.
