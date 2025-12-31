import time
import typing as t
from dataclasses import InitVar, dataclass, field
from types import MappingProxyType

import mariadb

from .cursor import Cursor


@dataclass(slots=True)
class Connector:
    host: str
    user: str
    password: InitVar[str]
    database_name: str | None
    port: int = 3306
    autocommit: bool = False
    converter: MappingProxyType[int, t.Callable[[t.Any], t.Any]] = field(
        default_factory=lambda: MappingProxyType({})
    )
    kwargs: InitVar[t.Mapping[str, t.Any]] = MappingProxyType({})

    _create_connection: t.Callable[[], mariadb.Connection] = field(init=False, default=None)  # type: ignore
    _existing_conn: mariadb.Connection | None = field(init=False, default=None)
    _existing_refs: int = 0

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

    def cursor(self) -> Cursor:
        if self._existing_conn is not None:
            return Cursor(self, self._existing_conn)

        RETRIES: int = 10
        DELAY: float = 0.25

        for i in range(RETRIES):
            try:
                conn = self._create_connection()
            except mariadb.Error as e:
                time.sleep(DELAY)

                if i >= RETRIES - 1:
                    raise e
            else:
                break

        assert conn is not None

        self._existing_conn = conn

        return Cursor(self, conn)


__all__ = ["Connector"]
