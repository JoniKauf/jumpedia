import re

_PASCAL_REPLACE_PATTERN = re.compile(r'(?!^)([A-Z]+)')

def pascal_to_snake(s: str):
    return re.sub(_PASCAL_REPLACE_PATTERN, r'_\1', s).lower()