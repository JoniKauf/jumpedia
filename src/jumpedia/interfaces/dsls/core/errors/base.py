from dataclasses import dataclass

lazy from jumpedia.interfaces.dsls.core.errors.eval import AnyEvalErrorT
lazy from jumpedia.interfaces.dsls.core.errors.lex import AnyLexErrorT
lazy from jumpedia.interfaces.dsls.core.errors.parse import AnyParseErrorT

type AnyDslErrorT = AnyEvalErrorT | AnyLexErrorT | AnyParseErrorT


@dataclass()
class DslError(Exception):
    """Base class of all DSL errors."""
