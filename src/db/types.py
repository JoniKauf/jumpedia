from sqlalchemy import Dialect
from sqlalchemy.types import TypeDecorator, String
import typing as t
from domain.value_objects import string


class RealStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(
        self, value: string.RealStr | None, dialect: Dialect
    ) -> str | None:
        assert isinstance(value, string.RealStr | None)

        if value is None:
            return None

        return value.value

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> string.RealStr | None:
        assert isinstance(value, str | None)

        if value is None:
            return None

        return string.RealStr(value, _validate=False)


class NormStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(
        self, value: string.NormStr | None, dialect: Dialect
    ) -> str | None:
        assert isinstance(value, string.NormStr | None)

        if value is None:
            return None

        return value.value

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> string.NormStr | None:
        assert isinstance(value, str | None)

        if value is None:
            return None

        return string.NormStr(value, _validate=False)
