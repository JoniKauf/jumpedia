import typing as t
from string.templatelib import Template
from types import CoroutineType

from adapting import BaseStructureAdapter
from structures import BaseStructure
from utils import gist

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
        t"Here is the info for the "
        + BaseStructureAdapter.do_mention(structure)
        + t":",
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
