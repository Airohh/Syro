# FastAPI vs Flask pour une API REST

## Vue d'ensemble

Flask est un micro-framework synchrone historique, très répandu. FastAPI est un framework moderne basé sur Starlette (ASGI) et Pydantic, conçu pour les API.

## Avantages de FastAPI

- **Asynchrone natif** : FastAPI s'appuie sur ASGI et `async/await`, ce qui permet de gérer un grand nombre de requêtes I/O-bound concurrentes (appels LLM, base de données, HTTP) sans bloquer. Flask est synchrone par défaut (WSGI).
- **Validation automatique** : les modèles Pydantic valident et sérialisent automatiquement les corps de requête et de réponse, avec des erreurs claires. En Flask, il faut le faire à la main ou via des extensions.
- **Documentation interactive** : FastAPI génère automatiquement un schéma OpenAPI et des UIs Swagger et ReDoc à partir des types Python.
- **Typage** : utilisation des annotations de type Python pour l'injection de dépendances (`Depends`), l'auto-complétion et la sécurité.
- **Performance** : proche de Node.js et Go sur les charges I/O grâce à ASGI/Uvicorn.

## Quand Flask reste pertinent

- Petits projets ou scripts où l'async n'apporte rien.
- Écosystème d'extensions matures déjà en place.
- Équipe déjà experte Flask.

## Conclusion

Pour une API REST moderne, surtout orientée I/O (RAG, microservices, appels externes), FastAPI offre validation, documentation et concurrence « gratuitement » grâce aux types et à l'async. C'est le choix par défaut recommandé aujourd'hui.
