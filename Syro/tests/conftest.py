"""
Configuration globale pour pytest.
Les markers (unit, integration, slow, security, worker) sont déclarés dans pytest.ini.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(autouse=True)
def clear_dependency_overrides(app):
    yield
    app.dependency_overrides.clear()


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
