import abc
import ast
import enum
import functools
import io
import itertools
import keyword
import re
import tokenize as tok
import typing as t
from types import EllipsisType, MappingProxyType

from discord_.errors import FeedbackError
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.errors import CollectionEntryNotFoundError
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AnyAttributeValueMappingT,
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from utils import text
from utils.expression_parsing import errors as ep_errors
from utils.expression_parsing.errors import WrongVisitError
from utils.expression_parsing.parser import ExpressionParser, ExpressionParserConfig
from utils.expression_parsing.visitor import (
    BaseExpressionVisitor,
    ExpressionVisitorConfig,
)
from utils.text import NormStr, RealStr

from . import errors

type FilterAvmCollectionT = dict[int, dict[NormStr, frozenset[SlotTypeT]]]
type FilterAttributesT = dict[NormStr, AnyAttributeT]


_CHILD_TYPE_TO_STR: dict[type[ast.expr], str] = {
    ast.Constant: "string",
    ast.List: "list",
    ast.Tuple: "tuple",
    ast.Dict: "mapping",
}


def validate_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T] | tuple[type[T], ...]
) -> tuple[T, ...]:
    ch = tuple(children)

    if child_type is not ast.AST:
        for child in ch:
            if not isinstance(child, child_type):
                raise WrongVisitError(child, child_type)

    return ch  # type: ignore


@t.overload
def visit_string_like_and_validate(
    node: ast.AST,
    visitor: BaseExpressionVisitor,
    none_as_obj: t.Literal[False] = ...,
    ellipsis_as_obj: t.Literal[False] = ...,
) -> str:
    pass


@t.overload
def visit_string_like_and_validate(
    node: ast.AST,
    visitor: BaseExpressionVisitor,
    none_as_obj: t.Literal[False],
    ellipsis_as_obj: t.Literal[True],
) -> str | EllipsisType:
    pass


@t.overload
def visit_string_like_and_validate(
    node: ast.AST,
    visitor: BaseExpressionVisitor,
    none_as_obj: t.Literal[True],
    ellipsis_as_obj: t.Literal[False],
) -> str | None:
    pass


@t.overload
def visit_string_like_and_validate(
    node: ast.AST,
    visitor: BaseExpressionVisitor,
    none_as_obj: t.Literal[True],
    ellipsis_as_obj: t.Literal[True],
) -> str | None | EllipsisType:
    pass


_PYTHON_KEYWORDS = frozenset(keyword.kwlist) | frozenset(keyword.softkwlist)
_PYTHON_KEYWORD_CHARS: t.Final[str] = "".join(c for kw in _PYTHON_KEYWORDS for c in kw)
_ANY_NON_KEYWORD_CHAR_PATTERN_PLUS_SPACE: t.Final[re.Pattern] = re.compile(
    f"[^ {re.escape(_PYTHON_KEYWORD_CHARS)}]"
)


def visit_string_like_and_validate(
    node: ast.AST,
    visitor: BaseExpressionVisitor,
    none_as_obj: bool = False,
    ellipsis_as_obj: bool = False,
) -> str | None | EllipsisType:
    s: str

    if isinstance(node, ast.Name):
        s = node.id

    elif isinstance(node, ast.Constant):
        if node.value is None:
            if none_as_obj:
                return None

            s = str(None)

        elif node.value is Ellipsis:
            if ellipsis_as_obj:
                return Ellipsis

            s = str(Ellipsis)

        # Float is not allowed because it loses precision
        elif isinstance(node.value, str | bool | int):
            s = str(node.value)

        else:
            raise ep_errors.WrongVisitError(None, None)

    else:
        raise ep_errors.WrongVisitError(node, None)

    if not isinstance(s, str):
        raise FeedbackError(
            "String Expected",
            t'Expected a value that represents a string (`"text wrapped in quotes"`), but received `{s}` instead!',
        )

    if len(s) > visitor.config.STR_LEN_MAX:
        raise FeedbackError(
            "String Length Hard Limit Reached",
            t"The string `{text.shorten(s)}` of length `{len(s)}` has surpassed the hard limit of `{visitor.config.STR_LEN_MAX}` characters!",
        )

    return s


