import typing as t
from types import MappingProxyType

import mariadb

from .cursor import Cursor, CursorContextManager


class Connector:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str | None,
        *,
        port: int = 3306,
        autocommit: bool = False,
        connection_pool_size: int = 5,
        converter: t.Mapping[int, t.Callable[[t.Any], t.Any]] = MappingProxyType({}),
        **kwargs: t.Any
    ) -> None:
        self._pool = mariadb.ConnectionPool(
            # Pool
            pool_name="connector_pool",
            pool_size=connection_pool_size,
            # Connection
            host=host,
            user=user,
            password=password,
            database=database,
            autocommit=autocommit,
            port=port,
            converter=converter,
            **kwargs
        )

    def cursor(self) -> CursorContextManager:
        return CursorContextManager(
            Cursor(self._pool.get_connection().cursor(dictionary=True))
        )

__all__ = ["Connector"]
