"""
test_analytics_service.py
--------------------------
Unit tests for services/analytics_service.py.
Uses an in-memory SQLite database seeded with known data so every
assertion is deterministic.

Strategy: patch `services.analytics_service.SessionLocal` directly so the
service always opens connections to the in-memory database, regardless of
what the real database.py file does.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base

# Create a fresh in-memory DB for every test session
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)

@pytest.fixture(autouse=True, scope="module")
def setup_db():
    """Create tables, seed test data, and patch the service's SessionLocal."""
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    from database.models import User, Dataset, AudioFile, Annotation, AnnotationVersion, ReviewerApproval
    from database.enums import UserRole, AudioStatus, AnnotationState, ApprovalStatus

    # ── Users ────────────────────────────────────────────────────────────────
    admin = User(
        id="u-admin", username="admin", email="admin@test.com",
        password_hash="x", role=UserRole.ADMIN
    )
    ann1 = User(
        id="u-ann1", username="annotator1", email="ann1@test.com",
        password_hash="x", role=UserRole.ANNOTATOR,
        created_at=datetime(2025, 1, 1)
    )
    ann2 = User(
        id="u-ann2", username="annotator2", email="ann2@test.com",
        password_hash="x", role=UserRole.ANNOTATOR,
        created_at=datetime(2025, 1, 2)
    )
    rev1 = User(
        id="u-rev1", username="reviewer1", email="rev1@test.com",
        password_hash="x", role=UserRole.REVIEWER,
        created_at=datetime(2025, 1, 3)
    )

    # ── Dataset ──────────────────────────────────────────────────────────────
    ds = Dataset(
        id="ds-test", name="TestDataset", zip_filename="test.zip",
        language="hi", uploaded_by="u-admin",
        total_files=3, total_duration=30.0, total_size=0
    )

    # ── Audio files ───────────────────────────────────────────────────────────
    af1 = AudioFile(
        id="af-t1", dataset_id="ds-test", filename="a1.wav",
        original_filename="a1.wav", file_path="/a1.wav",
        language="hi", duration=10.0,
        status=AudioStatus.COMPLETED, uploaded_by="u-admin"
    )
    af2 = AudioFile(
        id="af-t2", dataset_id="ds-test", filename="a2.wav",
        original_filename="a2.wav", file_path="/a2.wav",
        language="hi", duration=10.0,
        status=AudioStatus.SUBMITTED, uploaded_by="u-admin"
    )
    af3 = AudioFile(
        id="af-t3", dataset_id="ds-test", filename="a3.wav",
        original_filename="a3.wav", file_path="/a3.wav",
        language="en", duration=10.0,
        status=AudioStatus.UNASSIGNED, uploaded_by="u-admin"
    )

    # ── Annotations ───────────────────────────────────────────────────────────
    now = datetime.utcnow()
    ann_a = Annotation(
        id="anno-t1", audio_id="af-t1", annotator_id="u-ann1",
        state=AnnotationState.APPROVED,
        created_at=now - timedelta(days=5),
        submitted_at=now - timedelta(days=3)
    )
    ann_b = Annotation(
        id="anno-t2", audio_id="af-t2", annotator_id="u-ann1",
        state=AnnotationState.SUBMITTED,
        created_at=now - timedelta(days=2),
        submitted_at=now - timedelta(days=1)
    )
    ann_c = Annotation(
        id="anno-t3", audio_id="af-t3", annotator_id="u-ann2",
        state=AnnotationState.DRAFT,
        created_at=now - timedelta(days=1)
    )

    # ── AnnotationVersions ────────────────────────────────────────────────────
    av1 = AnnotationVersion(
        id="av-t1", annotation_id="anno-t1", version_number=1,
        submitted_by="u-ann1", submitted_at=now - timedelta(days=3)
    )
    av2 = AnnotationVersion(
        id="av-t2", annotation_id="anno-t2", version_number=1,
        submitted_by="u-ann1", submitted_at=now - timedelta(days=1)
    )

    # ── ReviewerApproval ─────────────────────────────────────────────────────
    ra1 = ReviewerApproval(
        id="ra-t1", annotation_id="anno-t1", reviewer_id="u-rev1",
        version_approved=1, status=ApprovalStatus.APPROVED,
        created_at=now - timedelta(days=2)
    )

    db.add_all([admin, ann1, ann2, rev1, ds, af1, af2, af3,
                ann_a, ann_b, ann_c, av1, av2, ra1])
    db.commit()
    db.close()

    # Patch the SessionLocal that analytics_service uses (must stay active for whole module)
    import services.analytics_service as svc
    orig = svc.SessionLocal
    svc.SessionLocal = TestingSession
    yield
    svc.SessionLocal = orig
    Base.metadata.drop_all(bind=engine)


# ── Import service ─────────────────────────────────────────────────────────────
from services.analytics_service import (
    get_kpi_summary,
    get_pipeline_funnel,
    get_annotation_trend,
    get_dataset_breakdown,
    get_language_breakdown,
    get_annotator_leaderboard,
    get_reviewer_leaderboard,
    get_user_detail,
)


