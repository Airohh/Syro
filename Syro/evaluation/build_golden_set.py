"""Construit/étend le golden set d'évaluation (ticket T1.1).

Le golden set étendu ajoute, par paire, les champs nécessaires à l'éval
retrieval (T1.2) en plus de la génération :
    - question        : la requête utilisateur
    - ground_truth    : réponse de référence (ancrée dans le corpus)
    - domain          : tech | mlops
    - intent          : bucket d'intention (cf. INTENTS)
    - relevant_doc_ids: noms de fichiers corpus pertinents (= documents.filename),
                        [] pour les questions hors-corpus (refus attendu)

Process : ce script charge `eval_dataset.json`, fusionne les NEW_ENTRIES
curées ci-dessous (dédup par question normalisée) et réécrit le fichier.
Idempotent : ré-exécuter ne crée pas de doublons.

Usage :
    cd Syro
    python evaluation/build_golden_set.py

Note qualité (R1) : ground_truth/relevant_doc_ids sont rédigés depuis le
corpus mais doivent être relus par un annotateur (DA) avant d'être traités
comme vérité de référence à 100 %.
"""

from __future__ import annotations

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "eval_dataset.json"

# Buckets d'intention couverts (>= 4, cf. T1.1)
INTENTS = {"factual_lookup", "exact_identifier", "multi_hop", "out_of_corpus"}


def _e(domain, intent, question, ground_truth, docs):
    return {
        "domain": domain,
        "intent": intent,
        "question": question,
        "ground_truth": ground_truth,
        "relevant_doc_ids": docs,
    }


def _norm(q: str) -> str:
    return " ".join(q.lower().split())


