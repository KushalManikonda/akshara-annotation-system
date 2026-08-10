import re

def is_valid_email(email: str) -> bool:
    """
    Check if the provided email string is a valid email format.
    """
    if not email:
        return False
    email_regex = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    return bool(email_regex.match(email))

def is_not_empty(value: str) -> bool:
    """
    Check if a string value is not empty or just whitespace.
    """
    return bool(value and value.strip())
