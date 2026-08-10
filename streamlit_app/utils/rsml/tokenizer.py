from dataclasses import dataclass


@dataclass
class Token:

    type: str
    value: str
    start: int
    end: int

import re

TOKEN_PATTERN = re.compile(
    r"""
    (@[A-Za-z0-9\-]+)|
    (&[A-Za-z0-9\-]+)|
    (\#[A-Za-z]*\[[^\]]+\]\([^)]+\))|
    (\![A-Za-z]*\[[^\]]+\]\([^)]+\))|
    (\$[A-Za-z\-]*\[[^\]]+\]\([^)]+\))|
    (\[[^\]]+\]\([^)]+\))
    """,
    re.VERBOSE,
)

def tokenize(text):

    tokens = []

    index = 0

    for match in TOKEN_PATTERN.finditer(text):

        if match.start() > index:

            tokens.append(
                Token(
                    "TEXT",
                    text[index:match.start()],
                    index,
                    match.start(),
                )
            )

        tokens.append(

            Token(

                "TAG",

                match.group(),

                match.start(),

                match.end(),

            )

        )

        index = match.end()

    if index < len(text):

        tokens.append(

            Token(

                "TEXT",

                text[index:],

                index,

                len(text),

            )

        )

    return tokens

