"""Script to create a new Syro instance for a specific domain."""

import os
import shutil
import sys
from pathlib import Path


def create_instance(domain: str, instance_name: str | None = None):
    """
    Create a new Syro instance for a specific domain.
    
    Args:
        domain: Domain ID (tech, medical, legal, finance, education, general)
        instance_name: Instance folder name (default: Syro{domain.capitalize()})
    """
    # Domain mapping
    domain_names = {
        "tech": "SyroTech",
        "medical": "SyroMed",
        "legal": "SyroLegal",
        "finance": "SyroFinance",
        "education": "SyroEdu",
        "mlops": "SyroMLOps",
        "general": "Syro",
    }
    
    if domain not in domain_names:
        print(f"Domaine invalide: {domain}")
        print(f"Domaines disponibles: {', '.join(domain_names.keys())}")
        return False
    
    if instance_name is None:
        instance_name = domain_names[domain]
    
    base_dir = Path(__file__).parent
    syro_base = base_dir / "Syro"
    instance_dir = base_dir / instance_name
    
    # Check if Syro base exists
    if not syro_base.exists():
        print(f"Le dossier de base 'Syro' n'existe pas.")
        print(f"   Creez d'abord le dossier Syro avec le code commun.")
        return False
    
    # Check if instance already exists
    if instance_dir.exists():
        response = input(f"Le dossier '{instance_name}' existe deja. Voulez-vous le remplacer? (o/N): ")
        if response.lower() != 'o':
            print("Operation annulee.")
            return False
        shutil.rmtree(instance_dir)
    
    print(f"Creation de l'instance '{instance_name}' pour le domaine '{domain}'...")
    
    # Create instance directory
    instance_dir.mkdir(exist_ok=True)
    
    # Copy essential files and directories
    files_to_copy = [
        "requirements.txt",
        "docker-compose.yml",
        "pytest.ini",
    ]
    
    # Copy UI files if they exist
    ui_files = ["streamlit_app.py", "run_ui.py"]
    for ui_file in ui_files:
        ui_src = syro_base / ui_file
        if ui_src.exists():
            files_to_copy.append(ui_file)
    
    # Copy .env.example if it exists
    env_example_src = syro_base / ".env.example"
    if env_example_src.exists():
        files_to_copy.append(".env.example")
    
    dirs_to_copy = [
        "app",
        "scripts",
        "tests",
    ]
    
    # Copy files
    for file_name in files_to_copy:
        src = syro_base / file_name
        if src.exists():
            shutil.copy2(src, instance_dir / file_name)
            print(f"  Copie: {file_name}")
    
    # Copy directories
    for dir_name in dirs_to_copy:
        src = syro_base / dir_name
        if src.exists():
            shutil.copytree(src, instance_dir / dir_name, dirs_exist_ok=True)
            print(f"  Copie: {dir_name}/")
    
    # Create instance-specific directories
    (instance_dir / "db").mkdir(exist_ok=True)
    (instance_dir / "storage").mkdir(exist_ok=True)
    (instance_dir / "storage" / "tmp").mkdir(exist_ok=True)
    
    # Copy schema.sql
    schema_src = syro_base / "db" / "schema.sql"
    if schema_src.exists():
        (instance_dir / "db").mkdir(exist_ok=True)
        shutil.copy2(schema_src, instance_dir / "db" / "schema.sql")
        print(f"  Copie: db/schema.sql")
    
    # Create .env file
    env_content = f"""# Configuration pour {instance_name}
DOMAIN={domain}
SECRET_KEY=dev-secret-change-me-in-production
DEBUG=True

# OpenAI (optionnel)
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
EMBEDDINGS_MODEL=text-embedding-3-large
CHAT_MODEL=gpt-4o-mini

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME={instance_name.lower()}_chunks

# Database
DB_PATH=db/{instance_name.lower()}.db
DATA_DIR=storage

# Hybrid Search
HYBRID_SEARCH_ALPHA=0.7
RETRIEVAL_TOP_K=10
RERANK_TOP_K=5

# Reranking
ENABLE_RERANKING=True
RERANK_WEIGHT=0.7
"""
    
    env_file = instance_dir / ".env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"  Cree: .env")
    
    # Create README.md for instance
    readme_content = f"""# {instance_name}

Instance Syro pour le domaine **{domain}**.

## 🚀 Démarrage rapide

### 1. Installer les dépendances
```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Démarrer Qdrant
```bash
docker-compose up -d qdrant
```

### 3. Initialiser la base de données
```bash
python scripts/init_db.py
```

### 4. Configurer .env
Le fichier `.env` est déjà créé avec la configuration pour le domaine **{domain}**.
Modifiez-le si nécessaire (notamment `SECRET_KEY` et `OPENAI_API_KEY`).

### 5. Lancer l'API
```bash
uvicorn app.main:app --reload
```

L'API sera disponible sur `http://localhost:8000`

## 📚 Documentation

Voir la documentation principale dans le dossier `Syro/` pour plus d'informations.

## 🔧 Configuration

Le domaine est configure dans le fichier .env :
```env
DOMAIN={domain}
```

Pour changer de domaine, modifiez cette valeur et redemarrez l'API.
"""
    
    readme_file = instance_dir / "README.md"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"  Cree: README.md")
    
    print(f"\nInstance '{instance_name}' creee avec succes !")
    print(f"\nProchaines etapes :")
    print(f"   1. cd {instance_name}")
    print(f"   2. python -m venv .venv")
    print(f"   3. .venv\\Scripts\\activate  # Windows")
    print(f"   4. pip install -r requirements.txt")
    print(f"   5. python scripts/init_db.py")
    print(f"   6. uvicorn app.main:app --reload")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_syro_instance.py <domain> [instance_name]")
        print("\nDomaines disponibles:")
        print("  - tech      → SyroTech")
        print("  - medical   → SyroMed")
        print("  - legal     → SyroLegal")
        print("  - finance   → SyroFinance")
        print("  - education → SyroEdu")
        print("  - mlops     → SyroMLOps")
        print("  - general   → Syro")
        print("\nExemple:")
        print("  python create_syro_instance.py medical")
        print("  python create_syro_instance.py legal SyroLegal")
        sys.exit(1)
    
    domain = sys.argv[1]
    instance_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = create_instance(domain, instance_name)
    sys.exit(0 if success else 1)

