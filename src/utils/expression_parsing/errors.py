import ast
import typing as t


class BaseExpressionParsingError(Exception):
    pass


class GenericVisitError(BaseExpressionParsingError):
    def __init__(self, node: ast.AST) -> None:
        self.node = node
        super().__init__()


class WrongChildError(BaseExpressionParsingError):
    def __init__(
        self, received: ast.AST, expected: type[ast.AST]
    ) -> None:
        self.received = received
        self.expected = expected
        super().__init__()

class NotStrConstantError(BaseExpressionParsingError):
    def __init__(self, value: t.Any) -> None:
        self.value = value
        super().__init__()


class NewlineInSrcError(BaseExpressionParsingError):
    pass

class EmptySrcError(BaseExpressionParsingError):
    pass


class MaxTokenCountExceecedError(BaseExpressionParsingError):
    pass


class MaxSrcLengthExceededError(BaseExpressionParsingError):
    pass


class MaxStringLengthExceededError(BaseExpressionParsingError):
    pass

class ImplicitConcatOfStringsError(BaseExpressionParsingError):
    def __init__(self, left: str, right: str) -> None:
        self.left = left
        self.right = right
        super().__init__()