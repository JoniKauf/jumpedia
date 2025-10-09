from . import BaseStructure
import typing as t

if t.TYPE_CHECKING:
    from .community import Community

class BaseStructureError(Exception):
    def __init_subclass__(cls) -> None:
        if cls is BaseStructureError:
            raise RuntimeError
    
class StructureNotFoundError[T: BaseStructure = BaseStructure](BaseStructureError, LookupError):
    def __init__(self, type: type[T], *args: object) -> None:
        self.type = type
        super().__init__(type, *args)

class StructureFoundError[T: BaseStructure = BaseStructure](BaseStructureError, LookupError):
    def __init__(self, structure: T, *args: object) -> None:
        self.structure = structure
        super().__init__(structure, *args)

class SynAlreadyTakenError[T: BaseStructure = BaseStructure](StructureFoundError[T]): pass

class ServerAlreadyConnectedToCommunityError(StructureFoundError[Community]): pass



def __verify_integrity() -> None:
    for obj in __dict__.values():
        if isinstance(obj, type) and isinstance(obj, Exception) and not isinstance(obj, BaseStructureError):
            raise RuntimeError
        
__verify_integrity()