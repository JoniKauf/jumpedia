from dataclasses import dataclass
from src.utils import text
import typing as t

@dataclass(slots=True)
class UniqueRealStrTuple[T: text.RealStr]:
    def __init__(self, iterable: t.Iterable[T], /, min_count: int = 1) -> None:
        mapping: dict[text.NormStr, T] = {}

        for real in iterable:
            norm = text.real_to_norm(real)

            if norm in mapping:
                raise ValueError(real, mapping[norm])
            
            mapping[norm] = real

        if len(mapping) < min_count:
            raise ValueError(len(mapping), min_count)

        self._real = tuple(mapping.values())
        self._norm = tuple(mapping)

    @property
    def real(self) -> tuple[T, ...]:
        return self._real
    
    @property
    def norm(self) -> tuple[text.NormStr, ...]:
        return self._norm
    
    @property
    def real_norm(self) -> tuple[tuple[T, text.NormStr], ...]:
        return tuple(zip(self.real, self.norm))