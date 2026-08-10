import pytest
from utils.rsml.ast import (
    TextNode,
    IsolatedTagNode,
    SpanStartNode,
    SpanEndNode,
    BracketNode,
)
from utils.rsml.formatter import RSMLFormatter

def test_rsml_formatter():
    formatter = RSMLFormatter()

    ast = [
        TextNode(type="TEXT", text="Hello"),
        IsolatedTagNode(type="ISOLATED", tag="@umm"),
        SpanStartNode(type="SPAN_START", tag="repetition"),
        TextNode(type="TEXT", text="world"),
        SpanEndNode(type="SPAN_END", tag="repetition"),
        BracketNode(type="BRACKET", category="NER", subtype="LOC", verbatim="hyd", normalized="Hyderabad"),
        BracketNode(type="BRACKET", category="CODE", subtype="hi", verbatim="namaste", normalized="namaste"),
        SpanStartNode(type="SPAN_START", tag="s1"),
        TextNode(type="TEXT", text="speaker1"),
        SpanEndNode(type="SPAN_END", tag="s1")
    ]

    expected = "Hello @umm @repetition-start world @repetition-end #LOC[hyd](Hyderabad) !hi[namaste](namaste) &s1-start speaker1 &s1-end"
    result = formatter.format(ast)
    assert result == expected

def test_rsml_formatter_spacing():
    formatter = RSMLFormatter()
    ast = [
        TextNode(type="TEXT", text="  Hello   "),
        IsolatedTagNode(type="ISOLATED", tag="@umm"),
        TextNode(type="TEXT", text="   world  ")
    ]
    expected = "Hello @umm world"
    result = formatter.format(ast)
    assert result == expected
