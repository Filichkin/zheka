"""Построение ссылок на сообщения Telegram по каналу и id."""

from zheka.constants import PRIVATE_CHANNEL_PREFIX


def build_message_link(channel: str, msg_id: int) -> str | None:
    """Собирает ссылку на сообщение по каналу (@username или id)."""
    if channel.startswith('@'):
        return f'https://t.me/{channel[1:]}/{msg_id}'
    if channel.startswith(PRIVATE_CHANNEL_PREFIX):
        internal_id = channel[len(PRIVATE_CHANNEL_PREFIX):]
        if internal_id.isdigit():
            return f'https://t.me/c/{internal_id}/{msg_id}'
    return None
