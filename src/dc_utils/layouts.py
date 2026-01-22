import typing as t
from string.templatelib import Template
from types import CoroutineType

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


def browse(
    structure_type: type[BaseStructure],
    rows_count: int,
    urls: t.Sequence[str]
) -> str:
    zfill = len(str(len(urls)))

    if rows_count <= 0: 
        info(
            f"{structure_type.type_name.title()} Browsed",
            t"No {type} that matches the specified criteria could be found!",
        )
    
    assert urls

    return info(
        f"{structure_type.type_name_plural.title()} Browsed",
        t"A total of **{rows_count}** {structure_type.type_name_plural + ' were' if rows_count > 1 else structure_type.type_name + ' was'} found!",
        additional=Template(
            "\n".join(
                f"- **#{str(i).zfill(zfill)}**: {url}" for i, url in enumerate(urls, 1)
            )
            if len(urls) > 1
            else urls[0]
        ),
    )
