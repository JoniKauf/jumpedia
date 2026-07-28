from dataclasses import dataclass

lazy from interfaces.dsls.core.errors.eval import AnyEvalErrorT
lazy from interfaces.dsls.core.errors.lex import AnyLexErrorT
lazy from interfaces.dsls.core.errors.parse import AnyParseErrorT

type AnyDslErrorT = AnyEvalErrorT | AnyLexErrorT | AnyParseErrorT


@dataclass()
class DslError(Exception):
    """Base class of all DSL errors."""
