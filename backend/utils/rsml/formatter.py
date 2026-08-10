import re
from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)

class RSMLFormatter:

    def format(self, ast):
        output = []

        for node in ast:
            text = self.format_node(node)
            if text:
                output.append(text)

        # Join the text representations
        formatted = " ".join(output)

        # Collapse multiple spaces
        formatted = re.sub(r"\s+", " ", formatted)

        # Ensure no space before closing punctuation if there was no space originally,
        # but the safest generic format for RSML is just single space between tokens.
        # So stripping is good enough.
        return formatted.strip()

    def format_node(self, node):

        if isinstance(node, TextNode):
            return node.text.strip()

        if isinstance(node, IsolatedTagNode):
            return node.tag

        if isinstance(node, SpanStartNode):
            prefix = "&" if node.tag.startswith("s") and node.tag[1:].isdigit() else "@"
            return f"{prefix}{node.tag}-start"

        if isinstance(node, SpanEndNode):
            prefix = "&" if node.tag.startswith("s") and node.tag[1:].isdigit() else "@"
            return f"{prefix}{node.tag}-end"

        if isinstance(node, BracketNode):
            # Reconstruct bracket string
            prefix = ""
            if node.category == "NER":
                prefix = f"#{node.subtype or ''}"
            elif node.category == "CODE":
                prefix = f"!{node.subtype or ''}"
            elif node.category == "ACCENT":
                prefix = f"${node.subtype or ''}"
            
            return f"{prefix}[{node.verbatim}]({node.normalized})"

        return ""
