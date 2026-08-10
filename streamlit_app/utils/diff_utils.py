"""
diff_utils.py – Phase 7
Produces a human-readable visual diff between two RSML transcript strings.

Uses Python's stdlib `difflib.HtmlDiff` for a styled side-by-side comparison
and `difflib.unified_diff` for a compact patch-style view rendered with
colour-coded HTML spans for use inside Streamlit's `st.html()`.
"""

import difflib


# ── Colour constants ──────────────────────────────────────────────────────────
_CSS = """
<style>
  .diff-wrap        { font-family: monospace; font-size: 0.85rem;
                      line-height: 1.5; white-space: pre-wrap;
                      border: 1px solid #333; border-radius: 6px;
                      padding: 1rem; background: #0e1117; color: #e0e0e0; }
  .diff-add         { background: #1a3a1a; color: #6fcf7c; display: block; }
  .diff-del         { background: #3a1a1a; color: #f28b82; display: block;
                      text-decoration: line-through; }
  .diff-context     { color: #888; display: block; }
  .diff-header      { color: #7ec8e3; font-weight: bold; display: block; }
  .diff-meta        { color: #aaa; font-size: 0.75rem; margin-bottom: 0.5rem; }
</style>
"""


def build_unified_diff_html(old_text: str, new_text: str,
                            old_label: str = "Previous Version",
                            new_label: str = "Current Text",
                            context_lines: int = 3) -> str:
    """
    Return a self-contained HTML snippet showing a unified diff between
    `old_text` and `new_text`, colour-coded for use in st.html().

    Lines added in the new version are highlighted green.
    Lines removed from the old version are highlighted red (struck through).
    Unchanged context lines are shown in grey.
    """
    old_lines = old_text.splitlines(keepends=True) if old_text else [""]
    new_lines = new_text.splitlines(keepends=True) if new_text else [""]

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=old_label,
        tofile=new_label,
        n=context_lines,
    ))

    if not diff:
        return (
            _CSS
            + '<div class="diff-wrap">'
            + '<span class="diff-context">✅ No differences — the texts are identical.</span>'
            + '</div>'
        )

    html_lines = []

    for line in diff:
        # Escape HTML special chars
        safe = (
            line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .rstrip("\n")
        )

        if line.startswith("+++") or line.startswith("---"):
            html_lines.append(f'<span class="diff-header">{safe}</span>')
        elif line.startswith("@@"):
            html_lines.append(f'<span class="diff-header">{safe}</span>')
        elif line.startswith("+"):
            html_lines.append(f'<span class="diff-add">+ {safe[1:]}</span>')
        elif line.startswith("-"):
            html_lines.append(f'<span class="diff-del">- {safe[1:]}</span>')
        else:
            html_lines.append(f'<span class="diff-context">  {safe[1:]}</span>')

    body = "\n".join(html_lines)
    return _CSS + f'<div class="diff-wrap">{body}</div>'


def texts_are_identical(a: str, b: str) -> bool:
    """Return True if both texts normalise to the same content."""
    return (a or "").strip() == (b or "").strip()
