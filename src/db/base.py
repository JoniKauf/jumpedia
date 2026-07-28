
from sqlalchemy.orm import DeclarativeBase
import typing as t

SCHEMA_NAME: t.Final[str] = "jumpedia"

class BaseModel(DeclarativeBase):
    __abstract__ = True

    __table_args__ = (
        {
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_bin",
            "schema": SCHEMA_NAME,
        },
    )
