import streamlit as st
import html as html_lib

from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)


# ─── CSS ─────────────────────────────────────────────────────────────────────

STYLES = """
<style>
.rsml-view {
    font-family: 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 2.0;
    color: #e0e0e0;
    padding: 4px 0;
}

/* ── Mode banner ──────────────────────────────────────────────────────── */
.rsml-mode-banner {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border-radius: 6px;
    padding: 3px 12px 3px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.rsml-mode-banner.norm {
    background: #0d3b2e;
    border: 1.5px solid #27ae60;
    color: #2ecc71;
}
.rsml-mode-banner.verb {
    background: #2d1a00;
    border: 1.5px solid #e67e22;
    color: #f39c12;
}
.rsml-mode-banner .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
}
.rsml-mode-banner.norm .dot { background: #2ecc71; }
.rsml-mode-banner.verb .dot { background: #f39c12; }

/* ── Speaker turn block ───────────────────────────────────────────────── */
.rsml-speaker {
    border: 1.5px solid #444;
    border-radius: 10px;
    padding: 10px 14px;
    margin: 10px 0;
}
.rsml-speaker-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-radius: 4px;
    padding: 2px 8px;
    display: inline-block;
    margin-bottom: 6px;
}

/* ── Generic pill ─────────────────────────────────────────────────────── */
.rsml-pill {
    display: inline-block;
    border-radius: 5px;
    padding: 1px 8px;
    margin: 1px 3px;
    font-size: 13px;
    line-height: 1.6;
    white-space: nowrap;
    vertical-align: middle;
    cursor: default;
    position: relative;
    transition: filter 0.15s;
}
.rsml-pill:hover { filter: brightness(1.3); }

/* ── Isolated tags ────────────────────────────────────────────────────── */
.rsml-isolated {
    background: #2d3748;
    color: #90cdf4;
    border: 1px solid #4a5568;
}

/* ── Disfluency / prosody / paralinguistic spans ──────────────────────── */
.rsml-span { display: inline; border-radius: 4px; padding: 0 3px; margin: 0 1px; }
.rsml-span-filler        { background: rgba(255,193,7,0.13);  border-bottom: 2px solid #ffc107; }
.rsml-span-repetition    { background: rgba(255,152,0,0.13);  border-bottom: 2px solid #ff9800; }
.rsml-span-broken-word   { background: rgba(244,67,54,0.13);  border-bottom: 2px solid #f44336; }
.rsml-span-repair        { background: rgba(156,39,176,0.13); border-bottom: 2px solid #9c27b0; }
.rsml-span-false-start   { background: rgba(96,125,139,0.13); border-bottom: 2px solid #607d8b; }
.rsml-span-prolongation  { background: rgba(0,188,212,0.13);  border-bottom: 2px solid #00bcd4; }
.rsml-span-crying        { background: rgba(33,150,243,0.13); border-bottom: 2px dashed #2196f3; }
.rsml-span-yelling       { background: rgba(244,67,54,0.20);  border-bottom: 2px solid #f44336; font-weight:700; }
.rsml-span-laughing      { background: rgba(76,175,80,0.13);  border-bottom: 2px solid #4caf50; }
.rsml-span-singing       { background: rgba(171,71,188,0.13); border-bottom: 2px solid #ab47bc; }
.rsml-span-humming       { background: rgba(0,150,136,0.13);  border-bottom: 2px solid #009688; }
.rsml-span-whistling     { background: rgba(3,169,244,0.13);  border-bottom: 2px solid #03a9f4; }
.rsml-span-whispering    { background: rgba(158,158,158,0.13); border-bottom: 2px dashed #9e9e9e; font-style: italic; }
.rsml-span-emphasis      { background: rgba(255,235,59,0.16); border-bottom: 2px solid #ffeb3b; font-weight: 700; }
.rsml-span-falling-pitch { background: rgba(121,85,72,0.16);  border-bottom: 2px solid #795548; }
.rsml-span-raising-pitch { background: rgba(0,230,118,0.13);  border-bottom: 2px solid #00e676; }

/* ── Bracket / NER / CODE / ACCENT ───────────────────────────────────── */
.rsml-ner    { background: #1a3a2a; border: 1.5px solid #27ae60; color: #69e08d; }
.rsml-code   { background: #1a2a3a; border: 1.5px solid #2980b9; color: #74b9e0; }
.rsml-accent { background: #3a1a1a; border: 1.5px solid #c0392b; color: #e07474; }
.rsml-normal { background: #2a2a3a; border: 1.5px solid #555;    color: #c0c0d8; }

.rsml-pill small {
    font-size: 9px;
    opacity: 0.65;
    margin-left: 4px;
    vertical-align: super;
}

.rsml-text { color: #d8d8d8; }
</style>
"""


