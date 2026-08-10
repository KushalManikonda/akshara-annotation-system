import sys
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")
if _STREAMLIT_APP not in sys.path:
    sys.path.insert(0, _STREAMLIT_APP)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base

# Create in-memory database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_db(request, monkeypatch):
    """
    Creates fresh tables for every test and patches SessionLocal in all services.
    Skips patching for Phase 2/3/4 tests which need the real PostgreSQL instance.
    """
    if any(x in request.module.__name__ for x in ["phase2_database", "phase3_storage", "phase4_api"]):
        yield
        return

    Base.metadata.create_all(bind=engine)
    
    # Patch all services that use SessionLocal directly
    monkeypatch.setattr("services.annotation_service.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("services.reviewer_service.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("services.auth_service.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("services.audio_service.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("services.assignment_service.SessionLocal", TestingSessionLocal)
    
    yield
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    """Provides a database session for the test functions to setup mock data."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
