"""Построение ссылок на сообщения Telegram по каналу и id."""

from zheka.constants import PRIVATE_CHANNEL_PREFIX


def build_message_link(
    channel: str,
    msg_id: int,
    topic_id: int | None = None,
) -> str | None:
    """Собирает ссылку на сообщение по каналу (@username или id).

    Для сообщений в темах форума нужна трёхсегментная ссылка
    (с topic_id) — двухсегментную Telegram в форумных группах
    может не открыть.
    """
    if channel.startswith('@'):
        username = channel[1:]
        if topic_id is not None:
            return f'https://t.me/{username}/{topic_id}/{msg_id}'
        return f'https://t.me/{username}/{msg_id}'
    if channel.startswith(PRIVATE_CHANNEL_PREFIX):
        internal_id = channel[len(PRIVATE_CHANNEL_PREFIX):]
        if internal_id.isdigit():
            if topic_id is not None:
                return (
                    f'https://t.me/c/{internal_id}/{topic_id}/{msg_id}'
                )
            return f'https://t.me/c/{internal_id}/{msg_id}'
    return None
