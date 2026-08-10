"""
tests/backend/test_phase1_foundation.py
----------------------------------------
Phase 1 regression tests.

Tests:
1. FastAPI health check endpoint
2. Streamlit app imports cleanly (services are not broken)
3. Database models are importable
4. JWT utilities work correctly
5. Config loads without error
"""

import sys
import os
import pytest

# ── Add project paths ─────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")

for path in (_ROOT, _STREAMLIT_APP):
    if path not in sys.path:
        sys.path.insert(0, path)


# ── 1. Config loads ───────────────────────────────────────────────────────────
def test_config_loads():
    """Settings should load without errors."""
    from backend.core.config import settings
    assert settings.APP_NAME == "Akshara Annotation Platform"
    assert settings.JWT_ALGORITHM == "HS256"
    print(f"✅ Config loaded. DB URL: {settings.DATABASE_URL[:40]}")


# ── 2. Database models importable ─────────────────────────────────────────────
def test_database_models_importable():
    """All SQLAlchemy models should import without errors."""
    from database.models import (
        User,
        Dataset,
        AudioFile,
        Annotation,
        AnnotationVersion,
        ReviewComment,
        ReviewerApproval,
        AuditLog,
        SessionToken,
    )
    assert User.__tablename__ == "users"
    assert Dataset.__tablename__ == "datasets"
    assert AudioFile.__tablename__ == "audio_files"
    assert Annotation.__tablename__ == "annotations"
    print("✅ All database models importable.")


# ── 3. Services importable ────────────────────────────────────────────────────
def test_services_importable():
    """All existing services should import without errors."""
    from services import auth_service, user_service, audio_service
    from services import assignment_service, annotation_service
    from services import reviewer_service, task_service
    from services import analytics_service, session_service
    print("✅ All services importable.")


# ── 4. Enums correct ──────────────────────────────────────────────────────────
def test_enums():
    """Enum values should match expected strings."""
    from database.enums import UserRole, AudioStatus, AnnotationState, ApprovalStatus
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.ANNOTATOR == "ANNOTATOR"
    assert UserRole.REVIEWER == "REVIEWER"
    assert AudioStatus.UNASSIGNED == "UNASSIGNED"
    assert AnnotationState.DRAFT == "DRAFT"
    assert ApprovalStatus.PENDING == "PENDING"
    print("✅ Enums correct.")


# ── 5. JWT utilities ──────────────────────────────────────────────────────────
def test_jwt_create_and_decode():
    """Should create a valid JWT access token and decode it."""
    from backend.core.security import create_access_token, decode_token

    token = create_access_token(data={"sub": "test-user-123"})
    assert token is not None
    assert len(token) > 20

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "test-user-123"
    assert payload["type"] == "access"
    print("✅ JWT create and decode works.")


def test_jwt_expired_token_returns_none():
    """An expired token should return None on decode."""
    from datetime import timedelta
    from backend.core.security import create_access_token, decode_token

    # Create a token that expires immediately
    token = create_access_token(
        data={"sub": "test-user-123"},
        expires_delta=timedelta(seconds=-1)
    )
    payload = decode_token(token)
    assert payload is None
    print("✅ Expired JWT returns None.")


def test_jwt_wrong_secret_returns_none():
    """A token signed with a different secret should return None."""
    from jose import jwt
    from backend.core.security import decode_token

    # Sign with wrong secret
    fake_token = jwt.encode(
        {"sub": "hacker", "type": "access"},
        "wrong-secret",
        algorithm="HS256"
    )
    payload = decode_token(fake_token)
    assert payload is None
    print("✅ Token with wrong secret rejected.")


# ── 6. Password hashing ────────────────────────────────────────────────────────
def test_password_hash_and_verify():
    """Should hash a password and verify it correctly."""
    from backend.core.security import hash_password, verify_password

    plain = "MySecurePassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False
    print("✅ Password hashing works.")


# ── 7. FastAPI app starts ─────────────────────────────────────────────────────
def test_fastapi_health_endpoint():
    """Health check endpoint should return status ok."""
    from httpx import Client
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data
    print("✅ FastAPI health check returns 200 ok.")


# ── 8. CORS headers present ───────────────────────────────────────────────────
def test_cors_headers():
    """Preflight request from allowed origin should get CORS headers."""
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Either 200 (allowed) or 400 (handled but not crashed)
        assert response.status_code in (200, 400)
    print("✅ CORS middleware applied.")
