"""
tests/backend/test_phase4_api.py
--------------------------------
Phase 4 API endpoint regression tests.
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from backend.main import app
from backend.core.dependencies import get_current_user
from database.models import User

client = TestClient(app)

def mock_get_current_user():
    return User(
        id="mock_id",
        username="admin",
        role="SUPERADMIN",
        is_active=True
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

def test_get_users():
    response = client.get("/users/")
    # If the database returns users, it will be 200.
    # Otherwise it might be 200 with [] depending on DB state.
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_datasets():
    response = client.get("/datasets/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_audio():
    response = client.get("/audio/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
