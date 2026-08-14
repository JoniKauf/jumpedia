from jumpedia.domain.value_objects.attribute import AttributeSynStr
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.interfaces import dsls
from jumpedia.interfaces.bindings import common


# attribute_aliases, attributes and yield_ technically share the same
# code but might evolve differently. Keep them seperate.
def attribute_aliases(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(
                common.build_dsl_input(s)
            )
        )
    )


def attributes(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(
                common.build_dsl_input(s)
            )
        )
    )


def yield_(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(syn)
            for syn in dsls.sequence.engine.SequenceEngine().eval(
                common.build_dsl_input(s)
            )
        )
    )


def task_aliases(s: str | None) -> tuple[FieldSlotStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            FieldSlotStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(
                common.build_dsl_input(s)
            )
        )
    )
