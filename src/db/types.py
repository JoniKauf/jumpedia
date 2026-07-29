import typing as t

from sqlalchemy import Dialect
from sqlalchemy.types import String, TypeDecorator

from domain.value_objects import string


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


class NormStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(
        self, value: string.NormStr | None, dialect: Dialect
    ) -> str | None:
        assert value is None or isinstance(value, string.NormStr)

        if value is None:
            return None

        return value.value

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> string.NormStr | None:
        assert value is None or isinstance(value, str)

        if value is None:
            return None

        return string.NormStr._create(value)