def visit_List_and_validate_children(
    node: ast.List, visitor: BaseExpressionVisitor, elts_type: type[ast.expr]
) -> list:
    elts = validate_children_type(node.elts, elts_type)
    return [visitor.visit(n) for n in elts]


def _pre_process_general(
    s: str, parser: ExpressionParser
) -> tuple[str, list[tok.TokenInfo]]:
    s = s.replace("\r\n", " ").replace("\n", " ")

    tokens: list[tok.TokenInfo] = []

    count: int = 0
    prev_token: tok.TokenInfo | None = None

    for token in tok.tokenize(io.BytesIO(s.encode("utf-8")).readline):
        count += 1

        if count > parser.config.TOKEN_COUNT_MAX:
            raise ep_errors.MaxTokenCountExceededError()

        # Disallow inplicit string concat
        if (
            prev_token is not None
            and prev_token.type == tok.STRING
            and token.type == tok.STRING
        ):
            raise ep_errors.ImplicitConcatOfStringsError(
                prev_token.string, token.string
            )

        if token.type == tok.NUMBER:
            tokens.append(
                tok.TokenInfo(
                    token.type, f'"{token.string}"', (-1, -1), (-1, -1), ""
                )
            )
        else:
            tokens.append(token)

    return tok.untokenize((token.type, token.string) for token in tokens), list(
        token for token in tokens if token.string.strip()
    )


def _valid_string_like_token(token: tok.TokenInfo) -> bool:
    if token in (tok.NAME, tok.STRING):
        return True

    if token.type == tok.OP and token.string == "...":
        return True

    return False


_KIBIBYTE = 2**10
_CONFIG_PARSER_PRESET = (_KIBIBYTE * _KIBIBYTE * 2, _KIBIBYTE * 4)

_DEFAULT_CONFIG_PARSER = ExpressionParserConfig(
    *_CONFIG_PARSER_PRESET, lambda s, p: _pre_process_general(s, p)[0]
)
_DEFAULT_CONFIG_VISITOR = ExpressionVisitorConfig(255)


