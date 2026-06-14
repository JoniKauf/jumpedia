from dataclasses import dataclass


from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeName, AttributeSlot
from domain.value_objects.list import ListName
from repositories.attribute import AttributeRepository
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.attribute import AttributeInfoDTO, AttributeSummaryDTO
from services.list import ListAccessService
from services.permission import PermissionService
from services.user import CommunityUserAccessService


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _permission_service: PermissionService
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService

    def create(self, name: AttributeName, type: AttributeType, kind: AttributeKind, slot: AttributeSlot) -> AttributeEntity:
        community = self._community_access_service.get_current_or_raise()
        community_user = self._community_user_access_service.get_or_create_current_with_defaults(community)

        self._permission_service.ensure_community_rank(community_user, CommunityRank.ADMINISTRATOR)

        self._repo.count_by_list()

        # TODO check limit of max slot count below community limit because it is not checked in entity anymore


@dataclass(frozen=True, slots=True, eq=False)
class AttributeQueryService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _access_service: AttributeAccessService
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService
    _list_access_service: ListAccessService

    def info(self, name: AttributeName, list_name: str | None) -> AttributeInfoDTO:
        _, _, lst = self._list_access_service.get_convenient(None, None if list_name is None else ListName(list_name))

        attr = self._access_service.get_by_list_and_name_or_raise(lst, name)

        return AttributeInfoDTO(
            attr.name,
            lst,
            attr.type,
            attr.kind,
            attr.slot,
            attr.position
        )
    
    def browse(
        self,
        list_name: str | None,
    ) -> tuple[AttributeSummaryDTO, ...]:
        _, _, lst = self._list_access_service.get_convenient(None, None if list_name is None else ListName(list_name))

        attrs = self._repo.get_all_by_list_id(
            lst.id,
        )

        return tuple(
            AttributeSummaryDTO(
                attr.name,
                lst,
                attr.type,
                attr.kind,
                attr.slot,
                attr.position,
            )
            for attr in attrs
        )
        

@dataclass(frozen=True, slots=True, eq=False)
class AttributeAccessService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService

    def get_by_list_and_name_or_raise(self, lst: ListEntity, name: AttributeName) -> AttributeEntity:
        attr = self._repo.get_by_list_id_and_name(lst.id, name)

        if attr is None:
            raise errors.NotFoundByName(name, AttributeEntity)
        
        return attr