from types import SimpleNamespace
from typing import Any

import openai
import pytest

from zheka.config import Settings
from zheka.llm import LLMClient


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        TG_BOT_TOKEN='test-token',
        OPEN_AI_KEY='test-key',
        llm_model='test-model',
    )


class FakeCompletions:
    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self._content = content
        self._error = error

    async def create(self, **kwargs: Any) -> Any:
        if self._error is not None:
            raise self._error
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_client(completions: FakeCompletions) -> LLMClient:
    client = LLMClient(make_settings())
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    return client


@pytest.mark.asyncio
async def test_returns_stripped_content() -> None:
    client = make_client(FakeCompletions(content='  привет!  '))

    assert await client.generate([]) == 'привет!'


@pytest.mark.asyncio
async def test_api_error_returns_none() -> None:
    client = make_client(FakeCompletions(error=openai.OpenAIError('boom')))

    assert await client.generate([]) is None


@pytest.mark.asyncio
async def test_empty_content_returns_none() -> None:
    client = make_client(FakeCompletions(content=''))

    assert await client.generate([]) is None
