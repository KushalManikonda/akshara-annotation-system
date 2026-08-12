"""
migrations/versions/003_local_audio_path.py
--------------------------------------------
Non-breaking migration: adds two new nullable columns to audio_files.

  audio_relative_path  VARCHAR  NULLABLE
    Portable relative path, e.g. 'Telugu/telugu1.wav'.
    Never contains machine-specific prefixes like C:\\ or /Users/.
    Resolved at runtime as: AUDIO_ROOT_DIR + '/' + audio_relative_path

  audio_storage_type  VARCHAR  NULLABLE
    'local'    — WAV is NOT in Supabase; user selects it in the browser.
    'supabase' — WAV is in Supabase Storage (legacy behaviour).
    NULL       — treated as 'supabase' for backward compatibility.

Existing rows are unaffected (both columns default to NULL).
"""

from alembic import op
import sqlalchemy as sa

# Alembic revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "audio_files",
        sa.Column("audio_relative_path", sa.String(), nullable=True),
    )
    op.add_column(
        "audio_files",
        sa.Column("audio_storage_type", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column("audio_files", "audio_storage_type")
    op.drop_column("audio_files", "audio_relative_path")
