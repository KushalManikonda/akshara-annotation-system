import re

from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)

from utils.rsml.constants import ISOLATED_TAGS

BRACKET_PATTERN = re.compile(
    r'([!#$]?)([A-Za-z\-]*)?\[([^\]]+)\]\(([^)]+)\)'
)

class RSMLParser:

    def parse(self, tokens):

        ast = []

        for token in tokens:
            ast.append(self.parse_token(token))

        return ast

    def parse_token(self, token):

        if token.type == "TEXT":
            return TextNode(
                type="TEXT",
                text=token.value,
            )

        value = token.value

        if value in ISOLATED_TAGS:
            return IsolatedTagNode(
                type="ISOLATED",
                tag=value,
            )

        if value.endswith("-start"):
            return SpanStartNode(
                type="SPAN_START",
                tag=value[1:-6],
            )

        if value.endswith("-end"):
            return SpanEndNode(
                type="SPAN_END",
                tag=value[1:-4],
            )

        match = BRACKET_PATTERN.fullmatch(value)

        if match:

            prefix = match.group(1)

            subtype = match.group(2) or None

            verbatim = match.group(3)

            normalized = match.group(4)

            category = "NORMAL"

            if prefix == "!":
                category = "CODE"

            elif prefix == "#":
                category = "NER"

            elif prefix == "$":
                category = "ACCENT"

            return BracketNode(
                type="BRACKET",
                category=category,
                subtype=subtype,
                verbatim=verbatim,
                normalized=normalized,
            )

        raise ValueError(
            f"Unknown RSML token: {token.value}"
        )