class TestKPISummary:
    def test_total_users(self):
        data = get_kpi_summary()
        assert data["total_users"] == 4  # admin + 2 ann + 1 rev

    def test_role_counts(self):
        data = get_kpi_summary()
        assert data["total_annotators"] == 2
        assert data["total_reviewers"] == 1

    def test_total_audio(self):
        data = get_kpi_summary()
        assert data["total_audio"] == 3

    def test_total_duration(self):
        data = get_kpi_summary()
        assert data["total_duration"] == pytest.approx(30.0)

    def test_approved_counts(self):
        data = get_kpi_summary()
        assert data["approved_count"] == 1
        assert data["submitted_count"] == 1
        assert data["draft_count"] == 1

    def test_approved_duration_and_pct(self):
        data = get_kpi_summary()
        assert data["approved_duration"] == pytest.approx(10.0)
        assert data["approved_pct"] == pytest.approx(100.0)


class TestPipelineFunnel:
    def test_returns_all_stages(self):
        funnel = get_pipeline_funnel()
        stages = [f["stage"] for f in funnel]
        assert "UNASSIGNED" in stages
        assert "SUBMITTED" in stages
        assert "COMPLETED" in stages

    def test_stage_counts(self):
        funnel = get_pipeline_funnel()
        stage_map = {f["stage"]: f["count"] for f in funnel}
        assert stage_map["UNASSIGNED"] == 1
        assert stage_map["SUBMITTED"] == 1
        assert stage_map["COMPLETED"] == 1


class TestAnnotationTrend:
    def test_returns_correct_length(self):
        trend = get_annotation_trend(days=7)
        assert len(trend) == 7

    def test_recent_submissions_present(self):
        trend = get_annotation_trend(days=30)
        total = sum(d["submitted"] for d in trend)
        # We seeded 2 annotation versions
        assert total == 2

    def test_date_format(self):
        trend = get_annotation_trend(days=5)
        for item in trend:
            datetime.strptime(item["date"], "%Y-%m-%d")  # must not raise


class TestDatasetBreakdown:
    def test_returns_one_dataset(self):
        data = get_dataset_breakdown()
        assert len(data) == 1
        assert data[0]["name"] == "TestDataset"

    def test_dataset_file_count(self):
        data = get_dataset_breakdown()
        assert data[0]["total_files"] == 3

    def test_approved_files(self):
        data = get_dataset_breakdown()
        assert data[0]["approved_files"] == 1

    def test_approved_pct(self):
        data = get_dataset_breakdown()
        assert data[0]["approved_pct"] == pytest.approx(100.0 / 3.0, abs=0.5)


class TestLanguageBreakdown:
    def test_returns_both_languages(self):
        data = get_language_breakdown()
        langs = [d["language"] for d in data]
        assert "hi" in langs
        assert "en" in langs

    def test_hi_count(self):
        data = get_language_breakdown()
        hi = next(d for d in data if d["language"] == "hi")
        assert hi["file_count"] == 2

    def test_en_count(self):
        data = get_language_breakdown()
        en = next(d for d in data if d["language"] == "en")
        assert en["file_count"] == 1


class TestAnnotatorLeaderboard:
    def test_returns_two_annotators(self):
        data = get_annotator_leaderboard()
        assert len(data) == 2

    def test_sorted_by_approved(self):
        data = get_annotator_leaderboard()
        # ann1 has 1 approved, ann2 has 0 — ann1 should be first
        assert data[0]["username"] == "annotator1"
        assert data[0]["approved"] == 1

    def test_quality_pct_present(self):
        data = get_annotator_leaderboard()
        ann1 = next(d for d in data if d["username"] == "annotator1")
        assert "quality_pct" in ann1
        assert "avg_turnaround_days" not in ann1


class TestReviewerLeaderboard:
    def test_returns_one_reviewer(self):
        data = get_reviewer_leaderboard()
        assert len(data) == 1
        assert data[0]["username"] == "reviewer1"

    def test_approval_count(self):
        data = get_reviewer_leaderboard()
        assert data[0]["approvals"] == 1
        assert data[0]["rejections"] == 0


class TestUserDetail:
    def test_annotator_detail(self):
        detail = get_user_detail("u-ann1")
        assert detail is not None
        assert detail["role"] == "ANNOTATOR"
        assert detail["username"] == "annotator1"
        assert detail["approved"] == 1
        assert detail["submitted"] == 1
        assert len(detail["recent_tasks"]) >= 2

    def test_reviewer_detail(self):
        detail = get_user_detail("u-rev1")
        assert detail is not None
        assert detail["role"] == "REVIEWER"
        assert detail["total_reviews"] == 1
        assert detail["approvals"] == 1

    def test_nonexistent_user_returns_none(self):
        detail = get_user_detail("does-not-exist")
        assert detail is None
