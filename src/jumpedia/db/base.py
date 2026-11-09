import typing as t

from sqlalchemy.orm import DeclarativeBase

SCHEMA_NAME: t.Final[str] = "jumpedia"


class BaseModel(DeclarativeBase):
    """The base model used by every model.
    
    It holds the general charset and collation so it is consistent with Python and 
    across all models.
    """

    __abstract__ = True

    __table_args__ = (
        {
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_bin",
            "schema": SCHEMA_NAME,
        },
    )