# ─── Speaker colour palette ───────────────────────────────────────────────────

_SPEAKER_STYLES = [
    ("background:#1a2744;border-color:#3b6db5", "color:#3b6db5;background:#1a274488", "Speaker 1"),
    ("background:#1a3320;border-color:#2e8b45", "color:#2e8b45;background:#1a332088", "Speaker 2"),
    ("background:#3a1a1a;border-color:#b53b3b", "color:#b53b3b;background:#3a1a1a88", "Speaker 3"),
    ("background:#2d2a10;border-color:#a08020", "color:#a08020;background:#2d2a1088", "Speaker 4"),
    ("background:#251a3a;border-color:#7b3bb5", "color:#7b3bb5;background:#251a3a88", "Speaker 5"),
]


def _speaker_style(n: int):
    return _SPEAKER_STYLES[(n - 1) % len(_SPEAKER_STYLES)]


# ─── Tooltip labels ───────────────────────────────────────────────────────────

_ISOLATED_LABELS = {
    # Hesitations
    "@umm": "Hesitation: umm",
    "@uhh": "Hesitation: uhh",
    "@hmm": "Hesitation: hmm",
    "@ugh": "Hesitation: ugh",
    "@huh": "Hesitation: huh",
    "@tsk": "Hesitation: tsk",
    "@uh-huh": "Hesitation: uh-huh",
    "@ehh": "Hesitation: ehh",
    # Paralinguistic
    "@laughter": "Paralinguistic: laughter",
    "@cry":      "Paralinguistic: cry",
    "@hum":      "Paralinguistic: hum",
    "@breathe":  "Paralinguistic: breathe",
    "@sniff":    "Paralinguistic: sniff",
    "@nose-blowing":     "Paralinguistic: nose-blowing",
    "@cough":            "Paralinguistic: cough",
    "@sneeze":           "Paralinguistic: sneeze",
    "@throat-clearing":  "Paralinguistic: throat-clearing",
    "@yawn":             "Paralinguistic: yawn",
    "@eating-sounds":    "Paralinguistic: eating sounds",
    "@snore":            "Paralinguistic: snore",
    "@groan":            "Paralinguistic: groan",
    "@sigh":             "Paralinguistic: sigh",
    # Other
    "@silence":       "Other: silence",
    "@unintelligible":"Other: unintelligible",
    "@stutter-block": "Other: stutter block",
}

_SPAN_LABELS = {
    "filler":        "Disfluency: filler",
    "repetition":    "Disfluency: repetition",
    "broken-word":   "Disfluency: broken word",
    "repair":        "Disfluency: repair",
    "false-start":   "Disfluency: false start",
    "prolongation":  "Disfluency: prolongation",
    "crying":        "Paralinguistic: crying",
    "yelling":       "Paralinguistic: yelling",
    "laughing":      "Paralinguistic: laughing",
    "singing":       "Paralinguistic: singing",
    "humming":       "Paralinguistic: humming",
    "whistling":     "Paralinguistic: whistling",
    "whispering":    "Paralinguistic: whispering",
    "emphasis":      "Prosody: emphasis",
    "falling-pitch": "Prosody: falling pitch",
    "raising-pitch": "Prosody: raising pitch",
}

_NER_LABELS = {
    "PER": "Person", "GPE": "Geo Political Entity", "FAC": "Facility",
    "LOC": "Location", "ITEM": "Item", "WOA": "Work of Art",
    "EVENT": "Event", "SPORTS": "Sports", "ORG": "Organization",
    "BRAND": "Brand", "HON": "Honorific", "DATETIME": "Date/Time",
    "MONEY": "Money", "QUANT": "Quantity", "NUM": "Number",
    "LANG": "Language", "LAW": "Law/Policy", "ID": "Identifier",
}


