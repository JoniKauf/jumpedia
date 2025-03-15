from typing import Any, Protocol, Sequence

class Comparable(Protocol):
    def __le__(self, value: Any, /) -> bool:
        ...

    def __lt__(self, value: Any, /) -> bool:
        ...

class Range[T: Comparable]:
    def __init__(self, first: T, last: T) -> None:
        self.first = first
        self.last = last

    def __repr__(self) -> str:
        return f"{Range.__name__}({self.first!r}, {self.last!r})"
    
    def __str__(self) -> str:
        return f"{self.first}->{self.last}"
    
    def __contains__(self, value: T) -> bool:
        return self.first <= value <= self.last
    
    @classmethod
    def combine(cls, range: 'Range[T]', *ranges: 'Range[T]') -> list['Range[T]']:
        all_ranges = sorted((range,) + ranges, key=lambda r: r.first)
        merged: list[Range[T]] = []
        
        if isinstance(all_ranges[0].first, int):
            for r in all_ranges:
                if merged and merged[-1].last + 1 >= r.first:  # type: ignore
                    merged[-1].last = max(merged[-1].last, r.last)
                else:
                    merged.append(cls(r.first, r.last))

            return merged
        
        for r in all_ranges:
            if merged and merged[-1].last >= r.first:
                merged[-1].last = max(merged[-1].last, r.last)
            else:
                merged.append(cls(r.first, r.last))
        
        return merged