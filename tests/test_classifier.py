from types import SimpleNamespace
from typing import Any

import openai
import pytest

from zheka.llm import SearchClassifier


class FakeCompletions:
    def __init__(self, content: str | None, error: bool = False) -> None:
        self._content = content
        self._error = error
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        if self._error:
            raise openai.APIConnectionError(request=None)
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_classifier(
    content: str | None, error: bool = False
) -> tuple[SearchClassifier, FakeCompletions]:
    completions = FakeCompletions(content, error)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    classifier = SearchClassifier(client, 'test-model', 'промпт')
    return classifier, completions


@pytest.mark.asyncio
async def test_yes_answer_means_search() -> None:
    classifier, completions = make_classifier('да')

    assert await classifier.is_search_query('где сантехник?') is True
    assert completions.requests[0]['messages'][1]['content'] == (
        'где сантехник?'
    )


@pytest.mark.asyncio
async def test_yes_with_punctuation_and_case() -> None:
    classifier, _ = make_classifier('Да.')

    assert await classifier.is_search_query('текст') is True


@pytest.mark.asyncio
async def test_no_answer_means_chitchat() -> None:
    classifier, _ = make_classifier('нет')

    assert await classifier.is_search_query('что горит?') is False


@pytest.mark.asyncio
async def test_unexpected_answer_means_chitchat() -> None:
    classifier, _ = make_classifier('возможно')

    assert await classifier.is_search_query('текст') is False


@pytest.mark.asyncio
async def test_empty_answer_means_chitchat() -> None:
    classifier, _ = make_classifier(None)

    assert await classifier.is_search_query('текст') is False


@pytest.mark.asyncio
async def test_api_error_means_chitchat() -> None:
    classifier, _ = make_classifier(None, error=True)

    assert await classifier.is_search_query('текст') is False
