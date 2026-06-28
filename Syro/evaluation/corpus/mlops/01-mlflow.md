# MLflow — suivi d'expériences ML

## Qu'est-ce que MLflow

MLflow est une plateforme open source de gestion du cycle de vie du machine learning. Elle aide à tracer, reproduire et déployer les modèles. Elle est agnostique au framework (scikit-learn, PyTorch, XGBoost, etc.).

## Les composants principaux

- **MLflow Tracking** : enregistre les **paramètres**, **métriques**, **artefacts** (modèles, graphiques) et le **code** de chaque exécution (run). On compare ainsi les expériences dans une UI.
- **MLflow Projects** : empaquette le code de manière reproductible (dépendances, point d'entrée).
- **MLflow Models** : format standard pour packager un modèle et le servir sur différentes plateformes.
- **Model Registry** : catalogue centralisé des modèles avec versions et stades (Staging, Production, Archived).

## À quoi ça sert dans un projet ML

- **Comparer les expériences** : retrouver quels hyperparamètres ont donné la meilleure métrique.
- **Reproductibilité** : chaque run garde son code, ses données et son environnement.
- **Collaboration** : une UI partagée pour visualiser les résultats de l'équipe.
- **Gouvernance** : le registry trace quelle version d'un modèle est en production et permet de revenir en arrière (rollback).

## Utilisation typique

```python
import mlflow
with mlflow.start_run():
    mlflow.log_param("alpha", 0.7)
    mlflow.log_metric("faithfulness", 0.82)
    mlflow.log_artifact("results.json")
```

Dans un pipeline RAG, MLflow sert à tracer les évaluations (scores RAGAS, latence) au fil des changements de configuration, pour piloter les améliorations par la donnée.
