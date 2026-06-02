from dataclasses import dataclass


from repositories.attribute import AttributeRepository
from services.contexts.interacting_user import InteractingUserContext
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _permission_service: PermissionService
