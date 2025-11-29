# Syro - RAG Multi-Domaines

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)
![React](https://img.shields.io/badge/React-18.2.0-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Système de recherche documentaire avancé avec RAG (Retrieval-Augmented Generation) hybride**

[Features](#features) • [Installation](#installation) • [Documentation](#documentation) • [Architecture](#architecture)

</div>

---

**Syro** est un système de recherche documentaire avancé qui permet de créer plusieurs instances spécialisées par domaine (Tech, Médical, Juridique, Finance, Éducation). Chaque instance utilise une architecture RAG hybride combinant recherche vectorielle (Qdrant) et recherche lexicale (BM25) pour fournir des réponses précises basées sur vos documents.
## Features

### Recherche Hybride
- **Recherche vectorielle** (Qdrant) : Similarité sémantique
- **Recherche lexicale** (BM25) : Mots-clés exacts
- **Fusion optimisée** : Combinaison des deux méthodes
- **Reranking** : Amélioration de la précision avec FlagEmbedding
### Traitement de Documents
- **Chunking hiérarchique** : Respecte la structure markdown/HTML
- **Métadonnées enrichies** : Détection automatique (type, difficulté, tags)
- **Citations sources** : Chaque réponse inclut ses sources
### Multi-Instances
- **Architecture modulaire** : Code commun + instances spécialisées
- **6 domaines** : Tech, Médical, Juridique, Finance, Éducation, MLOps
- **Agents personnalisés** : Créez des profils de recherche avec leur propre personnalité
### Performance
- **Recherche rapide** : 10-70ms pour hybrid search
- **Scalable** : Qdrant pour millions de documents
- **API REST** : FastAPI avec documentation Swagger automatique
### Interface Utilisateur
- **React + TypeScript** : Application web moderne
- **Chat en temps réel** : Conversation fluide avec visualisation des sources
- **Design responsive** : Interface adaptée mobile et desktop
- **Electron** : Application desktop
## Installation
### Prérequis

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (pour le frontend)
### Installation Rapide

```bash
# 1. Cloner le repository
git clone https://github.com/votre-username/syro.git
cd syro

# 2. Créer une instance (ex: Tech)
python create_syro_instance.py tech

# 3. Aller dans l'instance
cd SyroTech

# 4. Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 5. Installer les dépendances
pip install -r requirements.txt

# 6. Démarrer Qdrant (optionnel, pour la recherche vectorielle)
docker-compose up -d qdrant

# 7. Configurer .env
copy env.example .env  # Windows
# cp env.example .env  # Linux/Mac
# Le fichier .env est pré-configuré, vous pouvez le modifier si nécessaire

# 8. Initialiser la base de données
python scripts/init_db.py

# 9. Lancer l'API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera disponible sur `http://localhost:8000`

**Documentation API** : `http://localhost:8000/docs`
### Frontend (Optionnel)

```bash
# Dans un autre terminal
cd SyroTech/frontend
npm install
npm run dev
```

Interface disponible sur `http://localhost:5173`

**Note** : Le backend fonctionne sans frontend. Vous pouvez utiliser l'API directement via Swagger UI.
### Connexion

- **Email**: `owner@example.com`
- **Password**: `ChangeMe123!`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI API                          │
│  (Authentification, Upload, Chat, Agents, Admin)        │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│   Qdrant     │  │    SQLite    │  │     Redis    │
│ (Vector DB)  │  │ (Metadata)   │  │   (Queue)    │
└──────────────┘  └──────────────┘  └──────────────┘
```
## Documentation

- **[docs/architecture.md](docs/architecture.md)** : Architecture détaillée
- **[docs/getting-started.md](docs/getting-started.md)** : Guide de démarrage complet
## Tests

```bash
# Lancer tous les tests
pytest

# Avec coverage
pytest --cov=app tests/
```
## Stack Technique
### Backend
- **FastAPI** : Framework web moderne
- **SQLite** : Base de données pour métadonnées
- **Qdrant** : Base de données vectorielle
- **BM25** : Recherche lexicale
### Frontend
- **React + TypeScript** : Application web moderne
- **Tailwind CSS** : Design system
- **Vite** : Build tool moderne
- **Electron** : Application desktop
### ML/Search
- **Ollama** : LLM local (optionnel)
- **OpenAI** : LLM cloud (optionnel)
- **FlagEmbedding** : Reranking (optionnel)
## Performance

| Métrique | Valeur |
|----------|--------|
| Recherche vectorielle | 10-50ms |
| Recherche BM25 | 5-20ms |
| Hybrid search | 15-70ms |
| Chat complet | 1-2s |
## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour le guide complet.
## License

Voir [LICENSE](LICENSE) pour plus d'informations.

---

Fait pour la recherche documentaire intelligente
