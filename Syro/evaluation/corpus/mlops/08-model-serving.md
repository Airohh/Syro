# Model serving — déployer un modèle ML en production

## Qu'est-ce que le model serving

Le model serving consiste à rendre un modèle entraîné **accessible pour l'inférence**, généralement derrière une API, afin que des applications puissent obtenir des prédictions en temps réel ou par lots.

## Modes de service

- **Online / temps réel** : une API (REST/gRPC) répond à la demande, faible latence. Cas d'usage interactif (RAG, recommandation, scoring à la volée).
- **Batch** : on prédit sur de gros volumes en différé (jobs planifiés), latence non critique.
- **Streaming** : prédictions sur un flux d'événements (Kafka).
- **Edge** : le modèle tourne sur l'appareil (mobile, IoT) pour la confidentialité et la latence.

## Options techniques

- **API maison** : FastAPI/Flask qui charge le modèle (load-once via cache) et expose `/predict`. Simple et flexible.
- **Serveurs d'inférence dédiés** : TorchServe, TensorFlow Serving, NVIDIA Triton — optimisés (batching dynamique, GPU, multi-modèles).
- **Formats portables** : exporter en **ONNX** pour l'interopérabilité et l'accélération.
- **Plateformes managées** : AWS SageMaker, Google Vertex AI, Azure ML, ou serverless (conteneurs).
- **MLflow Models** : packaging standard servable sur plusieurs cibles.

## Bonnes pratiques

- **Conteneuriser** (Docker) pour la reproductibilité.
- **Charger le modèle une seule fois** au démarrage, pas à chaque requête.
- **Versionner** les modèles (Model Registry) et permettre le rollback.
- **Monitorer** latence, débit, erreurs et qualité des prédictions (drift).
- **Scalabilité** : autoscaling horizontal, batching des requêtes, GPU si nécessaire.
- **Déploiements progressifs** : canary ou blue-green pour limiter le risque.

Le serving transforme un artefact de modèle en service fiable, observable et scalable.
