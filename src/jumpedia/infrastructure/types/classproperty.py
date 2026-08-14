import typing as t


class classproperty[TOwner, TValue]:
    # Pyright requires value callable. So use TOwner instead type[TOwner] for now
    def __init__(self, func: t.Callable[[TOwner], TValue]) -> None:
        self.fget: t.Callable[[type[TOwner]], TValue] = func  # type: ignore

    @t.overload
    def __get__(self, instance: None, owner: type[TOwner]) -> TValue:
        pass

    @t.overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass

    def __get__(self, instance: TOwner | None, owner: type[TOwner]) -> TValue:
        return self.fget(owner)


class cached_classproperty[TOwner, TValue](classproperty[TOwner, TValue]):
    def __init__(self, func: t.Callable[[TOwner], TValue]) -> None:
        super().__init__(func)
        self._value: TValue | None = None

    def __get__(self, instance: TOwner | None, owner: type[TOwner]) -> TValue:
        if self._value is None:
            self._value = self.fget(owner)

        return self._value
