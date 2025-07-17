
from database import queries
from database.simple_orm import BaseRow, Cell, Rows, cell_body
from database import simple_orm

class SchemaFetchResult(BaseRow):
    @Cell
    def table_name(self_or_cls) -> str: cell_body()

    @Cell
    def column_name(self_or_cls) -> str: cell_body()

def _generate_typed() -> None:
    with queries.connected() as (_, cursor):
        cursor.execute(f"""
            SELECT
                t.TABLE_NAME AS {SchemaFetchResult.table_name},
                c.COLUMN_NAME AS {SchemaFetchResult.column_name}
            FROM
                information_schema.TABLES t
            JOIN
                information_schema.COLUMNS c
            ON
                t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
            WHERE
                t.TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys') -- Exclude system databases
        """)

        rows = Rows(cursor.fetchall(), SchemaFetchResult)
    
    result: list[str] = [
        _get_module(),
        _get_buildstones_class()
    ]

    table_columns: dict[str, list[str]] = {}

    for row in rows:
        table
        table_columns.setdefault(row.table_name, []).append(row.column_name)

    

    for tbl, columns in table_columns.items():
        pass
    
def ind(s: str, n: int) -> str:
    return s.rjust(n, " ")

def _get_module() -> str:
    module_path = simple_orm.__name__.split('.')

    if len(module_path) == 1:
        return module_path[0]
    
    return f"from {'.'.join(module_path[:-1])} import {module_path[-1]}"

def _get_buildstones_class(table_columns: dict[str, list[str]]) -> str:
    BUILD_STONES_CLASS = "TablesBuildingStones"

    r = [f"class {BUILD_STONES_CLASS}:"]

    for table, columns in table_columns.items():
        r.append(f"{ind(f"# {table}")}")

        table


# _generate_typed()