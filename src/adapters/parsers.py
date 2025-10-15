import ast
import typing as t
from src.discord_.errors import FeedbackError
from src.adapters.errors import InvalidArgumentFeedbackError
from src.utils.expression_parsing.parser import ExpressionParser, ExpressionParserConfig
from src.utils.expression_parsing.visitor import ListOfStrVisitor, ListOfTupleVisitor, DictOfStrToListOfStrVisitor, ExpressionVisitorConfig, BaseExpressionVisitor
from structures.task import Task

_KIBIBYTE = 2 ** 10

_CONFIG_PARSER = ExpressionParserConfig(_KIBIBYTE * _KIBIBYTE * 2, _KIBIBYTE * 4)
_CONFIG_VISITOR = ExpressionVisitorConfig(255)

LIST_PARSER = ExpressionParser(ListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER)
MAPPING_PARSER = ExpressionParser(DictOfStrToListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER)


def _handle_name_aliases_tuple(tup: ast.Tuple, visitor: ListOfTupleVisitor) -> tuple[str, list[str]]:
    ADDITIONAL = (
        t"The tuple should have 2 elements in this order:\n"
        t"1. The value (a string)\n"
        t"2. The aliases (a list of strings)"
    )

    if len(tup.elts) != 2:
        raise InvalidArgumentFeedbackError(
            t"A tuple of length {len(tup.elts)} is invalid!",
            additional=ADDITIONAL
        )
    
    first, second = tup.elts

    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        raise InvalidArgumentFeedbackError(
            t"The first element of the tuple is not a string!",
            additional=ADDITIONAL
        )
    
    elts: list[str] = []
    valid: bool = True

    if not isinstance(second, ast.List):
        valid = False
    else:
        for elem in second.elts:
            if not isinstance(elem, ast.Constant) or not isinstance(elem.value, str):
                valid = False
                break

            elts.append(elem.value)

    if not valid:
        raise InvalidArgumentFeedbackError(
            t"The second element of the tuple is not a list of strings!",
            additional=ADDITIONAL
        )
    
    return (first.value, elts)

    
LIST_OF_NAME_ALIASES_PARSER = ExpressionParser(ListOfTupleVisitor(_handle_name_aliases_tuple, config=_CONFIG_VISITOR), config=_CONFIG_PARSER)

    
class FilterVisitor(BaseExpressionVisitor[list[ast.AST]], body_type=ast.BoolOp):
    def __init__(self, tasks: list[Task], *, config: ExpressionVisitorConfig) -> None:
        self.tasks = tasks
        super().__init__(config=config)
 
    def visit_Constant(self, node: ast.Constant) -> t.Any:
        print("const")
    
    def visit_BoolOp(self, node: ast.BoolOp) -> t.Any:
        if isinstance(node)
    