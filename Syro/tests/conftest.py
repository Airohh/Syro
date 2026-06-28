"""
Configuration globale pour pytest.
Les markers (unit, integration, slow, security, worker) sont déclarés dans pytest.ini.
"""

import os

# --- Garde GPU : tests CPU-only --------------------------------------------
# Charger un modèle torch sur CUDA (RTX 4070) pendant les tests peut planter
# le driver GPU et faire redémarrer le PC (TDR Windows). On masque le GPU
# AVANT tout import de torch/FlagEmbedding/sentence-transformers pour que tout
# tombe sur CPU. conftest = importé en premier, donc en tête de fichier.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# --- Garde réseau modèles : interdit tout téléchargement HuggingFace -------
# Symptôme observé : un vrai FlagReranker(...) déclenche le download de
# bge-reranker-v2-m3 (~20 Go) avec des barres tqdm qui inondent le terminal
# et saturent la RAM → freeze + reboot du PC. En mode offline, tout chargement
# réel de modèle échoue IMMÉDIATEMENT (fail-fast) au lieu de figer la machine.
# Les tests utilisent le stub FlagEmbedding ci-dessous, jamais le vrai poids.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import pytest
import sys
import types
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# --- Stub FlagEmbedding (reranker) ---------------------------------------
# Le vrai reranker charge BAAI/bge-reranker-v2-m3 (modèle lourd, ~20 Go RAM)
# dès que Reranker._load_model() atteint son chemin réel. On enregistre un
# faux module FlagEmbedding AVANT tout import de app.services.reranker, pour
# que `from FlagEmbedding import FlagReranker` récupère un stub déterministe.
# Les tests qui mockent eux-mêmes _load_model (test_reranker) ne sont pas
# affectés ; le test ImportError force __import__ et passe toujours.
if "FlagEmbedding" not in sys.modules:
    _fake_flag = types.ModuleType("FlagEmbedding")

    class FlagReranker:  # noqa: N801 — nom imposé par l'API réelle
        def __init__(self, *args, **kwargs):
            pass

        def compute_score(self, pairs, normalize=False):
            # Scalaire pour une paire (tuple), liste sinon — comme le vrai modèle.
            if isinstance(pairs, tuple):
                return 0.5
            return [0.5] * len(pairs)

    _fake_flag.FlagReranker = FlagReranker
    sys.modules["FlagEmbedding"] = _fake_flag


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(autouse=True)
def reset_qdrant_singleton():
    # Le client Qdrant est un singleton module-level. Sans reset, un mock
    # QdrantClient posé par un test fuiterait sur les suivants (le singleton
    # garderait la connexion du test précédent). On le remet à None avant ET
    # après chaque test, uniquement si le module a déjà été importé.
    def _reset():
        vs_module = sys.modules.get("app.services.vector_store")
        if vs_module is not None:
            vs_module._shared_client = None

    _reset()
    yield
    _reset()


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    # Ne dépend PAS de la fixture `app` : une dépendance directe forcerait
    # l'import de app.main (torch, langchain, mlflow…) pour CHAQUE test,
    # y compris les tests unitaires purs. On ne nettoie que si l'app a
    # réellement été importée par le test.
    yield
    app_module = sys.modules.get("app.main")
    if app_module is not None:
        app_module.app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_user():
    return {
        "id": 1,
        "email": "test@example.com",
        "role": "member",
        "organization_id": 1,
        "is_active": True,
    }


@pytest.fixture
def mock_org():
    return {
        "id": 1,
        "name": "Test Org",
        "status": "active",
        "credit_balance": 100.0,
        "max_members": 10,
    }
