from sqlalchemy import Dialect
from sqlalchemy.types import TypeDecorator, String
import typing as t
from domain.value_objects import s


class RealStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: s.RealStr | None, dialect: Dialect) -> str | None:
        assert isinstance(value, s.RealStr | None)

        if value is None:
            return None
        
        return value.value

    def process_result_value(self, value: str | None, dialect: Dialect) -> s.RealStr | None:
        assert isinstance(value, str | None)

        if value is None:
            return None
        
        return s.RealStr(value, _validate=False)


class NormStrType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: s.NormStr | None, dialect: Dialect) -> str | None:
        assert isinstance(value, s.NormStr | None)

        if value is None:
            return None
        
        return value.value
        

    def process_result_value(self, value: str | None, dialect: Dialect) -> s.NormStr | None:
        assert isinstance(value, str | None)
        
        if value is None:
            return None
        
        return s.NormStr(value, _validate=False)