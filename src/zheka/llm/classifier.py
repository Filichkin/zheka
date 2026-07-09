"""Классификатор: нужен ли поиск по истории для сообщения."""

import openai
from loguru import logger
from openai import AsyncOpenAI

from zheka.constants import (
    CLASSIFIER_MAX_TOKENS,
    CLASSIFIER_POSITIVE,
)


class SearchClassifier:
    """Дешёвый LLM-вызов: «да» — вопрос для поиска по истории.

    Любая ошибка или неожиданный ответ трактуются как «нет» —
    сообщение уходит на обычный путь болтовни.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        model: str,
        prompt: str,
    ) -> None:
        self._client = openai_client
        self._model = model
        self._prompt = prompt

    async def is_search_query(self, text: str) -> bool:
        """Решает, искать ли ответ на сообщение в истории чата."""
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {'role': 'system', 'content': self._prompt},
                    {'role': 'user', 'content': text},
                ],
                max_completion_tokens=CLASSIFIER_MAX_TOKENS,
            )
        except openai.OpenAIError as error:
            logger.warning('Ошибка классификатора: {}', error)
            return False
        content = (
            (completion.choices[0].message.content or '')
            .strip()
            .lower()
        )
        decision = content.startswith(CLASSIFIER_POSITIVE)
        logger.info(
            'Классификатор: {!r} -> {!r} ({})',
            text[:60],
            content,
            'поиск' if decision else 'болтовня',
        )
        return decision