NEW_ENTRIES: list[dict] = [
    # ---------- tech/01 RAG fundamentals ----------
    _e("tech", "factual_lookup", "Quelles sont les trois étapes du pipeline RAG ?",
       "Indexation (découpage en chunks, embeddings, stockage vectoriel), récupération (la question est encodée puis comparée aux chunks pour le top-k) et génération (les chunks récupérés sont injectés dans le prompt du LLM).",
       ["01-rag-fundamentals.md"]),
    _e("tech", "factual_lookup", "Pourquoi le RAG réduit-il les hallucinations ?",
       "Parce que la réponse est ancrée dans des documents réels et citables récupérés à la requête, au lieu de provenir uniquement des paramètres entraînés du modèle.",
       ["01-rag-fundamentals.md"]),
    _e("tech", "factual_lookup", "Quand préférer le RAG au fine-tuning pour ajouter de la connaissance ?",
       "Dès qu'il faut répondre sur un corpus spécifique, à jour et vérifiable : le RAG met à jour la base sans réentraîner et évite le coût du fine-tuning.",
       ["01-rag-fundamentals.md"]),
    _e("tech", "factual_lookup", "Que se passe-t-il à l'étape de récupération du RAG ?",
       "La question de l'utilisateur est encodée puis comparée aux chunks indexés pour récupérer les plus pertinents (top-k).",
       ["01-rag-fundamentals.md"]),
    # ---------- tech/02 vectoriel / BM25 / hybride ----------
    _e("tech", "factual_lookup", "Quelle est la faiblesse de la recherche vectorielle dense ?",
       "Elle peut manquer une correspondance exacte de terme rare (référence produit, acronyme précis) car elle raisonne sur le sens.",
       ["02-recherche-vectorielle-bm25.md"]),
    _e("tech", "exact_identifier", "Sur quoi repose le score BM25 ?",
       "Sur la fréquence des termes (TF), la fréquence inverse de document (IDF) et la normalisation par la longueur du document.",
       ["02-recherche-vectorielle-bm25.md"]),
    _e("tech", "exact_identifier", "Comment la recherche hybride combine-t-elle les deux scores ?",
       "Par une somme pondérée, par ex. score = α·score_vectoriel + (1-α)·score_BM25 ; avec α=0,7 on privilégie le sémantique tout en gardant la précision lexicale.",
       ["02-recherche-vectorielle-bm25.md"]),
    # ---------- tech/03 chunking ----------
    _e("tech", "exact_identifier", "Quels sont les paramètres typiques de taille et d'overlap d'un chunk ?",
       "Taille cible de 300 à 800 tokens par chunk, overlap de 10 à 20 % de la taille du chunk.",
       ["03-chunking-hierarchique.md"]),
    _e("tech", "factual_lookup", "Pourquoi appliquer un overlap entre chunks consécutifs ?",
       "Pour ne pas perdre une idée à cheval sur une frontière entre deux chunks.",
       ["03-chunking-hierarchique.md"]),
    _e("tech", "factual_lookup", "Quelle métadonnée le chunking hiérarchique permet-il de conserver ?",
       "Le chemin de titres (headers), ce qui améliore le contexte fourni au LLM.",
       ["03-chunking-hierarchique.md"]),
    # ---------- tech/04 reranking ----------
    _e("tech", "exact_identifier", "Quel modèle est typiquement utilisé comme reranker ?",
       "Un cross-encoder, par exemple BAAI/bge-reranker-v2-m3.",
       ["04-reranking.md"]),
    _e("tech", "exact_identifier", "Combien de chunks garde-t-on après reranking pour le LLM ?",
       "Le rerank top-k, typiquement 3 à 5 passages.",
       ["04-reranking.md"]),
    _e("tech", "factual_lookup", "Quel est le coût du reranking et comment le gérer ?",
       "Une latence supplémentaire ; on l'active en mode qualité et on peut le désactiver en mode rapide.",
       ["04-reranking.md"]),
    # ---------- tech/05 bi/cross-encoder ----------
    _e("tech", "factual_lookup", "Pourquoi un bi-encoder est-il rapide pour le retrieval ?",
       "Parce qu'il encode requête et documents séparément : les embeddings des documents sont pré-calculés et indexés, on compare alors un vecteur de requête à des vecteurs pré-calculés.",
       ["05-bi-encoder-cross-encoder.md"]),
    _e("tech", "exact_identifier", "Quel modèle de bi-encoder est cité pour sentence-transformers ?",
       "all-MiniLM-L6-v2.",
       ["05-bi-encoder-cross-encoder.md"]),
    _e("tech", "factual_lookup", "Pourquoi le cross-encoder ne peut-il pas chercher dans toute la base ?",
       "Il prend la paire (requête, document) ensemble et ne peut rien pré-calculer : il faut une passe du modèle par paire, trop lent à l'échelle de la base.",
       ["05-bi-encoder-cross-encoder.md"]),
    # ---------- tech/06 Qdrant ----------
    _e("tech", "exact_identifier", "Quel index Qdrant utilise-t-il pour la recherche ANN ?",
       "HNSW (Hierarchical Navigable Small World).",
       ["06-qdrant.md"]),
    _e("tech", "exact_identifier", "En quel langage Qdrant est-il écrit ?",
       "En Rust.",
       ["06-qdrant.md"]),
    _e("tech", "factual_lookup", "Qu'est-ce qu'un point dans Qdrant ?",
       "Un vecteur accompagné de son id et de son payload (métadonnées JSON).",
       ["06-qdrant.md"]),
    _e("tech", "factual_lookup", "Comment Qdrant gère-t-il le multi-tenant ?",
       "Par le filtrage par métadonnées (ex. domain ou organization_id) combiné à la similarité vectorielle, et par des collections isolées par domaine ou tenant.",
       ["06-qdrant.md"]),
    # ---------- tech/07 JWT ----------
    _e("tech", "exact_identifier", "Quelles sont les trois parties d'un JWT ?",
       "Un header, un payload (les claims comme sub, exp, role) et une signature, encodés en base64url.",
       ["07-fastapi-jwt-auth.md"]),
    _e("tech", "factual_lookup", "Pourquoi un JWT est-il dit stateless ?",
       "Le serveur n'a pas besoin de stocker la session : il vérifie simplement la signature du token.",
       ["07-fastapi-jwt-auth.md"]),
    _e("tech", "exact_identifier", "Quel utilitaire FastAPI récupère le token depuis le header Authorization ?",
       "OAuth2PasswordBearer.",
       ["07-fastapi-jwt-auth.md"]),
    _e("tech", "exact_identifier", "Avec quoi hache-t-on le mot de passe au login ?",
       "bcrypt.",
       ["07-fastapi-jwt-auth.md"]),
    # ---------- tech/08 rate limiting ----------
    _e("tech", "exact_identifier", "Quel code HTTP renvoyer quand le quota de rate limiting est dépassé ?",
       "429 Too Many Requests, avec un en-tête Retry-After.",
       ["08-rate-limiting-fastapi.md"]),
    _e("tech", "factual_lookup", "Pourquoi utiliser Redis plutôt que la mémoire pour le rate limiting ?",
       "Dès qu'il y a plusieurs workers/instances, le compteur doit être partagé entre eux.",
       ["08-rate-limiting-fastapi.md"]),
    _e("tech", "factual_lookup", "Cite trois algorithmes de rate limiting.",
       "Fixed window, sliding window et token bucket.",
       ["08-rate-limiting-fastapi.md"]),
    _e("tech", "exact_identifier", "Quel en-tête informe le client du quota restant ?",
       "X-RateLimit-Remaining.",
       ["08-rate-limiting-fastapi.md"]),
    # ---------- tech/09 FastAPI vs Flask ----------
    _e("tech", "factual_lookup", "Pourquoi FastAPI gère-t-il mieux les charges I/O concurrentes que Flask ?",
       "FastAPI s'appuie sur ASGI et async/await (non bloquant), alors que Flask est synchrone par défaut (WSGI).",
       ["09-fastapi-vs-flask.md"]),
    _e("tech", "exact_identifier", "Sur quels composants repose FastAPI ?",
       "Starlette (ASGI) et Pydantic.",
       ["09-fastapi-vs-flask.md"]),
    _e("tech", "factual_lookup", "Quelle documentation FastAPI génère-t-il automatiquement ?",
       "Un schéma OpenAPI et des interfaces Swagger et ReDoc à partir des types Python.",
       ["09-fastapi-vs-flask.md"]),
    # ---------- tech/10 sécurité API ----------
    _e("tech", "factual_lookup", "Pourquoi ne faut-il jamais exposer les détails d'exception au client ?",
       "Pour éviter de fuiter des informations (stack trace) ; on renvoie un message générique et on logue le détail côté serveur.",
       ["10-securite-api-rest.md"]),
    _e("tech", "factual_lookup", "Comment configurer CORS de façon sûre en production ?",
       "Strictement : autoriser uniquement les origines de confiance, pas '*' en production.",
       ["10-securite-api-rest.md"]),
    _e("tech", "factual_lookup", "Où stocker les secrets d'une API ?",
       "Dans des variables d'environnement ou un coffre, jamais dans le code ni le dépôt.",
       ["10-securite-api-rest.md"]),
    _e("tech", "exact_identifier", "Cite deux en-têtes de sécurité HTTP recommandés.",
       "Par exemple Strict-Transport-Security, X-Content-Type-Options: nosniff, X-Frame-Options, Content-Security-Policy.",
       ["10-securite-api-rest.md"]),
    # ---------- tech/11 docker compose ----------
    _e("tech", "factual_lookup", "Comment les services se joignent-ils dans un réseau Docker Compose ?",
       "Par leur nom de service sur le réseau par défaut créé par Compose (ex. http://qdrant:6333).",
       ["11-docker-compose.md"]),
    _e("tech", "factual_lookup", "À quoi sert depends_on dans Docker Compose ?",
       "À définir l'ordre de démarrage des services.",
       ["11-docker-compose.md"]),
    _e("tech", "factual_lookup", "Comment superposer des configurations Docker Compose ?",
       "Via docker-compose.override.yml ou plusieurs fichiers -f fichier1.yml -f fichier2.yml.",
       ["11-docker-compose.md"]),
    # ---------- mlops/01 MLflow ----------
    _e("mlops", "factual_lookup", "Que tracke MLflow Tracking ?",
       "Les paramètres, métriques, artefacts (modèles, graphiques) et le code de chaque run.",
       ["01-mlflow.md"]),
    _e("mlops", "exact_identifier", "Quels sont les stades d'un modèle dans le Model Registry MLflow ?",
       "Staging, Production, Archived.",
       ["01-mlflow.md"]),
    _e("mlops", "exact_identifier", "Quelle fonction MLflow démarre un run et logue une métrique ?",
       "mlflow.start_run() (en contexte), puis mlflow.log_metric(...) (avec aussi log_param et log_artifact).",
       ["01-mlflow.md"]),
    # ---------- mlops/02 KPIs ----------
    _e("mlops", "factual_lookup", "Quelles sont les quatre familles de KPIs à surveiller en production ?",
       "Performance du modèle (qualité), qualité des données (drift), performance opérationnelle (système) et usage/business.",
       ["02-kpis-production.md"]),
    _e("mlops", "exact_identifier", "Quels percentiles de latence surveille-t-on ?",
       "p50, p95 et p99.",
       ["02-kpis-production.md"]),
    _e("mlops", "factual_lookup", "Pourquoi les métriques de qualité sont-elles souvent calculées en différé ?",
       "Parce que le label réel (ground truth) arrive plus tard.",
       ["02-kpis-production.md"]),
    # ---------- mlops/03 observabilité ----------
    _e("mlops", "factual_lookup", "Quels sont les trois piliers de l'observabilité ?",
       "Les logs, les métriques et les traces.",
       ["03-observabilite-rag.md"]),
    _e("mlops", "factual_lookup", "À quoi sert un correlation ID ?",
       "À suivre une requête de bout en bout (retrieval, reranking, génération) dans les logs structurés.",
       ["03-observabilite-rag.md"]),
    _e("mlops", "exact_identifier", "Quel outil trace une requête à travers chaque service et étape ?",
       "OpenTelemetry.",
       ["03-observabilite-rag.md"]),
    # ---------- mlops/04 drift ----------
    _e("mlops", "factual_lookup", "Quelle est la différence entre data drift et concept drift ?",
       "Le data drift est le changement de la distribution des features P(X) ; le concept drift est le changement de la relation P(y|X) entre entrées et cible.",
       ["04-data-drift.md"]),
    _e("mlops", "exact_identifier", "Quels tests statistiques détectent le drift ?",
       "PSI (Population Stability Index), le test de Kolmogorov-Smirnov, et le Chi-2 pour les variables catégorielles.",
       ["04-data-drift.md"]),
    _e("mlops", "exact_identifier", "Cite deux outils de détection de drift.",
       "Evidently et NannyML (ou des checks maison loggés dans MLflow).",
       ["04-data-drift.md"]),
    # ---------- mlops/05 Celery ----------
    _e("mlops", "factual_lookup", "De quoi Celery a-t-il besoin pour fonctionner ?",
       "D'un broker de messages (souvent Redis ou RabbitMQ), et optionnellement d'un backend de résultats.",
       ["05-celery-rag-async.md"]),
    _e("mlops", "exact_identifier", "Quel statut a un document juste après l'upload, avant traitement ?",
       "queued.",
       ["05-celery-rag-async.md"]),
    _e("mlops", "exact_identifier", "Quel mode Celery exécute les tâches de façon synchrone pour les tests ?",
       "Le mode eager (task_always_eager=True).",
       ["05-celery-rag-async.md"]),
    # ---------- mlops/06 RAGAS ----------
    _e("mlops", "factual_lookup", "Quelles métriques RAGAS évaluent le retrieval ?",
       "Context Recall (toute l'information nécessaire est-elle récupérée) et Context Precision (les passages pertinents sont-ils bien classés en tête).",
       ["06-metriques-ragas.md"]),
    _e("mlops", "factual_lookup", "Que signifie une faithfulness basse ?",
       "Une hallucination : la réponse n'est pas soutenue par les passages récupérés.",
       ["06-metriques-ragas.md"]),
    _e("mlops", "factual_lookup", "RAGAS a-t-il besoin d'annotations humaines à grande échelle ?",
       "Non : il utilise un LLM comme juge pour noter automatiquement ; chaque métrique est un score entre 0 et 1.",
       ["06-metriques-ragas.md"]),
    # ---------- mlops/07 éval sans RAGAS ----------
    _e("mlops", "exact_identifier", "Cite des métriques de ranking pour évaluer le retrieval sans LLM.",
       "Recall@k, Precision@k, MRR (Mean Reciprocal Rank) et nDCG.",
       ["07-evaluer-rag-sans-ragas.md"]),
    _e("mlops", "factual_lookup", "Que mesure le MRR ?",
       "L'inverse du rang du premier passage pertinent : il récompense le fait de le placer en tête.",
       ["07-evaluer-rag-sans-ragas.md"]),
    _e("mlops", "exact_identifier", "Quelles métriques comparent une réponse générée à une référence ?",
       "BLEU, ROUGE, METEOR (chevauchement) et la similarité sémantique type BERTScore.",
       ["07-evaluer-rag-sans-ragas.md"]),
    # ---------- mlops/08 model serving ----------
    _e("mlops", "factual_lookup", "Quels sont les modes de model serving ?",
       "Online/temps réel, batch, streaming et edge.",
       ["08-model-serving.md"]),
    _e("mlops", "factual_lookup", "Pourquoi charger le modèle une seule fois au démarrage ?",
       "Pour éviter de le recharger à chaque requête (load-once via cache).",
       ["08-model-serving.md"]),
    _e("mlops", "exact_identifier", "Cite des serveurs d'inférence dédiés.",
       "TorchServe, TensorFlow Serving et NVIDIA Triton.",
       ["08-model-serving.md"]),
    _e("mlops", "exact_identifier", "Quel format portable exporter pour l'interopérabilité ?",
       "ONNX.",
       ["08-model-serving.md"]),
    _e("mlops", "exact_identifier", "Cite deux stratégies de déploiement progressif.",
       "Canary et blue-green.",
       ["08-model-serving.md"]),
    # ---------- multi-hop (>= 2 documents) ----------
    _e("tech", "multi_hop", "Comment bi-encoder et cross-encoder se combinent-ils dans le pattern RAG standard ?",
       "Récupération large par bi-encoder (retrieval rapide et scalable), puis reranking par cross-encoder (précision) sur les candidats.",
       ["05-bi-encoder-cross-encoder.md", "04-reranking.md"]),
    _e("tech", "multi_hop", "Pourquoi combiner recherche hybride et reranking ?",
       "La recherche hybride (vectorielle + BM25) récupère largement les bons passages, puis le reranking cross-encoder réordonne finement et ne garde que les meilleurs pour le LLM.",
       ["02-recherche-vectorielle-bm25.md", "04-reranking.md"]),
    _e("mlops", "multi_hop", "Quelle métrique RAGAS correspond au Recall@k de l'éval sans RAGAS, et que diagnostiquent-elles ?",
       "Le Context Recall de RAGAS et le Recall@k mesurent tous deux si le retrieval a récupéré les passages nécessaires ; un score bas pointe un problème de retrieval (chunking, embeddings, top-k).",
       ["06-metriques-ragas.md", "07-evaluer-rag-sans-ragas.md"]),
    _e("mlops", "multi_hop", "Comment Celery et l'observabilité se combinent-ils pour l'ingestion ?",
       "Celery exécute l'ingestion en arrière-plan et met à jour le statut ; l'observabilité (logs, métriques Prometheus, traces) instrumente chaque étape pour suivre latence et erreurs.",
       ["05-celery-rag-async.md", "03-observabilite-rag.md"]),
    _e("mlops", "multi_hop", "Quel lien entre data drift et les KPIs de production ?",
       "Le data drift est l'une des familles de KPIs (qualité des données) à surveiller ; sa détection par tests statistiques déclenche une alerte puis un réentraînement.",
       ["04-data-drift.md", "02-kpis-production.md"]),
    _e("tech", "multi_hop", "Pourquoi un bon chunking améliore-t-il les métriques de retrieval ?",
       "Un chunking hiérarchique produit des chunks sémantiquement cohérents, ce qui augmente le rappel/la précision du contexte (Context Recall/Precision ou Recall@k/nDCG) car les frontières suivent le sens.",
       ["03-chunking-hierarchique.md", "07-evaluer-rag-sans-ragas.md"]),
    _e("tech", "multi_hop", "Comment sécuriser une API FastAPI contre l'accès non autorisé et les abus ?",
       "Authentification JWT via dépendances (OAuth2PasswordBearer, get_current_user) et rate limiting (réponses 429) pour contrer le brute force/DoS, le tout servi en HTTPS.",
       ["07-fastapi-jwt-auth.md", "10-securite-api-rest.md"]),
    _e("tech", "multi_hop", "Quel rôle jouent Qdrant et Docker Compose dans un stack RAG ?",
       "Qdrant est la base vectorielle (mémoire sémantique) interrogée à chaque requête ; Docker Compose orchestre l'API, le worker, Qdrant, Redis et MLflow sur un réseau commun.",
       ["06-qdrant.md", "11-docker-compose.md"]),
    # ---------- out-of-corpus (refus attendu, relevant_doc_ids vide) ----------
    _e("tech", "out_of_corpus", "Quel est le prix par token de GPT-4 chez OpenAI ?",
       "Cette information n'est pas présente dans le corpus documentaire.",
       []),
    _e("mlops", "out_of_corpus", "Comment configurer un Horizontal Pod Autoscaler dans Kubernetes ?",
       "Le corpus ne couvre pas Kubernetes ; l'information n'est pas disponible.",
       []),
    _e("tech", "out_of_corpus", "Quelle est la capitale de l'Australie ?",
       "Question hors sujet : cette information n'est pas dans le corpus documentaire.",
       []),
    _e("mlops", "out_of_corpus", "Comment fine-tuner Llama 3 avec LoRA ?",
       "Le corpus ne traite pas du fine-tuning de Llama 3 ni de LoRA.",
       []),
    _e("tech", "out_of_corpus", "Quelle est la complexité temporelle du tri rapide ?",
       "Cette information n'est pas couverte par le corpus.",
       []),
    _e("mlops", "out_of_corpus", "Comment déployer une fonction sur AWS Lambda avec Terraform ?",
       "Le corpus ne décrit pas le déploiement AWS Lambda ni Terraform.",
       []),
    _e("tech", "out_of_corpus", "Quels sont les horaires d'ouverture du support Syro ?",
       "Cette information n'existe pas dans le corpus documentaire.",
       []),
    _e("mlops", "out_of_corpus", "Comment entraîner un réseau de neurones convolutif pour la vision ?",
       "Le corpus ne couvre pas les CNN ni la vision par ordinateur.",
       []),
]


