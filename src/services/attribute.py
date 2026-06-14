from dataclasses import dataclass


from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeName, AttributeSlot
from domain.value_objects.community import CommunityLimits, CommunityName
from domain.value_objects.list import ListName
from repositories.attribute import AttributeRepository
from repositories.dtos.attribute import CreateAttributeDTO
from services.community import CommunityAccessService
from services.community_user import CommunityUserAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.attribute import AttributeInfoDTO, AttributeSummaryDTO, DeletedAttributeDTO
from services.list import ListAccessService
from services.permission import PermissionService
import typing as t


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _access_service: AttributeAccessService
    _permission_service: PermissionService
    _list_access_service: ListAccessService

    @t.overload
    def create(
        self,
        name: AttributeName,
        type: t.Literal[AttributeType.STATIC],
        kind: t.Literal[AttributeKind.ID, AttributeKind.NAME, AttributeKind.ALIAS],
        slot: AttributeSlot,
        list_name: ListName | None,
    ) -> AttributeEntity:
        pass

    @t.overload
    def create(
        self,
        name: AttributeName,
        type: t.Literal[AttributeType.TASK, AttributeType.USER],
        kind: t.Literal[AttributeKind.NONE],
        slot: AttributeSlot[t.Literal[0]],
        list_name: ListName | None,
    ) -> AttributeEntity:
        pass

    def create(
        self,
        name: AttributeName,
        type: AttributeType,
        kind: AttributeKind,
        slot: AttributeSlot,
        list_name: ListName | None,
    ) -> AttributeEntity:
        # --- Verify Typing ---
        if type is AttributeType.STATIC:
            if kind is AttributeKind.NONE:
                raise ValueError(f"{kind=}")
        else:
            if kind is not AttributeKind.NONE or slot.min_count != 0:
                raise ValueError(f"{kind=}, {slot.min_count=}")

        # --- Get Data ---
        community, community_user, lst = self._list_access_service.get_convenient(
            None, list_name
        )

        # --- Verify Rank ---
        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )
        
        # --- Verify Limit Of Count Not Exceeded ---
        # pos starts at 1 so max_pos == count
        attr_count = self._repo.count_by_list(lst.id)

        if attr_count >= community.limits.list_attribute_count_max:
            raise errors.CountLimitReached(
                community.limits.list_attribute_count_max, AttributeEntity
            )

        # --- Verify Name Not Taken ---
        name_taken_attr = self._repo.get_by_list_id_and_name(lst.id, name)

        if name_taken_attr is not None:
            raise errors.NameAlreadyTaken(name, name_taken_attr)

        # --- Verify Alias Not Taken ---
        alias_taken_attr = self._repo.get_by_list_id_and_alias(lst.id, name)

        if alias_taken_attr is not None:
            raise errors.NameAlreadyTaken(name, alias_taken_attr)
        
        # TODO check all aliases as well, avoid N + 1, add new error for aliases/syn

        # TODO allow aliases, allow collection and verify

        # Check slot count max does not exceed community limit here, because in Slot itself we don't know the community's limit
        if slot.max_count > community.limits.attribute_task_value_slot_count_max:
            raise errors.SlotCountLimitExceeded(
                slot.min_count,
                slot.max_count,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT,
                community.limits.attribute_task_value_slot_count_max,
            )

        return self._repo.create(
            CreateAttributeDTO(lst._id, name, type, kind, slot, attr_count + 1)
        )

    def delete(self, name: AttributeName, list_name: ListName | None) -> DeletedAttributeDTO:
        _, community_user, lst, attr = self._access_service.get_convenient(
            None, list_name, name
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )

        self._repo.delete(attr.id)
        self._repo.decrement_positions_after(lst.id, attr.position)

        return DeletedAttributeDTO(
            attr.name,
            lst,
            attr.type,
            attr.kind,
            attr.slot,
            attr.position
        )




@dataclass(frozen=True, slots=True, eq=False)
class AttributeQueryService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _access_service: AttributeAccessService
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService
    _list_access_service: ListAccessService

    def info(self, name: AttributeName, list_name: str | None) -> AttributeInfoDTO:
        _, _, lst = self._list_access_service.get_convenient(
            None, None if list_name is None else ListName(list_name)
        )

        attr = self._access_service.get_by_list_and_name_or_raise(lst, name)

        return AttributeInfoDTO(
            attr.name, lst, attr.type, attr.kind, attr.slot, attr.position
        )

    def browse(
        self,
        list_name: str | None,
    ) -> tuple[AttributeSummaryDTO, ...]:
        _, _, lst = self._list_access_service.get_convenient(
            None, None if list_name is None else ListName(list_name)
        )

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
    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: AttributeName
    ) -> AttributeEntity:
        attr = self._repo.get_by_list_id_and_name(lst.id, name)

        if attr is None:
            raise errors.NotFoundByName(name, AttributeEntity)

        return attr

    def get_convenient(
        self,
        community_name: CommunityName | None,
        list_name: ListName | None,
        attribute_name: AttributeName,
    ) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity, AttributeEntity]:
        community, community_user, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        attr = self.get_by_list_and_name_or_raise(lst, attribute_name)

        return (community, community_user, lst, attr)
