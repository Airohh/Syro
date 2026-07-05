# Architecture Syro — état actuel

> **Statut** : description de l'état réel du code (pas un backlog).
> Plan d'exécution vivant : **[`CHANGEMENTS/ROADMAP_RAG.md`](../CHANGEMENTS/ROADMAP_RAG.md)**

---

## Vue d'ensemble

Syro est un RAG hybride multi-domaines : FastAPI + Qdrant (dense) + BM25
(sparse), fusion RRF, reranking cross-encoder, ingestion async Celery,
observabilité Prometheus/OpenTelemetry/Langfuse (opt-in), éval RAGAS + golden set 100 paires.

```
Question
   │
   ▼
┌──────────────────┐   mots-clés (domain_detector.py) ou route /domains/{domain}/chat
│  Domain routing  │   ADR-001 : mono-API, 1 base URL (VITE_API_URL)
└────────┬─────────┘
         │
   ┌─────┴──────────────────────────────────────┐
   │  Query understanding (opt-in, flags)      │
   │  rewriting · HyDE · décomposition · CRAG   │
   └────────┬─────────────────────────────────┘
         │
   ┌─────┴─────┐  recherche parallèle
   ▼           ▼
┌──────┐   ┌──────┐
│Vector│   │ BM25 │   embedding KO → dégradation BM25-only
│Qdrant│   │      │
└──┬───┘   └──┬───┘
   └────┬─────┘
        ▼
┌───────────────┐   Reciprocal Rank Fusion (rrf_k=60)
│  RRF fusion   │   hybrid_search_alpha déprécié (ignoré)
└───────┬───────┘
        ▼
┌───────────────┐   bge-reranker-v2-m3 (opt-in via enable_reranking)
│  Cross-encoder│
└───────┬───────┘
        ▼
┌───────────────┐   Self-RAG filter (opt-in) + historique conversation (T2.5)
│  LLM answer   │   cache sémantique retrieval (opt-in, T4.5)
└───────────────┘
```

## État par capacité

Échelle : 🟢 au niveau de l'état de l'art · 🟡 fait avec dette · 🔴 absent.

| Capacité | État | Où / Note |
|----------|------|-----------|
| Détection de domaine | 🟢 | `domain_detector.py` — mots-clés (pas de modèle ML) |
| Recherche multi-domaines | 🟢 | `multi_domain_rag.py`, `chat.py` |
| Fusion résultats | 🟢 | RRF dans `hybrid_search.py` |
| Reranking | 🟢 | `bge-reranker-v2-m3`, blend RRF × `rerank_weight` |
| Query rewriting | 🟡 | `query_rewriter.py` — **off par défaut** (`enable_query_rewriting`) |
| HyDE | 🟡 | `hyde.py` — **off par défaut** |
| CRAG / Self-RAG / décomposition | 🟡 | `crag.py`, `self_rag.py`, `decompose.py` — **off par défaut** |
| Historique conversationnel | 🟢 | `load_conversation_history` → retrieval + prompt LLM (T2.5) |
| Cache sémantique retrieval | 🟡 | `semantic_cache.py` — **off par défaut** |
| Tracing RAG (Langfuse) | 🟡 | `langfuse_tracer.py` — **off par défaut**, profil Docker optionnel |
| Golden set + gates CI | 🟡 | 100 paires, gate intégrité en CI ; gate retrieval = stack live |
| Éval retrieval vs génération | 🟢 | `metrics.py` + `evaluate.py` ; `--retrieval-only` sans LLM |
| Modèle multi-domaines | 🟢 | ADR-001 Accepted : mono-API |
| Persistance métadonnées | 🟡 | SQLite (`db.py`) ; Postgres dans compose **commenté** (non branché) |
| BM25 | 🟡 | In-memory par processus ; fingerprint SQL pour invalidation cross-worker |
| Ingestion multimodale | 🔴 | Texte seul ; tableaux/images DOCX non extraits |
| Config domaines par org | 🔴 | Domaine = config globale + détection |

## Évaluation

| Commande | Rôle |
|----------|------|
| `make eval-gate` | Intégrité golden set (CI, sans stack) |
| `make eval-retrieval` | Retrieval live → `report.json` (Qdrant + embeddings) |
| `make eval-retrieval-gate` | Seuils sur `report.json` |
| `make eval` | RAGAS complet (LLM judge) |

---

Détail tickets et sprints : **[`CHANGEMENTS/ROADMAP_RAG.md`](../CHANGEMENTS/ROADMAP_RAG.md)**
