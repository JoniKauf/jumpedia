from typing import Any, Mapping, Optional, Self, Sequence, Sized

import mariadb
from mariadb import Connection, Cursor, Error


def placeholder(amount: int | Sized, placeholder: str = '%s') -> str:
    return ', '.join([placeholder] * (amount if isinstance(amount, int) else len(amount)))


class MariaDBConnector:
    def __init__(self, conn_kwargs: dict[str, Any]):
        self._conn_kwargs = conn_kwargs
        self._conn: Optional[Connection] = None # type: ignore
    
    def __enter__(self) -> Self:
        self._conn = mariadb.connect(**self._conn_kwargs)
        return self

    def _verify_connection(self):
        if self._conn is None or not self._conn.open:
            raise ConnectionError('use a context manager to open the connection')
        
    def __exit__(self, exc_type, exc_value, traceback):
        self._verify_connection()
        self._conn: Connection
        
        self._conn.commit()
        self._conn.close()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Cursor:
        self._verify_connection()
        c = self._conn.cursor()
        c.execute(query, params)
        return c