import typing as t
from dataclasses import InitVar, dataclass, field
from types import MappingProxyType

import mariadb
import mariadb.connectionpool

from .cursor import Cursor


@dataclass(frozen=True, slots=True)
class Connector:
    host: str
    user: str
    password: InitVar[str]
    database_name: str | None
    port: int = 3306
    autocommit: bool = False
    pool_name: InitVar[str] = "pool"
    connection_pool_size: InitVar[int] = 10
    converter: MappingProxyType[int, t.Callable[[t.Any], t.Any]] = MappingProxyType({})
    kwargs: InitVar[t.Mapping[str, t.Any]] = MappingProxyType({})
    _pool: mariadb.ConnectionPool | None = field(init=False, default=None)
    _lazy_pool: t.Callable[[], mariadb.ConnectionPool] = field(init=False, default=None)  # type: ignore

    def __post_init__(
        self,
        password: str,
        pool_name: str,
        connection_pool_size: int,
        kwargs: t.Mapping[str, t.Any],
    ) -> None:
        object.__setattr__(
            self,
            "_lazy_pool",
            lambda: mariadb.ConnectionPool(
                # Pool
                pool_name=pool_name,
                pool_size=connection_pool_size,
                # Connection
                host=self.host,
                user=self.user,
                password=password,
                database=self.database_name,
                autocommit=self.autocommit,
                port=self.port,
                converter=self.converter,
                **kwargs,
            ),
        )

    def _get_pool(self) -> mariadb.ConnectionPool:
        if self._pool is None:
            object.__setattr__(self, "_pool", self._lazy_pool())

        return self._pool  # type: ignore

    def cursor(self, c: Cursor | None = None) -> Cursor:
        if c is not None:
            return c

        c = self._get_pool().get_connection().cursor(dictionary=True)
        c.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        return Cursor(c)


__all__ = ["Connector"]
