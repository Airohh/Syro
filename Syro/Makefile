# Makefile pour Syro - Commandes courantes

.PHONY: help up down logs build clean test lint format release

help: ## Afficher cette aide
	@echo "Commandes disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Démarrer tous les services (profil local-llm par défaut)
	docker compose -f infra/docker-compose.yml -f infra/docker-compose.local-llm.yml up -d

up-openai: ## Démarrer avec OpenAI (nécessite OPENAI_API_KEY dans .env)
	docker compose -f infra/docker-compose.yml -f infra/docker-compose.openai.yml up -d

down: ## Arrêter tous les services
	docker compose -f infra/docker-compose.yml down

logs: ## Voir les logs de tous les services
	docker compose -f infra/docker-compose.yml logs -f

logs-api: ## Voir les logs de l'API uniquement
	docker compose -f infra/docker-compose.yml logs -f syro-api

logs-frontend: ## Voir les logs du frontend uniquement
	docker compose -f infra/docker-compose.yml logs -f syro-frontend

build: ## Rebuild toutes les images
	docker compose -f infra/docker-compose.yml build --no-cache

build-api: ## Rebuild uniquement l'image API
	docker compose -f infra/docker-compose.yml build --no-cache syro-api

build-frontend: ## Rebuild uniquement l'image frontend
	docker compose -f infra/docker-compose.yml build --no-cache syro-frontend

clean: ## Nettoyer volumes et images (ATTENTION: supprime les données)
	docker compose -f infra/docker-compose.yml down -v
	docker rmi syro-api syro-frontend 2>/dev/null || true

test: ## Lancer les tests (local)
	pytest

test-cov: ## Lancer les tests avec coverage
	pytest --cov=app --cov=worker --cov-report=html --cov-report=term

test-unit: ## Lancer uniquement les tests unitaires
	pytest -m unit

test-integration: ## Lancer uniquement les tests d'intégration
	pytest -m integration

test-security: ## Lancer uniquement les tests de sécurité
	pytest -m security

test-worker: ## Lancer uniquement les tests worker
	pytest -m worker

test-docker: ## Lancer les tests dans Docker
	docker compose -f infra/docker-compose.yml exec syro-api pytest

smoke: ## Smoke test post-deploiement (API + Qdrant + Redis + MLflow)
	python scripts/smoke_test.py

eval: ## Evaluation RAGAS reproductible (necessite OPENAI_API_KEY ou USE_OLLAMA=true)
	python evaluation/evaluate.py

benchmark: ## Benchmark latence p50/p95/p99 (retrieval vs end-to-end, stack requis)
	python evaluation/benchmark.py --repeats 5

lint: ## Lancer le linting (ruff)
	ruff check app worker tests
	ruff format --check app worker tests

format: ## Formater le code (ruff)
	ruff format app worker tests

version: ## Afficher la version actuelle
	@python scripts/version.py get

version-bump-patch: ## Incrémenter la version patch (1.2.3 -> 1.2.4)
	@python scripts/version.py bump patch

version-bump-minor: ## Incrémenter la version minor (1.2.3 -> 1.3.0)
	@python scripts/version.py bump minor

version-bump-major: ## Incrémenter la version major (1.2.3 -> 2.0.0)
	@python scripts/version.py bump major

release: ## Créer une release (nécessite VERSION=1.2.3 ou utilise version actuelle)
	@if [ -z "$(VERSION)" ]; then \
		VERSION=$$(python scripts/version.py get); \
		echo "Utilisation de la version actuelle: $$VERSION"; \
	else \
		python scripts/version.py set $(VERSION); \
	fi
	@VERSION=$$(python scripts/version.py get); \
	git add VERSION CHANGELOG.md; \
	git commit -m "chore: bump version to $$VERSION" || true; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	git push origin main --tags; \
	echo "Release v$$VERSION créée. GitHub Actions va créer la release automatiquement."

ps: ## Voir l'état des conteneurs
	docker compose -f infra/docker-compose.yml ps

restart: ## Redémarrer tous les services
	docker compose -f infra/docker-compose.yml restart

restart-api: ## Redémarrer uniquement l'API
	docker compose -f infra/docker-compose.yml restart syro-api

shell-api: ## Ouvrir un shell dans le conteneur API
	docker compose -f infra/docker-compose.yml exec syro-api /bin/bash

shell-postgres: ## Ouvrir un shell PostgreSQL
	docker compose -f infra/docker-compose.yml exec postgres psql -U syro -d syro

logs-worker: ## Voir les logs du worker uniquement
	docker compose -f infra/docker-compose.yml logs -f syro-worker

restart-worker: ## Redémarrer uniquement le worker
	docker compose -f infra/docker-compose.yml restart syro-worker

shell-worker: ## Ouvrir un shell dans le conteneur worker
	docker compose -f infra/docker-compose.yml exec syro-worker /bin/bash

