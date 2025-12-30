import time
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
    converter: MappingProxyType[int, t.Callable[[t.Any], t.Any]] = MappingProxyType({})
    kwargs: InitVar[t.Mapping[str, t.Any]] = MappingProxyType({})
    _create_connection: t.Callable[[], mariadb.Connection] = field(init=False, default=None)  # type: ignore

    def __post_init__(
        self,
        password: str,
        kwargs: t.Mapping[str, t.Any],
    ) -> None:
        object.__setattr__(
            self,
            "_create_connection",
            lambda: mariadb.connect(
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

    def cursor(self, c: Cursor | None = None) -> Cursor:
        if c is not None:
            return c

        RETRIES: int = 5
        DELAY: float = 0.5

        for i in range(RETRIES):
            try:
                c = self._create_connection()
            except mariadb.Error as e:
                time.sleep(DELAY)

                if i >= RETRIES - 1:
                    raise e
            else:
                break

        assert c is not None

        return Cursor(c)


__all__ = ["Connector"]
