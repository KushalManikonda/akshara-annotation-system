from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)

import re


class RSMLNormalizer:

    def normalize(self, ast):

        output = []

        for node in ast:

            text = self.normalize_node(node)

            if text:
                output.append(text)

        normalized = "".join(output)

        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove spaces before punctuation
        normalized = re.sub(r"\s+([.,!?;:])", r"\1", normalized)

        return normalized.strip()

    def normalize_node(self, node):

        if isinstance(node, TextNode):
            return node.text

        if isinstance(node, IsolatedTagNode):
            return ""

        if isinstance(node, SpanStartNode):
            return ""

        if isinstance(node, SpanEndNode):
            return ""

        if isinstance(node, BracketNode):
            return node.normalized

        return ""

    