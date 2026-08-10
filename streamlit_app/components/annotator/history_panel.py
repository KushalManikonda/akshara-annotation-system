"""
history_panel.py – Phase 7
Renders the Annotation Version History panel.

Shared between:
  - Annotator workspace (read, compare, restore)
  - Reviewer workspace  (read, compare only — no restore)

Args to `render()`:
    annotation_id   : str  – the annotation whose versions to show.
    current_text    : str  – the text currently in the editor (used as the
                             "right side" of the diff).
    allow_restore   : bool – True for annotators, False for reviewers.

Returns:
    The transcript text to restore to, or None if no restore was requested.
"""

import streamlit as st
from datetime import datetime

from services.version_service import get_versions, restore_version
from utils.diff_utils import build_unified_diff_html, texts_are_identical


def _fmt_dt(dt) -> str:
    if not dt:
        return "—"
    if isinstance(dt, datetime):
        return dt.strftime("%d %b %Y, %H:%M")
    return str(dt)


@st.dialog("📄 Version Diff", width="large")
def _show_diff_dialog(version_number: int, old_text: str, new_text: str):
    """Streamlit dialog that displays the visual diff."""
    st.caption(
        f"Comparing **v{version_number}** (snapshot) → **current working draft**"
    )

    if texts_are_identical(old_text, new_text):
        st.success("✅ The current draft is identical to this snapshot.")
        return

    diff_html = build_unified_diff_html(
        old_text=old_text or "",
        new_text=new_text or "",
        old_label=f"v{version_number} (snapshot)",
        new_label="Current Draft",
    )
    st.html(diff_html)


def render(annotation_id: str, current_text: str, allow_restore: bool = True):
    """
    Render the history panel inside an expander.

    Returns the transcript to restore to if the user clicked Restore,
    otherwise returns None.
    """
    versions = get_versions(annotation_id)

    with st.expander(
        f"🕓 Version History ({len(versions)} submission{'s' if len(versions) != 1 else ''})",
        expanded=False,
    ):

        if not versions:
            st.info("No submissions yet. History will appear here after you submit.")
            return None

        restore_text = None

        for v in versions:
            c_info, c_compare, c_restore = st.columns([5, 2, 2])

            with c_info:
                label = f"**v{v.version_number}**"
                if v.version_number == versions[-1].version_number:
                    # oldest
                    label += " *(first submission)*"
                elif v.version_number == versions[0].version_number:
                    label += " *(latest)*"
                st.markdown(label)
                st.caption(f"Submitted: {_fmt_dt(v.submitted_at)}")

            with c_compare:
                if st.button(
                    "Compare",
                    key=f"compare_v{v.id}",
                    use_container_width=True,
                    help=f"See what changed between v{v.version_number} and your current draft",
                ):
                    _show_diff_dialog(v.version_number, v.transcript_snapshot, current_text)

            with c_restore:
                if allow_restore:
                    if st.button(
                        "Restore",
                        key=f"restore_v{v.id}",
                        use_container_width=True,
                        help=f"Roll back to the text from v{v.version_number}",
                        type="secondary",
                    ):
                        restore_text = v.transcript_snapshot

            st.divider()

        return restore_text
