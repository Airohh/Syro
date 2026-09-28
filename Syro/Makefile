# Syro — raccourcis. Sans make : les commandes docker compose sont dans le README.
.DEFAULT_GOAL := help
.PHONY: help up demo down logs ps restart clean dev test lint format eval-gate eval eval-retrieval reindex

help: ## Afficher cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- Utilisation -----------------------------------------------------------
up: ## Démarrer toute la stack (UI :5173, API :8000)
	docker compose up -d --build
	@echo "UI  : http://localhost:5173  (demo@syro.local / syro-demo)"
	@echo "API : http://localhost:8000/docs"

demo: ## Charger les 19 documents de démo (à lancer après `make up`)
	docker compose exec syro-api python scripts/load_demo.py

down: ## Arrêter la stack (les données sont conservées)
	docker compose down

logs: ## Suivre les logs de l'API et du worker
	docker compose logs -f syro-api syro-worker

ps: ## État des conteneurs
	docker compose ps

restart: ## Redémarrer l'API et le worker
	docker compose restart syro-api syro-worker

reindex: ## Réindexer tous les documents (après changement de modèle d'embedding)
	docker compose exec syro-api python scripts/reindex.py

clean: ## Tout supprimer, données comprises (demande confirmation)
	@read -p "Supprimer TOUTES les données (documents, index, modèles) ? [y/N] " a && [ "$$a" = y ]
	docker compose down -v

# --- Développement ---------------------------------------------------------
dev: ## API en local (hot reload) avec Qdrant + Redis + Ollama en Docker
	docker compose up -d qdrant redis ollama ollama-init
	uvicorn app.main:app --reload --port 8000

test: ## Tests (sans service externe)
	pytest

lint: ## Ruff + Black (comme la CI)
	ruff check app worker scripts
	black --check app worker scripts

format: ## Formater le code
	black app worker scripts
	ruff check app worker scripts --fix

# --- Évaluation ------------------------------------------------------------
eval-gate: ## Intégrité du golden set (sans service)
	python evaluation/validate_golden_set.py

eval-retrieval: ## Métriques retrieval live (Recall/nDCG/MRR) → evaluation/report.json
	docker compose exec syro-api python evaluation/ingest_corpus.py
	docker compose exec syro-api python evaluation/evaluate.py --retrieval-only

eval: ## Évaluation complète RAGAS (LLM juge, pip install -r evaluation/requirements-eval.txt)
	python evaluation/evaluate.py
