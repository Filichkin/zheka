"""Хелперы агента: конвертация и представление результатов поиска."""

from datetime import datetime
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
        link=build_message_link(
            channel,
            get_field(hit, 'msg_id_start'),
            get_field(hit, 'topic_id'),
        ),
    )


def format_date(date: datetime | str | None) -> str | None:
    """Приводит дату цитаты к виду YYYY-MM-DD."""
    if date is None:
        return None
    if isinstance(date, datetime):
        return date.strftime('%Y-%m-%d')
    return str(date)[:10] or None


def citation_line(index: int, citation: Citation) -> str:
    """Строка источника: номер, тема и дата (если есть), ссылка."""
    parts = [
        part
        for part in (citation.topic_title, format_date(citation.date))
        if part
    ]
    if parts:
        return f'{index}. {", ".join(parts)} — {citation.link}'
    return f'{index}. {citation.link}'