_OP_TO_FUNC: t.Final[
    dict[type[ast.AST], t.Callable[[frozenset[SlotTypeT], SlotTypeT], bool]]
] = {
    ast.Is: lambda tav, v: v in tav,
    ast.IsNot: lambda tav, v: v not in tav,
    ast.Lt: lambda tav, v: any(
        s < v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.LtE: lambda tav, v: any(
        s <= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.Gt: lambda tav, v: any(
        s > v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.GtE: lambda tav, v: any(
        s >= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
}

_ORDER_OPS: t.Final[frozenset[type[ast.AST]]] = frozenset(
    (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
)


class FilterVisitor[T: AttributeValueMapping | UserAttributeValueMapping](
    BaseExpressionVisitor[
        list[T],
        [t.Iterable[T], dict[NormStr, AnyAttributeT], set[AnyAttributeT]],
    ],
    body_type=(ast.BoolOp, ast.Compare),
):
    def start_visit(
        self,
        node: ast.AST,
        avms: t.Iterable[T],
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> list[T]:
        attribute_value_mappings: dict[int, T] = {id(avm): avm for avm in avms}

        favmc: FilterAvmCollectionT = {
            id(avm): {
                attr.norm_name: frozenset(attr.slot_type(NormStr(slot)) for slot in val)
                for attr, val in avm.combined.items()
            }
            for avm in attribute_value_mappings.values()
        }

        result: FilterAvmCollectionT = super().visit(
            node, favmc, attributes, used_attributes
        )

        return list(attribute_value_mappings[id] for id in result)

    def visit_BoolOp(
        self,
        node: ast.BoolOp,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        assert isinstance(node.op, ast.And | ast.Or)

        values = validate_children_type(node.values, (ast.Compare, ast.BoolOp))

        favmc = favmc.copy()

        if isinstance(node.op, ast.Or):
            remaining_to_check = favmc
            result: dict[int, dict[NormStr, frozenset[SlotTypeT]]] = {}

            for v in values:
                if not remaining_to_check:
                    break

                checked_successfully: FilterAvmCollectionT = self.visit(
                    v, remaining_to_check, attributes, used_attributes
                )

                for k in checked_successfully:
                    remaining_to_check.pop(k, None)

                result |= checked_successfully

            return result

        if isinstance(node.op, ast.And):
            for v in values:
                if not favmc:
                    break

                checked_successfully: FilterAvmCollectionT = self.visit(
                    v, favmc, attributes, used_attributes
                )
                favmc = {k: v for k, v in favmc.items() if k in checked_successfully}

            return favmc

        t.assert_never(node.op)

    def visit_Compare(
        self,
        node: ast.Compare,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        if len(node.ops) > 1:
            raise ep_errors.WrongVisitError(node.ops[1], None)

        op = node.ops[0]

        op_func = _OP_TO_FUNC.get(op.__class__)

        if op_func is None:
            raise ep_errors.WrongVisitError(op_func, tuple(_OP_TO_FUNC))

        left, right = node.left, node.comparators[0]

        LEFT_RIGHT_TYPE = (ast.Constant, ast.Name)

        if not isinstance(left, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(left, LEFT_RIGHT_TYPE)

        if not isinstance(right, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(right, LEFT_RIGHT_TYPE)

        attr_syn: NormStr = self.visit(left, True, op)
        attr = attributes.get(attr_syn)

        if attr is None:
            raise errors.StructureNotFoundViaSynFeedbackError(
                attr_syn, BaseAttribute, False
            )

        used_attributes.add(attr)

        attr_name: NormStr = attr.norm_name
        value_str_real: RealStr | EllipsisType = self.visit(right, False, op)

        if value_str_real is Ellipsis:
            MUST_BE_EMPTY = isinstance(op, ast.Is)

            return {
                i: tav
                for i, tav in favmc.items()
                if (not tav.get(attr_name)) is MUST_BE_EMPTY
            }

        value_str_norm = NormStr(value_str_real)

        collection = attr.get_collection()

        if collection:
            try:
                entry = collection.get_entry_by_syn(value_str_norm)
            except KeyError:
                raise errors.CollectionEntryNotFoundFeedbackError(
                    CollectionEntryNotFoundError(value_str_real, collection)
                )

            return {
                i: tav
                for i, tav in favmc.items()
                if op_func(
                    frozenset(
                        collection.get_entry_by_syn(slot).collection_index
                        for slot in tav.get(attr_name, frozenset())
                    ),
                    entry.collection_index,
                )
            }

        value = attr.slot_type(value_str_norm)

        return {
            i: tav
            for i, tav in favmc.items()
            if op_func(tav.get(attr_name, frozenset()), value)
        }

    def visit_Name(self, node: ast.Name, attr: bool, op: ast.cmpop) -> t.Any:
        return self.visit_Constant(ast.Constant(node.id), attr, op)

    def visit_Constant(self, node: ast.Constant, attr: bool, op: ast.cmpop) -> t.Any:
        if not attr and op not in _ORDER_OPS and node.value is Ellipsis:
            return node.value

        return RealStr(visit_string_like_and_validate(node, self))


def sort[T: AttributeValueMapping | UserAttributeValueMapping](
    avms: t.Iterable[T], sorts: t.Iterable[tuple[AnyAttributeT, bool]]
) -> list[T]:
    # Remove duplicates while preserving order
    seen_attrs: set[AnyAttributeT] = set()
    sorts_unique: list[tuple[AnyAttributeT, bool]] = []

    for sort in sorts:
        attr, _ = sort

        if attr in seen_attrs:
            continue

        seen_attrs.add(attr)
        sorts_unique.append(sort)

    del seen_attrs, sorts

    attr_to_coll: dict[AnyAttributeT, Collection] = {
        attr: attr.get_collection() for attr, _ in sorts_unique
    }
    task_to_sort_value: dict[Task, list[tuple[t.Any, ...]]] = {}

    for avm in avms:
        result: list[tuple[t.Any, ...]] = []

        for attr, _ in sorts_unique:
            coll = attr_to_coll[attr]

            if coll:
                result.append(
                    tuple(
                        coll.get_entry_by_syn(NormStr(slot)).id
                        for slot in avm.combined.get(attr, ())
                    )
                )
            else:
                result.append(
                    tuple(
                        attr.slot_type(NormStr(slot))
                        for slot in avm.combined.get(attr, ())
                    )
                )

        task_to_sort_value[avm.task] = result

    def cmp_key(a: T, b: T) -> int:
        values_a = task_to_sort_value[a.task]
        values_b = task_to_sort_value[b.task]

        for va, vb, (_, asc) in zip(values_a, values_b, sorts_unique):
            if va < vb:
                return -1 if asc else 1

            if va > vb:
                return 1 if asc else -1

        return 0

    return sorted(avms, key=functools.cmp_to_key(cmp_key))  # type: ignore


class SortVisitor[T: AttributeValueMapping | UserAttributeValueMapping](
    BaseExpressionVisitor[
        list[T], [t.Iterable[T], dict[NormStr, AnyAttributeT], set[AnyAttributeT]]
    ],
    body_type=(ast.UnaryOp, ast.BinOp),
):
    def start_visit(
        self,
        node: ast.AST,
        avms: t.Iterable[T],
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> list[T]:
        assert isinstance(node, ast.Expression)

        sorts: tuple[tuple[AnyAttributeT, bool], ...] = self.visit(
            node, attributes, used_attributes
        )

        return sort(avms, sorts)

    def visit_UnaryOp(
        self,
        node: ast.UnaryOp,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ):
        if not isinstance(node.op, ast.USub | ast.UAdd):
            raise ep_errors.WrongVisitError(node, ast.USub)

        if not isinstance(node.operand, ast.Name | ast.Constant):
            raise ep_errors.WrongVisitError(node, (ast.Name, ast.Constant))

        return (
            (
                self._handle_expected_string_like(node.operand, attributes, used_attributes),
                isinstance(node.op, ast.UAdd),
            ),
        )

    def visit_BinOp(
        self,
        node: ast.BinOp,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ):
        if not isinstance(node.left, ast.BinOp | ast.UnaryOp):
            raise ep_errors.WrongVisitError(node, (ast.BinOp, ast.UnaryOp))

        if not isinstance(node.op, ast.Sub | ast.Add):
            raise ep_errors.WrongVisitError(node, ast.USub)

        if not isinstance(node.right, ast.Name | ast.Constant):
            raise ep_errors.WrongVisitError(node, ast.BinOp)

        return (
            *self.visit(node.left, attributes, used_attributes),
            (
                self._handle_expected_string_like(node.right, attributes, used_attributes),
                isinstance(node.op, ast.Add),
            ),
        )

    def _handle_expected_string_like(self, 
        node: ast.AST, 
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT]
    ):
        attr_syn = NormStr(visit_string_like_and_validate(node, self))
        attr = attributes.get(attr_syn)

        if attr is None:
            raise errors.StructureNotFoundViaSynFeedbackError(
                attr_syn, BaseAttribute, False
            )

        used_attributes.add(attr)

        return attr

def _pre_process_aliases(s: str, parser: ExpressionParser) -> str:
    s, tokens = _pre_process_general(s, parser)

    for tok in tokens:
        if tok.type not in (tok.STRING, tok.NAME):
            raise SyntaxError()

    return f"[{','.join(token.string for token in tokens)}]"


class AliasVisitor(BaseExpressionVisitor[list[str], []], body_type=ast.List):
    def visit_List(self, node: ast.List) -> t.Any:
        return [
            visit_string_like_and_validate(n, self) for n in node.elts
        ]


class _SynState(enum.Enum):
    AFTER_CLOSING_TUPLE = enum.auto()
    AFTER_OPENING_TUPLE = enum.auto()
    AFTER_NAME = enum.auto()
    AFTER_OPENING_LIST = enum.auto()
    AFTER_CLOSING_LIST = enum.auto()


"(name [alias1 alias2 alias3])"


def _pre_process_list_of_name_and_aliases(s: str, parser: ExpressionParser) -> str:
    s, tokens = _pre_process_general(s, parser)

    final_list: list[tuple[str, list[str]]] = []
    state: _SynState = _SynState.AFTER_CLOSING_TUPLE
    name: str = ""
    aliases: list[str] = []

    for token in tokens:
        if state is _SynState.AFTER_CLOSING_TUPLE:
            if token.type != tok.OP or token.string != "(":
                raise SyntaxError()

            assert not name
            assert not aliases

            state = _SynState.AFTER_OPENING_TUPLE

        elif state is _SynState.AFTER_OPENING_TUPLE:
            if not _valid_string_like_token(token):
                raise SyntaxError()

            name = token.string
            state = _SynState.AFTER_NAME

        elif state is _SynState.AFTER_NAME:
            if token.type != tok.OP or token.string != "[":
                raise SyntaxError()

            state = _SynState.AFTER_OPENING_LIST

        elif state is _SynState.AFTER_OPENING_LIST:
            if _valid_string_like_token(token):
                aliases.append(token.string)

            elif token.type == tok.OP and token.string == "]":
                state = _SynState.AFTER_CLOSING_LIST

            else:
                raise SyntaxError()

        elif state is _SynState.AFTER_CLOSING_LIST:
            if token.type != tok.OP or token.string != ")":
                raise SyntaxError()

            final_list.append((name, aliases))
            name = ""
            aliases = []

            state = _SynState.AFTER_CLOSING_TUPLE

    if state is not _SynState.AFTER_CLOSING_TUPLE:
        raise SyntaxError()

    return repr(final_list)


class ListOfNameAndAliasVisitor(
    BaseExpressionVisitor[list[tuple[str, tuple[str, ...]]], []], body_type=ast.List
):
    def visit_List(self, node: ast.List) -> t.Any:
        return visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        if len(node.elts) != 2:
            raise errors.InvalidArgumentFeedbackError(
                t"A specified tuple that must be of length **2** has the length **{len(node.elts)}**!"
            )

        first, second = node.elts

        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            raise errors.InvalidArgumentFeedbackError(
                t"The first element of a specified tuple is not a string, when it actually should be!"
            )

        elts: list[str] = []
        valid: bool = True

        if not isinstance(second, ast.List):
            valid = False
        else:
            for elem in second.elts:
                try:
                    s = visit_string_like_and_validate(elem, self)
                except WrongVisitError:
                    valid = False
                    break

                elts.append(s)

        if not valid:
            raise errors.InvalidArgumentFeedbackError(
                t"The second element of a tuple is not a list of strings, when it should be!"
            )

        return (first.value, elts)


class _AvmState(enum.Enum):
    AFTER_VALUE = enum.auto()
    AFTER_KEY = enum.auto()
    AFTER_COLON = enum.auto()


def _pre_process_avm(s: str, parser: ExpressionParser) -> str:
    s, tokens = _pre_process_general(s, parser)

    state: _AvmState = _AvmState.AFTER_VALUE
    final_dict: dict[str, str] = {}
    k: str = ""

    for token in tokens:
        if state is _AvmState.AFTER_VALUE:
            if not _valid_string_like_token(token):
                raise SyntaxError()

            assert not k

            k = token.string
            state = _AvmState.AFTER_KEY

        elif state is _AvmState.AFTER_KEY:
            if token.type != tok.OP or token != "=":
                raise SyntaxError()

            state = _AvmState.AFTER_COLON

        elif state is _AvmState.AFTER_COLON:
            if not _valid_string_like_token(token):
                raise SyntaxError()

            assert k

            final_dict[k] = token.string
            k = ""
            state = _AvmState.AFTER_VALUE

    if state is not _AvmState.AFTER_VALUE:
        raise SyntaxError()

    return repr(final_dict)


class AttributeValueMappingVisitor(
    BaseExpressionVisitor[
        dict[AnyAttributeT, tuple[SlotStr, ...]], [dict[NormStr, AnyAttributeT]]
    ],
    body_type=ast.Dict,
):
    def visit_Dict(self, node: ast.Dict, attributes: dict[str, AnyAttributeT]) -> t.Any:
        if None in node.keys:
            raise ep_errors.WrongVisitError(None, None)

        key_nodes = t.cast(list[ast.expr], node.keys)
        value_nodes = node.values

        keys = list(visit_string_like_and_validate(n, self) for n in key_nodes)
        values: list[list[str]] = []

        for n in value_nodes:
            mapped_nodes: list[list[ast.expr]] = []

            if isinstance(n, ast.List):
                mapped_nodes.append(n.elts)
            else:
                mapped_nodes.append([n])

            for nodes in mapped_nodes:
                values.append(
                    list(visit_string_like_and_validate(n, self) for n in nodes)
                )

        del key_nodes, value_nodes

        result: dict[AnyAttributeT, tuple[SlotStr, ...]] = {}
        used_syns: dict[AnyAttributeT, RealStr] = {}

        for k_raw, v_raw in zip(keys, values):
            k_real = RealStr(k_raw)
            attr = attributes.get(NormStr(k_real))

            if attr is None:
                raise errors.StructureNotFoundViaSynFeedbackError(k_real, BaseAttribute)

            if attr in result:
                raise FeedbackError(
                    "Not Unique Key Error",
                    t"The attribute `{attr.name}` was specified multiple times as a key!",
                    additional=t"It is both specified by `{k_real}` and `{used_syns[attr]}`.",
                )

            used_syns[attr] = k_real
            result[attr] = attr.real_to_slot_value(tuple(map(RealStr, v_raw)))

        return result


# class DictOfStrToListOfTupleVisitor[T: tuple](
#     BaseExpressionVisitor[dict[str, list[T]], []], body_type=ast.Dict
# ):
#     def start_visit(self, node: ast.AST) -> dict[str, list[T]]:
#         return self.visit(node)

#     def __init__(
#         self,
#         handle_tuple: t.Callable[[ast.Tuple, t.Self], T],
#         *,
#         config: ExpressionVisitorConfig,
#     ) -> None:
#         self._handle_tuple = handle_tuple
#         super().__init__(config=config)

#     def visit_Dict(self, node: ast.Dict) -> t.Any:
#         return visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
#             node, self
#         )

#     def visit_List(self, node: ast.List) -> t.Any:
#         return visit_List_and_validate_children(node, self, ast.Tuple)

#     def visit_Tuple(self, node: ast.Tuple) -> t.Any:
#         return self._handle_tuple(node, self)

#     def visit_Constant(self, node: ast.Constant) -> t.Any:
#         return visit_string_like_and_validate(node, self)


FILTER_PARSER = ExpressionParser(
    FilterVisitor(config=_DEFAULT_CONFIG_VISITOR), config=_DEFAULT_CONFIG_PARSER
)

SORT_PARSER = ExpressionParser(
    SortVisitor(config=_DEFAULT_CONFIG_VISITOR), config=_DEFAULT_CONFIG_PARSER
)


ALIAS_PARSER = ExpressionParser(
    AliasVisitor(config=_DEFAULT_CONFIG_VISITOR),
    config=ExpressionParserConfig(*_CONFIG_PARSER_PRESET, _pre_process_aliases),
)


ATTRIBUTE_VALUE_MAPPING_PARSER = ExpressionParser(
    AttributeValueMappingVisitor(config=_DEFAULT_CONFIG_VISITOR),
    config=ExpressionParserConfig(*_CONFIG_PARSER_PRESET, _pre_process_avm),
)


LIST_OF_NAME_ALIASES_PARSER = ExpressionParser(
    ListOfNameAndAliasVisitor(config=_DEFAULT_CONFIG_VISITOR),
    config=_DEFAULT_CONFIG_PARSER,
)


class TokenParserConfig(t.NamedTuple):
    max_tokens: int
    max_length: int


class BaseAdvancedParser[T, **P](abc.ABC):
    def __init__(self, config: TokenParserConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def parse(self, s: str, *args: P.args, **kwargs: P.kwargs) -> T:
        pass


class State(enum.Enum):
    ATTR = enum.auto()
    OP = enum.auto()
    VALUE = enum.auto()
    BOOL_OP = enum.auto()

class FilterTokenParser(BaseAdvancedParser[str, [AttributeValueMapping, dict[NormStr, AnyAttributeT]]]):
    

    
    def parse(self, s: str, avm: AttributeValueMapping, syn_to_attr: dict[NormStr, AnyAttributeT]) -> str:
        state: State = State.ATTR
        count: int = 0

        for token in tok.tokenize(io.BytesIO().readline):
            count += 1

            if not token.string.strip():
                continue

            if state is State.ATTR:
                pass
            
            

        

            

                