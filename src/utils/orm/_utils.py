import typing as t

if t.TYPE_CHECKING:
    from ._model import _SqlStrTag

PLACEHOLDER: str = '?'
type TupleOfOneOrMore[T] = tuple[T, *tuple[T, ...]]

def placehold(o: object, params: list[t.Any]) -> str:
    if isinstance(o, _SqlStrTag):
        return str(o)
    
    params.append(o)
    return PLACEHOLDER