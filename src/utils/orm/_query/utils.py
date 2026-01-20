import itertools
import typing as t

from .._structures.column import Column, ColumnBind
from .._structures.model import Model
from .._utils import SqlString, TupleOfOneOrMore
from . import Operator, Order

PLACEHOLDER: str = "?"


def placehold(o: object, params: list[t.Any], left_operator: Operator | None) -> str:
    if isinstance(o, SqlString):
        return str(o)

    if (
        left_operator in {Operator.IN}
        and not isinstance(o, str)
        and isinstance(o, t.Iterable)
    ):
        o = tuple(o)

        if not o:
            # Empty set
            return "(SELECT NULL WHERE 1 != 1)"

        params.extend(o)

        return f"({','.join(itertools.repeat('?', len(o)))})"

    params.append(o)

    return PLACEHOLDER


def handle_where_sql(
    where: list[tuple[tuple[t.Any, Operator, t.Any], ...]],
    parts: list[str],
    params: list[t.Any],
) -> None:
    if where:
        parts.append("WHERE")
        parts.append(
            " OR ".join(
                " AND ".join(
                    f"{placehold(left, params, None)} {comp} {placehold(right, params, comp)}"
                    for left, comp, right in and_where
                )
                for and_where in where
            )
        )


def handle_order_by_sql(
    order_by: tuple[Column[t.Any, t.Any] | tuple[Column[t.Any, t.Any], Order], ...],
    parts: list[str],
) -> None:
    if order_by:
        order_by_fixed = (
            (col_order, Order.ASC) if isinstance(col_order, Column) else col_order
            for col_order in order_by
        )

        parts.append("ORDER BY")
        parts.append(",".join(f"{col} {order}" for col, order in order_by_fixed))


def handle_limit_sql(limit: tuple[int, int] | None, parts: list[str]) -> None:
    if limit is not None:
        parts.append(f"LIMIT {limit[0]}")

        offset = limit[1]

        if offset != 0:
            parts.append(f"OFFSET {offset}")


def get_entire_insert_sql(
    table: type[Model], insert: tuple[tuple[ColumnBind[t.Any, t.Any], ...], bool]
) -> tuple[str, list[t.Any]]:
    parts: list[str] = ["INSERT"]

    cols_binded, ignore = insert

    cols, binded = tuple(zip(*cols_binded))
    cols: tuple[Column[t.Any, t.Any], ...]
    binded: tuple[TupleOfOneOrMore[t.Any], ...]

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
    where: list[tuple[tuple[t.Any, Operator, t.Any], ...]],
    order_by: tuple[Column[t.Any, t.Any] | tuple[Column[t.Any, t.Any], Order], ...],
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
    returning: tuple[Column[t.Any, t.Any], ...], sql: str, params: list[t.Any]
) -> tuple[str, list[t.Any]]:
    return (
        f"{sql} RETURNING {
            '*' if not returning 
            else (','.join(map(str, returning)))
        }",
        params,
    )
