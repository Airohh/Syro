# Architecture Syro — état actuel

> **⚠️ Statut de ce document : description de l'état réel, PAS un backlog.**
> Ce fichier était à l'origine un design doc pré-build (phases ⬜ à faire). La
> plupart de ces phases sont aujourd'hui implémentées. Le **plan d'exécution
> vivant** (tickets, sprints, priorités, gaps) est :
>
> 👉 **[`CHANGEMENTS/ROADMAP_RAG.md`](../CHANGEMENTS/ROADMAP_RAG.md)**
>
> Ne pas utiliser ce fichier comme source de vérité pour « ce qu'il reste à
> faire » — se référer à la roadmap.

---

## Vue d'ensemble

Syro est un RAG hybride multi-domaines : FastAPI + Qdrant (dense) + BM25
(sparse), fusion RRF, reranking cross-encoder, ingestion async Celery,
observabilité Prometheus/OpenTelemetry, éval RAGAS.

```
Question
   │
   ▼
┌──────────────────┐   auto-détection mots-clés (domain_detector.py)
│  Domain routing  │   ou domaine forcé (/domains/{domain}/chat)
└────────┬─────────┘
         │
   ┌─────┴─────┐  recherche parallèle (ThreadPoolExecutor)
   ▼           ▼
┌──────┐   ┌──────┐
│Vector│   │ BM25 │   embedding KO → dégradation BM25-only
│Qdrant│   │      │
└──┬───┘   └──┬───┘
   └────┬─────┘
        ▼
┌───────────────┐   Reciprocal Rank Fusion (rrf_k, immune aux échelles)
│  RRF fusion   │
└───────┬───────┘
        ▼
┌───────────────┐   bge-reranker-v2-m3 (GPU/CPU auto, fallback ordre RRF)
│  Cross-encoder│
│  rerank       │
└───────┬───────┘
        ▼
┌───────────────┐   prompt par domaine (mono) ou adaptatif (multi)
│  LLM answer   │
└───────────────┘
```

## État par capacité

Échelle : 🟢 au niveau de l'état de l'art · 🟡 fait avec dette · 🔴 absent.

| Capacité | État | Où / Note |
|----------|------|-----------|
| Détection de domaine | 🟢 | `domain_detector.py` — **mots-clés**, pas de modèle ML |
| Recherche multi-domaines | 🟢 | `multi_domain_rag.py`, appelé par `chat.py` si >1 domaine détecté |
| Fusion résultats | 🟢 | RRF dans `hybrid_search.py` (`alpha` déprécié/ignoré) |
| Fusion multi-domaines | 🟡 | tri par **score × confiance**, PAS un 2ᵉ rerank cross-encoder global |
| Reranking | 🟢 | cross-encoder `bge-reranker-v2-m3`, blend score RRF × `rerank_weight` |
| Métadonnée `domain` sur chunks | 🟢 | `worker/tasks.py` / `rag.py` → `metadata["domain"]` |
| Prompts adaptatifs | 🟢 | `get_adaptive_prompt()` (multi-domaine) |
| Résilience chat (500) | 🟢 | embedding KO → BM25-only ; voir `docs/diagnostic-chat-500.md` |
| Config domaines **par organisation** | 🔴 | pas de colonne `organizations.domains` ; domaine = config globale + détection |
| Cache de classification | 🔴 | absent |
| Query understanding (rewriting/HyDE) | 🔴 | question brute envoyée au retrieval → roadmap T2.1/T2.2 |
| Historique conversationnel dans le RAG | 🟡 | stocké (`conversations`/`messages`) mais **jamais injecté** dans `build_answer`/prompt → roadmap T2.5 |
| Cache sémantique | 🔴 | absent → roadmap T4.5 |
| Agentique (CRAG/Self-RAG) | 🔴 | `agent.py` = persona, pas d'orchestration → roadmap E3 |
| Golden set + éval CI | 🟡 | ~20 paires → roadmap T1.1–T1.4 |
| Tracing RAG (Langfuse) | 🔴 | MLflow ≠ trace par requête → roadmap T1.3 |

## Décision multi-domaines (non tranchée)

Deux modèles coexistent sans ADR : multi-instances par ports
(`frontend/utils/domainPorts.ts`) **et** multi-domaines 1 API
(`DOMAIN=general` + collections/filtres Qdrant). Arbitrage = roadmap **T0.4**
(ADR-001).

---

Pour le détail des gaps, priorités, tickets et sprints : **[`CHANGEMENTS/ROADMAP_RAG.md`](../CHANGEMENTS/ROADMAP_RAG.md)**.