# 20 paires historiques (pré-T1.1) sans intent / relevant_doc_ids — backfill DA.
LEGACY_BACKFILL: dict[str, dict] = {
    _norm(
        "Qu'est-ce que le RAG (Retrieval-Augmented Generation) et quels sont ses avantages par rapport à un LLM seul ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["01-rag-fundamentals.md"]},
    _norm(
        "Quelle est la différence entre la recherche vectorielle et la recherche BM25 ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["02-recherche-vectorielle-bm25.md"]},
    _norm("Comment fonctionne le chunking hiérarchique de documents ?"): {
        "intent": "factual_lookup",
        "relevant_doc_ids": ["03-chunking-hierarchique.md"],
    },
    _norm(
        "Qu'est-ce que le reranking dans un pipeline RAG et pourquoi est-il utile ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["04-reranking.md"]},
    _norm(
        "Qu'est-ce que MLflow et à quoi sert-il dans un projet de machine learning ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["01-mlflow.md"]},
    _norm(
        "Quels sont les principaux indicateurs de performance (KPIs) à surveiller pour un modèle en production ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["02-kpis-production.md"]},
    _norm(
        "Qu'est-ce que Celery et comment s'intègre-t-il dans une architecture RAG asynchrone ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["05-celery-rag-async.md"]},
    _norm("Comment fonctionne l'authentification JWT dans une API FastAPI ?"): {
        "intent": "factual_lookup",
        "relevant_doc_ids": ["07-fastapi-jwt-auth.md"],
    },
    _norm(
        "Qu'est-ce que Qdrant et pourquoi l'utiliser comme base de données vectorielle ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["06-qdrant.md"]},
    _norm("Quelles sont les métriques RAGAS et que mesurent-elles exactement ?"): {
        "intent": "factual_lookup",
        "relevant_doc_ids": ["06-metriques-ragas.md"],
    },
    _norm("Comment mettre en place un rate limiter dans une API FastAPI ?"): {
        "intent": "factual_lookup",
        "relevant_doc_ids": ["08-rate-limiting-fastapi.md"],
    },
    _norm(
        "Qu'est-ce que l'observabilité dans un système RAG en production et comment la mettre en place ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["03-observabilite-rag.md"]},
    _norm(
        "Quelle est la différence entre un embedding bi-encoder et un cross-encoder ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["05-bi-encoder-cross-encoder.md"]},
    _norm(
        "Comment détecter et gérer le data drift dans un pipeline de production ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["04-data-drift.md"]},
    _norm(
        "Quels sont les avantages de FastAPI par rapport à Flask pour construire une API REST ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["09-fastapi-vs-flask.md"]},
    _norm(
        "Comment fonctionne Docker Compose pour orchestrer un stack multi-services ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["11-docker-compose.md"]},
    _norm(
        "Qu'est-ce que le model serving et quelles sont les options pour déployer un modèle ML en production ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["08-model-serving.md"]},
    _norm(
        "Comment implémenter une recherche sémantique avec sentence-transformers ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["02-recherche-vectorielle-bm25.md"]},
    _norm(
        "Quelles sont les bonnes pratiques pour sécuriser une API REST exposée publiquement ?"
    ): {"intent": "factual_lookup", "relevant_doc_ids": ["10-securite-api-rest.md"]},
    _norm("Comment évaluer la qualité d'un pipeline RAG sans RAGAS ?"): {
        "intent": "factual_lookup",
        "relevant_doc_ids": ["07-evaluer-rag-sans-ragas.md"],
    },
}


def main() -> None:
    existing = json.loads(DATASET_PATH.read_text(encoding="utf-8")) if DATASET_PATH.exists() else []
    seen = {_norm(item["question"]) for item in existing}

    backfilled = 0
    for item in existing:
        patch = LEGACY_BACKFILL.get(_norm(item["question"]))
        if not patch:
            continue
        for field in ("intent", "relevant_doc_ids"):
            if item.get(field) is None:
                item[field] = patch[field]
                backfilled += 1

    bad = [e["intent"] for e in NEW_ENTRIES if e["intent"] not in INTENTS]
    if bad:
        raise SystemExit(f"Intent(s) inconnu(s): {sorted(set(bad))}")

    added = 0
    for entry in NEW_ENTRIES:
        if _norm(entry["question"]) in seen:
            continue
        existing.append(entry)
        seen.add(_norm(entry["question"]))
        added += 1

    DATASET_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with_ids = sum(1 for e in existing if e.get("relevant_doc_ids"))
    print(f"Golden set: {len(existing)} paires (+{added} ajoutées, {backfilled} champs backfill legacy)")
    print(f"  avec relevant_doc_ids: {with_ids}")
    from collections import Counter
    print(f"  intents: {dict(Counter(e.get('intent', 'unlabeled') for e in existing))}")
    print(f"  domaines: {dict(Counter(e.get('domain', '?') for e in existing))}")


if __name__ == "__main__":
    main()
