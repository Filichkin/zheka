"""Форматирование ответа агента для отправки в Telegram."""

from zheka.constants import (
    SEARCH_REPLY_PREFIX,
    SOURCES_HEADER,
    TELEGRAM_MESSAGE_LIMIT,
)
from zheka.llm.helpers import citation_line
from zheka.llm.schemas import AgentAnswer


def render_answer(answer: AgentAnswer) -> str:
    """Собирает текст ответа и блок источников в лимит Telegram.

    Ответ по результатам поиска предваряется вводной фразой.
    При обрезке страдает текст, а не ссылки: блок источников
    целиком помещается в лимит.
    """
    text = answer.text
    if answer.citations:
        text = f'{SEARCH_REPLY_PREFIX}\n{text}'
    linked = [c for c in answer.citations if c.link]
    if not linked:
        return text[:TELEGRAM_MESSAGE_LIMIT]
    sources = '\n'.join(
        citation_line(index, citation)
        for index, citation in enumerate(linked, start=1)
    )
    block = f'\n\n{SOURCES_HEADER}\n{sources}'
    text_budget = max(0, TELEGRAM_MESSAGE_LIMIT - len(block))
    return f'{text[:text_budget]}{block}'
