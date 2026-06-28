#  Guide de Démarrage Rapide
## Installation
### Prérequis
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (pour le frontend)
### Installation Rapide

```bash
# 1. Cloner le repository
git clone https://github.com/Airohh/Syro.git
cd Syro/Syro

# 2. Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Démarrer Qdrant
docker-compose up -d qdrant

# 5. Initialiser la base de données
python scripts/init_db.py

# 6. Lancer l'API
uvicorn app.main:app --reload
```
## Frontend

```bash
cd Syro/frontend
npm install
npm run dev
```
## Utilisation

1. L'API sera disponible sur `http://localhost:8000`
2. Le frontend sera disponible sur `http://localhost:5173`
3. Documentation API : `http://localhost:8000/docs`
## Configuration

Créez un fichier `.env` à la racine de l'application :

```env
DOMAIN=tech
SECRET_KEY=your-secret-key-here
QDRANT_URL=http://localhost:6333
DB_PATH=./db/syro.db
```

