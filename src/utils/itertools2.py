import typing as t
from collections import defaultdict


def groupby_unsorted[T1, T2: t.Hashable](
    iterable: t.Iterable[T1], /, key: t.Callable[[T1], T2]
) -> defaultdict[T2, list[T1]]:
    res: defaultdict[T2, list[T1]] = defaultdict(list)

    for elem in iterable:
        res[key(elem)].append(elem)

    return res