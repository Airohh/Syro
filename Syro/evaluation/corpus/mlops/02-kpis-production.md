# KPIs à surveiller pour un modèle en production

## Pourquoi surveiller

Un modèle qui performait bien à l'entraînement peut se dégrader en production (drift, charge, bugs). Le monitoring détecte ces problèmes tôt. On suit quatre familles d'indicateurs.

## 1. Performance du modèle (qualité)

- **Métriques métier** : accuracy, F1, précision/rappel, AUC pour la classification ; RMSE/MAE pour la régression.
- Pour un RAG : faithfulness, pertinence de la réponse, taux de réponses « je ne sais pas ».
- Souvent calculées en différé car le label réel (ground truth) arrive plus tard.

## 2. Qualité des données (drift)

- **Data drift** : la distribution des features d'entrée change par rapport à l'entraînement.
- **Concept drift** : la relation entre entrées et cible change.
- **Data quality** : valeurs manquantes, hors plage, schémas inattendus.

## 3. Performance opérationnelle (système)

- **Latence** (p50, p95, p99) et **débit** (requêtes/seconde).
- **Taux d'erreur** (5xx), **disponibilité** (uptime).
- **Coût** : consommation CPU/GPU/mémoire, coût par requête (tokens LLM).

## 4. Usage et business

- Volume de requêtes, taux d'adoption.
- Signaux de satisfaction utilisateur (feedback pouce haut/bas, taux de réponse jugée utile).

## Mise en pratique

On instrumente l'application (Prometheus pour les métriques système, logs structurés), on définit des **seuils d'alerte** et on visualise dans des dashboards (Grafana). L'objectif : être alerté avant que l'utilisateur ne subisse la dégradation.
