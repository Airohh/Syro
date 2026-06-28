# Docker Compose pour orchestrer un stack multi-services

## Rôle

Docker Compose permet de définir et lancer une application **multi-conteneurs** à partir d'un seul fichier YAML (`docker-compose.yml`). On décrit chaque service, ses dépendances et son réseau, puis on démarre tout avec `docker compose up`.

## Concepts clés

- **Service** : un conteneur (image, build, ports, variables d'environnement, commande).
- **Réseau** : Compose crée un réseau par défaut où chaque service est joignable par son **nom** (ex. `http://qdrant:6333`).
- **Volumes** : persistance des données hors du cycle de vie du conteneur (base vectorielle, base SQL).
- **depends_on** : ordre de démarrage des services.
- **healthcheck** : Compose vérifie qu'un service est réellement prêt avant que les dépendants l'utilisent.

## Exemple pour un stack RAG

Un stack typique déclare : l'API (FastAPI), un worker (Celery), Qdrant (base vectorielle), Redis (broker), et un serveur de tracking (MLflow). Chaque service communique via le réseau interne par son nom de service.

## Profils et overrides

- **Profiles** : activer un sous-ensemble de services selon le contexte (dev, prod, local-llm).
- **Fichiers d'override** : `docker-compose.override.yml` ou `-f fichier1.yml -f fichier2.yml` pour superposer des configurations (par exemple ajouter un sidecar Ollama en local, ou basculer sur OpenAI).

## Commandes utiles

- `docker compose up -d` : démarrer en arrière-plan.
- `docker compose logs -f api` : suivre les logs d'un service.
- `docker compose down` : tout arrêter (ajouter `-v` pour supprimer les volumes).

Compose rend le stack reproductible : un seul `up` et l'environnement complet est prêt.
