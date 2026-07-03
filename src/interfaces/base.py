import typing as t

from discord.ext import commands


class InterfaceMeta(commands.CogMeta):
    """CogMeta subclass to force a group name to be specified for all instances of this metaclass."""

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        *,
        group_name: str,
        **kwargs: t.Any,
    ):
        return super().__new__(
            mcls, name, bases, namespace, group_name=group_name, **kwargs
        )


class BaseInterface(commands.GroupCog, metaclass=InterfaceMeta, group_name="base"):
    pass
