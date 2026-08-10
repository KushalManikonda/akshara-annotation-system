from dataclasses import dataclass
from typing import Optional


@dataclass
class RSMLNode:
    type: str


@dataclass
class TextNode(RSMLNode):
    text: str


@dataclass
class IsolatedTagNode(RSMLNode):
    tag: str


@dataclass
class SpanStartNode(RSMLNode):
    tag: str


@dataclass
class SpanEndNode(RSMLNode):
    tag: str


@dataclass
class BracketNode(RSMLNode):
    category: str
    subtype: Optional[str]
    verbatim: str
    normalized: str