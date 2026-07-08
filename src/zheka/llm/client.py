import openai
from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from zheka.config import Settings
from zheka.constants import LLM_TIMEOUT_SECONDS, MAX_COMPLETION_TOKENS


class LLMClient:
    """Обёртка над AsyncOpenAI: один клиент на процесс."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        self._model = settings.llm_model

    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> str | None:
        """Возвращает текст ответа модели или None при ошибке."""
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )
        except openai.OpenAIError as error:
            logger.error('Ошибка вызова LLM: {}', error)
            return None
        content = completion.choices[0].message.content
        if not content:
            logger.warning('LLM вернула пустой ответ')
            return None
        return content.strip()
