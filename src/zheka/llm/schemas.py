"""Модели результата работы агента."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Citation:
    """Ссылка на сообщение-источник из результатов поиска."""

    channel: str
    topic_title: str | None
    date: datetime | str | None
    link: str | None


@dataclass
class AgentAnswer:
    """Итог работы агента: текст ответа и источники."""

    text: str
    citations: list[Citation] = field(default_factory=list)
