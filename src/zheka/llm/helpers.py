"""Хелперы агента: конвертация результатов MCP-поиска."""

from typing import Any

from zheka.llm.schemas import Citation
from zheka.mcp import build_message_link, get_field


def hit_to_citation(hit: Any) -> Citation:
    """Собирает Citation из одного найденного чанка."""
    channel = get_field(hit, 'channel')
    return Citation(
        channel=channel,
        topic_title=get_field(hit, 'topic_title'),
        date=get_field(hit, 'date_start'),
        link=build_message_link(channel, get_field(hit, 'msg_id_start')),
    )
