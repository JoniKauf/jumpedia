from dataclasses import InitVar, dataclass, field
import typing as t
from types import MappingProxyType

import mariadb

from .cursor import Cursor

@dataclass(frozen=True, slots=True)
class Connector:
    host: str
    user: str
    password: InitVar[str]
    database_name: str | None
    port: int = 3306
    autocommit: bool = False
    pool_name: InitVar[str] = 'pool'
    connection_pool_size: InitVar[int] = 5
    converter: MappingProxyType[int, t.Callable[[t.Any], t.Any]] = MappingProxyType({})
    kwargs: InitVar[t.Mapping[str, t.Any]] = MappingProxyType({})
    pool: mariadb.ConnectionPool = field(init=False, default=None)  # type: ignore
    
    def __post_init__(self, password: str, pool_name: str, connection_pool_size: int, kwargs: t.Mapping[str, t.Any]) -> None:
        object.__setattr__(self, 'pool', mariadb.ConnectionPool(
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
        ))
    
    def cursor(self) -> Cursor:
        c = self.pool.get_connection().cursor(dictionary=True)
        c.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        return c


__all__ = ["Connector"]
