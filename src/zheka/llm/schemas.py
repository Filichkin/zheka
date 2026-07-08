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
    """Итог работы агента: текст ответа и источники.

    searched — агент вызывал поиск; вместе с пустыми citations
    означает «искал и не нашёл» (бот в этом случае молчит).
    """

    text: str
    citations: list[Citation] = field(default_factory=list)
    searched: bool = False
