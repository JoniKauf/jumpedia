import typing as t

from sqlalchemy import BINARY, Dialect
from sqlalchemy.types import String, TypeDecorator

from jumpedia.domain.value_objects import string


class RealStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(
        self, value: string.RealStr | None, dialect: Dialect
    ) -> str | None:
        assert value is None or isinstance(value, string.RealStr)

        if value is None:
            return None

        return value.value

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> string.RealStr | None:
        assert value is None or isinstance(value, str)

        if value is None:
            return None

        return string.RealStr._create(value)


class NormHashType(TypeDecorator):
    impl = BINARY(32)
    cache_ok = True

    def process_bind_param(
        self, value: string.NormHash | None, dialect: Dialect
    ) -> bytes | None:
        assert value is None or isinstance(value, string.NormHash)

        if value is None:
            return None

        return value.value

    def process_result_value(
        self, value: bytes | None, dialect: Dialect
    ) -> string.NormHash | None:
        assert value is None or isinstance(value, bytes)

        if value is None:
            return None

        return string.NormHash._create(value)
