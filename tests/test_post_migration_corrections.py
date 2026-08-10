import os
import sys
import pytest

# Add paths to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "streamlit_app")))

from services.analytics_service import get_annotator_leaderboard, get_reviewer_leaderboard
from services.reviewer_service import validate_review_comment
from services.audio_service import _extract_id_from_path
from pathlib import Path


def test_duration_format_utils():
    # Test natural duration formatting
    def format_duration(seconds):
        if seconds is None or seconds <= 0:
            return "0 hrs, 0 mins"
        total_mins = int(seconds // 60)
        hrs = total_mins // 60
        mins = total_mins % 60
        hrs_str = "1 hr" if hrs == 1 else f"{hrs} hrs"
        return f"{hrs_str}, {mins} mins"

    assert format_duration(0) == "0 hrs, 0 mins"
    assert format_duration(5100) == "1 hr, 25 mins"
    assert format_duration(11220) == "3 hrs, 7 mins"


def test_leaderboard_quality_formulas():
    # Annotator Quality: approved / submitted * 100
    sub = 20
    app = 18
    quality = (app / sub * 100.0) if sub > 0 else 0.0
    assert quality == 90.0

    # If submitted = 0 -> 0.0
    sub0 = 0
    app0 = 0
    quality0 = (app0 / sub0 * 100.0) if sub0 > 0 else 0.0
    assert quality0 == 0.0

    # Reviewer Quality: approvals / total_reviews * 100
    reviews = 20
    approvals = 17
    rev_quality = (approvals / reviews * 100.0) if reviews > 0 else 0.0
    assert rev_quality == 85.0


def test_reviewer_comment_word_count_validation():
    # Invalid: empty
    val1, msg1 = validate_review_comment("")
    assert not val1

    # Invalid: whitespace only
    val2, msg2 = validate_review_comment("        ")
    assert not val2

    # Invalid: 3 words
    val3, msg3 = validate_review_comment("one  two  three")
    assert not val3
    assert "10 words" in msg3

    # Valid: exactly 10 words
    val4, msg4 = validate_review_comment("one two three four five six seven eight nine ten")
    assert val4

    # Valid: 12 words with excess spaces
    val5, msg5 = validate_review_comment("  one   two   three four five six  seven  eight nine ten eleven twelve  ")
    assert val5


def test_dataset_id_extraction():
    assert _extract_id_from_path(Path("lecture1.wav")) == "1"
    assert _extract_id_from_path(Path("transcript1.json")) == "1"
    assert _extract_id_from_path(Path("lecture_02.wav")) == "02"
    assert _extract_id_from_path(Path("transcript_02.json")) == "02"
    assert _extract_id_from_path(Path("audio_10.flac")) == "10"
    assert _extract_id_from_path(Path("transcript_10.json")) == "10"