def _esc(text: str) -> str:
    return html_lib.escape(str(text))


# ─── HTML Renderer ────────────────────────────────────────────────────────────

def _build_html(ast, verbatim: bool) -> str:
    parts = []
    speaker_stack = []
    span_stack = []          # list of (tag, tooltip) for open spans

    def close_span():
        if span_stack:
            span_stack.pop()
            parts.append("</span>")

    def close_speaker():
        if speaker_stack:
            speaker_stack.pop()
            parts.append("</div></div>")

    for node in ast:

        # ── plain text
        if isinstance(node, TextNode):
            parts.append(f'<span class="rsml-text">{_esc(node.text)}</span>')

        # ── isolated tag
        elif isinstance(node, IsolatedTagNode):
            tag = node.tag
            tooltip = _ISOLATED_LABELS.get(tag, f"Tag: {tag}")
            parts.append(
                f'<span class="rsml-pill rsml-isolated" title="{_esc(tooltip)}">'
                f'{_esc(tag)}</span>'
            )

        # ── span start
        elif isinstance(node, SpanStartNode):
            tag = node.tag

            if tag.startswith("s") and tag[1:].isdigit():
                n = int(tag[1:])
                div_style, label_style, label_text = _speaker_style(n)
                speaker_stack.append(n)
                parts.append(
                    f'<div class="rsml-speaker" style="{div_style}">'
                    f'<span class="rsml-speaker-label" style="{label_style}">'
                    f'{label_text}:</span><br><div>'
                )
            else:
                tooltip = _SPAN_LABELS.get(tag, f"Span: {tag}")
                css_class = f"rsml-span rsml-span-{tag}"
                span_stack.append(tag)
                parts.append(f'<span class="{css_class}" title="{_esc(tooltip)}">')

        # ── span end
        elif isinstance(node, SpanEndNode):
            tag = node.tag
            if tag.startswith("s") and tag[1:].isdigit():
                close_speaker()
            else:
                close_span()

        # ── bracket node (NER / CODE / ACCENT / NORMAL)
        elif isinstance(node, BracketNode):
            display = _esc(node.verbatim if verbatim else node.normalized)
            subtype = node.subtype or ""

            if node.category == "NER":
                css = "rsml-ner"
                label = f"#{subtype}"
                entity_name = _NER_LABELS.get(subtype, subtype)
                tooltip = f"Named Entity — {entity_name}"
                if not verbatim:
                    tooltip += f" | normalized: {node.normalized}"
            elif node.category == "CODE":
                css = "rsml-code"
                label = f"!{subtype}"
                tooltip = f"Code-mixing — language: {subtype}"
            elif node.category == "ACCENT":
                css = "rsml-accent"
                label = f"${subtype}"
                tooltip = f"Accent variant — {subtype}"
            else:
                css = "rsml-normal"
                label = ""
                tooltip = f"Bracket — verbatim: {node.verbatim} | normalized: {node.normalized}"

            badge = f'<small>{_esc(label)}</small>' if label else ""
            parts.append(
                f'<span class="rsml-pill {css}" title="{_esc(tooltip)}">'
                f'{display}{badge}</span>'
            )

    # Close any unclosed spans / speakers
    while span_stack:
        close_span()
    while speaker_stack:
        close_speaker()

    return "".join(parts)


# ─── Public component ─────────────────────────────────────────────────────────

def render(ast: list):
    st.subheader("Annotated View")

    if not ast:
        st.info("Start typing RSML on the left to see the annotated view here.")
        return

    is_normalized = st.toggle("Normalized", value=True, key="rsml_view_toggle")
    verbatim = not is_normalized

    # Distinct mode banner
    if is_normalized:
        banner_html = (
            '<div style="margin-bottom: 15px;"><div class="rsml-mode-banner norm">'
            '<span class="dot"></span> Showing Normalized text'
            '</div></div>'
        )
    else:
        banner_html = (
            '<div style="margin-bottom: 15px;"><div class="rsml-mode-banner verb">'
            '<span class="dot"></span> Showing Verbatim (spoken) text'
            '</div></div>'
        )

    html_body = _build_html(ast, verbatim)

    st.markdown(
        STYLES
        + f'<div class="rsml-view">{banner_html}{html_body}</div>',
        unsafe_allow_html=True,
    )