import typing as t
from string.templatelib import Template

from structures import BaseStructure
from structures.attribute.slot_str import SlotStr
from utils import text

from . import message


def _layout_message_status_factory(status: message.MessageStatus):
    def layout_message_status(
        header: str,
        core: Template,
        *,
        additional: Template | None = None,
        paragraphs: t.Sequence[Template] = (),
    ) -> str:
        return message.layout(
            header,
            core,
            status,
            additional=additional,
            paragraphs=paragraphs,
        )

    return layout_message_status


success = _layout_message_status_factory(message.MessageStatus.SUCCESS)
info = _layout_message_status_factory(message.MessageStatus.INFO)
warning = _layout_message_status_factory(message.MessageStatus.WARNING)


def _urls_additional(url: str, /, *urls: str) -> Template:
    urls = (url, *urls)

    return Template(
        "\n".join(
            f"- **#{str(i).zfill(len(str(len(urls))))}**: {url}"
            for i, url in enumerate(urls, 1)
        )
        if len(urls) > 1
        else urls[0]
    )


def structure_info(structure: BaseStructure, url: str, *urls: str) -> str:
    return info(
        f"{type(structure).type_name.title()} Info",
        t"Here is the info for the " + mention(structure) + t":",
        additional=_urls_additional(url, *urls),
    )


@t.overload
def structure_browsed(
    structure_type: type[BaseStructure],
    row_count: t.Literal[0],
) -> str: ...


@t.overload
def structure_browsed(
    structure_type: type[BaseStructure], row_count: int, url: str, *urls: str
) -> str: ...


def structure_browsed(
    structure_type: type[BaseStructure], row_count: int, url: str = "", *urls: str
) -> str:
    HEADER: t.Final[str] = f"{structure_type.type_name_plural.title()} Browsed"

    if row_count == 0:
        info(
            HEADER,
            t"No {structure_type} that matches the specified criteria could be found!",
        )

    assert row_count > 0

    assert url[0]

    urls = (url, *urls)

    return info(
        HEADER,
        t"A total of **{row_count}** {structure_type.type_name_plural + ' were' if row_count > 1 else structure_type.type_name + ' was'} found!",
        additional=_urls_additional(*urls),
    )


def structure_created(created_structure: BaseStructure) -> str:
    return success(
        f"{type(created_structure).type_name.title()} Created",
        t"The " + mention(created_structure) + t" has been created successfully!",
    )


def structure_nuked(nuked_structure: BaseStructure) -> str:
    return success(
        f"{type(nuked_structure).type_name.title()} Nuked",
        t"The " + mention(nuked_structure) + t" has been nuked successfully!",
    )


def structure_name_edited(
    edited_structure: BaseStructure, new_name: text.RealStr | SlotStr
) -> str:
    return success(
        f"{type(edited_structure).type_name.title()} Name Edited",
        t"The name of the "
        + mention(edited_structure)
        + t" has been changed to {new_name:,} successfully!",
    )


def structure_aliases_edited(
    edited_structure: BaseStructure,
    new_aliases: tuple[text.RealStr, ...] | tuple[SlotStr, ...],
) -> str:
    return success(
        f"{type(edited_structure).type_name.title()} Aliases Edited",
        t"The aliases of the "
        + mention(edited_structure)
        + t" have been changed to {new_aliases:,} successfully!",
    )


def mention(structure: BaseStructure, title: bool = False) -> Template:
    casing = str.title if title else str.lower
    return t"{casing(type(structure).type_name):p} {structure.name:,}"
