import ast
import typing as t
from ..discord_.errors import FeedbackError
from .errors import InvalidArgumentFeedbackError
from ..utils.argparsing import (ArgParser, DictOfStrToListOfStrVisitor,
                                ListOfTupleVisitor,
                                ListOfStrVisitor)

LIST_PARSER = ArgParser(ListOfStrVisitor())

MAPPING_PARSER = ArgParser(DictOfStrToListOfStrVisitor())


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

    


LIST_OF_NAME_ALIASES_PARSER = ArgParser(ListOfTupleVisitor(
    _handle_name_aliases_tuple
))
