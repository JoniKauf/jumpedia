import typing as t

import discord

from jumpedia.domain.errors.business import FileNotUtf8, FileTooBig

# Files are parsed before any rank is checked, so their size has to be capped.
_SIZE_MAX: t.Final[int] = 100_000


async def text(attachment: discord.Attachment) -> str:
    if attachment.size > _SIZE_MAX:
        raise FileTooBig(attachment.size, _SIZE_MAX)

    try:
        # Some editors on Windows start the file with an invisible byte order mark.
        return (await attachment.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FileNotUtf8()
