import typing as t

from .._utils import TagSafeSqlStr, TupleOfOneOrMore
from . import Operator, Order

if t.TYPE_CHECKING:
    from .._structures.column import Column, ColumnBindedMany
    from .._structures.model import Model

PLACEHOLDER: str = "?"


def placehold(o: object, params: list[t.Any]) -> str:
    if isinstance(o, TagSafeSqlStr):
        return str(o)

    params.append(o)
    return PLACEHOLDER


def handle_where_sql(
    where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None,
    parts: list[str],
    params: list[t.Any],
) -> None:
    if where is not None:
        parts.append("WHERE")
        parts.append(
            " AND ".join(
                f"{placehold(left, params)} {comp} {placehold(right, params)}"
                for left, comp, right in where
            )
        )


def handle_order_by_sql(
    order_by: TupleOfOneOrMore[tuple[Column[t.Any], Order]] | None, parts: list[str]
) -> None:
    if order_by is not None:
        parts.append("ORDER BY")
        parts.append(",".join(f"{col} {order}" for col, order in order_by))


def handle_limit_sql(limit: tuple[int, int] | None, parts: list[str]) -> None:
    if limit is not None:
        parts.append(f"LIMIT {limit[0]}")

        offset = limit[1]

        if offset != 0:
            parts.append(f"OFFSET {offset}")


def get_entire_insert_sql(
    table: type[Model], insert: tuple[TupleOfOneOrMore[ColumnBindedMany], bool]
) -> tuple[str, list[t.Any]]:
    parts: list[str] = ["INSERT"]

    cols_binded, ignore = insert

    cols, binded = tuple(zip(*cols_binded))
    cols: TupleOfOneOrMore[Column[t.Any]]
    binded: TupleOfOneOrMore[TupleOfOneOrMore[t.Any]]

    if ignore:
        parts.append("IGNORE")

    parts.append(str(table))

    parts.append(f"({','.join(map(str, cols))})")
    parts.append("VALUES")

    rows = list(zip(*binded, strict=True))

    parts.append(f"({','.join(PLACEHOLDER for _ in rows[0])})")

    return (" ".join(parts), rows)


def get_entire_delete_sql(
    table: type[Model],
    delete: bool,
    where: TupleOfOneOrMore[tuple[t.Any, Operator, t.Any]] | None,
    order_by: TupleOfOneOrMore[tuple[Column[t.Any], Order]] | None,
    limit: tuple[int, int] | None,
) -> tuple[str, list[t.Any]]:
    params: list[t.Any] = []
    parts: list[str] = ["DELETE"]

    if delete:
        parts.append("IGNORE")

    parts.append("FROM")
    parts.append(str(table))

    handle_where_sql(where, parts, params)

    handle_order_by_sql(order_by, parts)

    handle_limit_sql(limit, parts)

    return (" ".join(parts), params)


def get_added_returning_sql(
    returning: TupleOfOneOrMore[Column[t.Any]], sql: str, params: list[t.Any]
) -> tuple[str, list[t.Any]]:
    return (f"{sql} RETURNING {','.join(map(str, returning))}", params)


__all__ = []
