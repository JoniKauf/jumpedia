from typing import Iterable

def _get_iterable_index[T](iterable: Iterable[T], index: int) -> T:
    if index < 0:
        return tuple(iterable)[index]
    
    iterator = iter(iterable)

    try:
        for _ in range(index + 1):
            value: T = next(iterator)
    except StopIteration:
        raise IndexError("Index out of range") from None
    
    return value  # type: ignore