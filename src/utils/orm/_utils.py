import string

type TupleOfOneOrMore[T] = tuple[T, *tuple[T, ...]]


class SqlString:
    pass


def validate_identifier(s: str) -> bool:
    if len(s) > 64:
        return False

    GOOD_CHARS = set(string.ascii_letters + string.digits + "_")

    return all(c in GOOD_CHARS for c in s)
