import typing as t

class ExpressionParsingConfig(t.NamedTuple):
    SOURCE_LEN_MAX: int
    TOKEN_COUNT_MAX: int
    STR_LEN_MAX: int
