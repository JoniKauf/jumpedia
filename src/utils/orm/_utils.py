type TupleOfOneOrMore[T] = tuple[T, *tuple[T, ...]]


class TagSafeSqlStr:
    pass
