from sqlalchemy import Dialect
from sqlalchemy.types import TypeDecorator, String
import typing as t
from domain.value_objects import strings


class RealStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: strings.RealStr | None, dialect: Dialect) -> str | None:
        assert isinstance(value, strings.RealStr | None)

        if value is None:
            return None
        
        return value.value

    def process_result_value(self, value: str | None, dialect: Dialect) -> strings.RealStr | None:
        assert isinstance(value, str | None)

        if value is None:
            return None
        
        return strings.RealStr(value, _validate=False)


class NormStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: strings.NormStr | None, dialect: Dialect) -> str | None:
        assert isinstance(value, strings.NormStr | None)

        if value is None:
            return None
        
        return value.value
        

    def process_result_value(self, value: str | None, dialect: Dialect) -> strings.NormStr | None:
        assert isinstance(value, str | None)
        
        if value is None:
            return None
        
        return strings.NormStr(value, _validate=False)