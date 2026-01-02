import ast
import typing as t


class BaseExpressionParsingError(Exception):
    pass


class GenericVisitError(BaseExpressionParsingError):
    def __init__(self, node: ast.AST) -> None:
        self.node = node
        super().__init__()


class WrongVisitError(BaseExpressionParsingError):
    def __init__(
        self,
        received: ast.AST | None,
        expected: type[ast.AST] | tuple[type[ast.AST], ...] | None,
    ) -> None:
        self.received = received
        self.expected = expected
        super().__init__()


class NewlineInSrcError(BaseExpressionParsingError):
    pass


class EmptySrcError(BaseExpressionParsingError):
    pass


class MaxTokenCountExceecedError(BaseExpressionParsingError):
    pass


class MaxSrcLengthExceededError(BaseExpressionParsingError):
    pass

class ImplicitConcatOfStringsError(BaseExpressionParsingError):
    def __init__(self, left: str, right: str) -> None:
        self.left = left
        self.right = right
        super().__init__()
