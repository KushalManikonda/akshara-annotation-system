from dataclasses import dataclass

from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)

from utils.rsml.constants import (
    SPAN_TAGS,
    NER_TYPES,
    LANGUAGE_CODES,
)


@dataclass
class ValidationMessage:
    level: str
    message: str


class RSMLValidator:

    def validate(self, ast):

        self.messages = []

        self.validate_spans(ast)
        self.validate_ner(ast)
        self.validate_code_mixing(ast)
        self.validate_empty_nodes(ast)
        self.validate_duplicate_isolated(ast)
        self.validate_empty_transcript(ast)

        return self.messages

    def validate_spans(self, ast):

        stack = []

        for node in ast:

            if isinstance(node, SpanStartNode):

                is_speaker = node.tag.startswith("s") and node.tag[1:].isdigit()

                if not is_speaker and node.tag not in SPAN_TAGS:
                    self.messages.append(
                        ValidationMessage(
                            "ERROR",
                            f"Unknown span tag '{node.tag}'"
                        )
                    )

                stack.append(node.tag)

            elif isinstance(node, SpanEndNode):

                if not stack:
                    self.messages.append(
                        ValidationMessage(
                            "ERROR",
                            f"Unexpected closing tag '{node.tag}'"
                        )
                    )
                    continue

                current = stack.pop()

                if current != node.tag:
                    self.messages.append(
                        ValidationMessage(
                            "ERROR",
                            f"Mismatched span '{current}' and '{node.tag}'"
                        )
                    )

        while stack:
            tag = stack.pop()

            self.messages.append(
                ValidationMessage(
                    "ERROR",
                    f"Unclosed span '{tag}'"
                )
            )

    def validate_ner(self, ast):

        for node in ast:

            if not isinstance(node, BracketNode):
                continue

            if node.category != "NER":
                continue

            if node.subtype is None:

                self.messages.append(
                    ValidationMessage(
                        "ERROR",
                        "NER annotation missing entity type."
                    )
                )

                continue

            if node.subtype not in NER_TYPES:

                self.messages.append(
                    ValidationMessage(
                        "ERROR",
                        f"Invalid NER type '{node.subtype}'"
                    )
                )

    def validate_code_mixing(self, ast):

        for node in ast:

            if not isinstance(node, BracketNode):
                continue

            if node.category != "CODE":
                continue

            if node.subtype is None:
                self.messages.append(
                    ValidationMessage(
                        "ERROR",
                        "Code-mixing annotation missing language code."
                    )
                )
                continue

            if node.subtype not in LANGUAGE_CODES:
                self.messages.append(
                    ValidationMessage(
                        "ERROR",
                        f"Invalid language code '{node.subtype}'"
                    )
                )

    def validate_empty_nodes(self, ast):

        for node in ast:

            if not isinstance(node, BracketNode):
                continue

            if node.verbatim.strip() == "":
                self.messages.append(
                    ValidationMessage(
                        "WARNING",
                        "Empty verbatim text."
                    )
                )

            if node.normalized.strip() == "":
                self.messages.append(
                    ValidationMessage(
                        "WARNING",
                        "Empty normalized text."
                    )
                )

    def validate_duplicate_isolated(self, ast):

        previous = None

        for node in ast:

            if not isinstance(node, IsolatedTagNode):
                previous = None
                continue

            if previous == node.tag:
                self.messages.append(
                    ValidationMessage(
                        "WARNING",
                        f"Repeated isolated tag '{node.tag}'"
                    )
                )

            previous = node.tag

    def validate_empty_transcript(self, ast):

        has_text_or_tag = any(
            (isinstance(node, TextNode) and node.text.strip()) or
            isinstance(node, (IsolatedTagNode, SpanStartNode, SpanEndNode, BracketNode))
            for node in ast
        )

        if not has_text_or_tag:
            self.messages.append(
                ValidationMessage(
                    "ERROR",
                    "Transcript contains no text or tags."
                )
            )