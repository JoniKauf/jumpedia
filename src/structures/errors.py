from . import BaseStructure


class StructureNotFoundError(LookupError):
    def __init__(self, type: type[BaseStructure]) -> None:
        self.type = type
        super().__init__(type)
