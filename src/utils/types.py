import typing as t

type SetLike[T: t.Hashable] = set[T] | frozenset[T]
