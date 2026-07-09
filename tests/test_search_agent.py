import json
from types import SimpleNamespace
from typing import Any, Self

import pytest

from zheka.llm import SearchAgent
from zheka.llm.helpers import sanitize_search_result, strip_sender_ids


def make_hit(msg_id: int, text: str = 'текст') -> dict[str, Any]:
    return {
        'channel': '-1001103887282',
        'topic_id': 203154,
        'topic_title': 'Общие вопросы',
        'msg_id_start': msg_id,
        'date_start': '2026-07-01T10:00:00+03:00',
        'text': text,
    }


def tool_call_reply(arguments: dict[str, Any]) -> SimpleNamespace:
    """Ответ модели с одним вызовом search_messages."""
    call = SimpleNamespace(
        id='call-1',
        function=SimpleNamespace(
            name='search_messages',
            arguments=json.dumps(arguments),
        ),
    )
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def final_reply(text: str) -> SimpleNamespace:
    """Финальный ответ модели без вызовов инструментов."""
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, replies: list[SimpleNamespace]) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        return self._replies.pop(0)


class FakeOpenAI:
    def __init__(self, replies: list[SimpleNamespace]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(replies))


class FakeMCP:
    """MCP-клиент: контекстный менеджер с одним инструментом."""

    def __init__(self, hits: list[dict[str, Any]] | None = None) -> None:
        self._hits = hits or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def list_tools(self) -> list[Any]:
        return [
            SimpleNamespace(
                name='search_messages',
                description='Поиск по чатам',
                inputSchema={'type': 'object'},
            )
        ]

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> SimpleNamespace:
        self.calls.append((name, arguments))
        return SimpleNamespace(
            data={'hits': self._hits},
            structured_content={'hits': self._hits},
            content=[],
        )


def make_agent(
    replies: list[SimpleNamespace], mcp: FakeMCP
) -> SearchAgent:
    return SearchAgent(
        FakeOpenAI(replies),
        mcp_url='http://test/mcp',
        model='test-model',
        client_factory=lambda: mcp,
    )


MESSAGES = [{'role': 'system', 'content': 'персона'}]


@pytest.mark.asyncio
async def test_answer_without_tool_calls() -> None:
    mcp = FakeMCP()
    agent = make_agent([final_reply('просто болтаю')], mcp)

    answer = await agent.ask(MESSAGES, chat_id=-100)

    assert answer is not None
    assert answer.text == 'просто болтаю'
    assert answer.citations == []
    assert answer.searched is False
    assert mcp.calls == []


@pytest.mark.asyncio
async def test_search_forces_channel_and_drops_topic_id() -> None:
    mcp = FakeMCP(hits=[make_hit(10)])
    agent = make_agent(
        [
            tool_call_reply(
                {'query': 'сантехник', 'channel': '@other', 'topic_id': 5}
            ),
            final_reply('нашёл сантехника'),
        ],
        mcp,
    )

    answer = await agent.ask(MESSAGES, chat_id=-1001103887282)

    name, arguments = mcp.calls[0]
    assert name == 'search_messages'
    assert arguments['channel'] == '-1001103887282'
    assert 'topic_id' not in arguments
    assert arguments['query'] == 'сантехник'
    assert answer is not None
    assert answer.text == 'нашёл сантехника'
    assert answer.searched is True


@pytest.mark.asyncio
async def test_citations_deduplicated_and_limited() -> None:
    hits = [make_hit(1), make_hit(1), make_hit(2), make_hit(3), make_hit(4)]
    mcp = FakeMCP(hits=hits)
    agent = make_agent(
        [tool_call_reply({'query': 'вода'}), final_reply('итог')],
        mcp,
    )

    answer = await agent.ask(MESSAGES, chat_id=-1001103887282)

    assert answer is not None
    assert len(answer.citations) == 3
    assert answer.citations[0].link == (
        'https://t.me/c/1103887282/203154/1'
    )


@pytest.mark.asyncio
async def test_search_without_hits_sets_searched_flag() -> None:
    mcp = FakeMCP(hits=[])
    agent = make_agent(
        [tool_call_reply({'query': 'вода'}), final_reply('не нашёл')],
        mcp,
    )

    answer = await agent.ask(MESSAGES, chat_id=-100)

    assert answer is not None
    assert answer.searched is True
    assert answer.citations == []


@pytest.mark.asyncio
async def test_mcp_connection_error_returns_none() -> None:
    def broken_factory() -> Any:
        raise ConnectionError('MCP недоступен')

    agent = SearchAgent(
        FakeOpenAI([]),
        mcp_url='http://test/mcp',
        model='test-model',
        client_factory=broken_factory,
    )

    assert await agent.ask(MESSAGES, chat_id=-100) is None


@pytest.mark.asyncio
async def test_exhausted_rounds_return_none() -> None:
    replies = [tool_call_reply({'query': 'вода'}) for _ in range(5)]
    mcp = FakeMCP(hits=[make_hit(1)])
    agent = make_agent(replies, mcp)

    assert await agent.ask(MESSAGES, chat_id=-100) is None


def test_strip_sender_ids() -> None:
    text = (
        'Канал -100. тема «Услуги». период 2026-06-02–2026-06-02.\n'
        '6189604808: Принимаю заказы на выпечку\n'
        'unknown: без автора\n'
        'обычная строка: не трогаем\n'
        'позвоните по 89261234567: шутка'
    )

    cleaned = strip_sender_ids(text)

    assert '6189604808' not in cleaned
    assert 'unknown:' not in cleaned
    assert 'Принимаю заказы на выпечку' in cleaned
    assert 'обычная строка: не трогаем' in cleaned
    assert 'позвоните по 89261234567: шутка' in cleaned


def test_sanitize_survives_unexpected_result_shapes() -> None:
    sanitize_search_result(SimpleNamespace(structured_content=None))
    sanitize_search_result(SimpleNamespace(structured_content={}))
    sanitize_search_result(
        SimpleNamespace(
            structured_content={'hits': [{'chunk_id': 1}, 'мусор']}
        )
    )


@pytest.mark.asyncio
async def test_sender_ids_hidden_from_llm() -> None:
    hit = make_hit(10, text='6189604808: сдам гараж')
    mcp = FakeMCP(hits=[hit])
    openai = FakeOpenAI(
        [tool_call_reply({'query': 'гараж'}), final_reply('нашёл')]
    )
    agent = SearchAgent(
        openai,
        mcp_url='http://test/mcp',
        model='test-model',
        client_factory=lambda: mcp,
    )

    await agent.ask(MESSAGES, chat_id=-100)

    tool_message = openai.chat.completions.requests[1]['messages'][-1]
    assert '6189604808: ' not in tool_message['content']
    assert 'сдам гараж' in tool_message['content']


@pytest.mark.asyncio
async def test_tool_error_reported_to_llm() -> None:
    class BrokenMCP(FakeMCP):
        async def call_tool(
            self, name: str, arguments: dict[str, Any]
        ) -> SimpleNamespace:
            raise RuntimeError('база лежит')

    mcp = BrokenMCP()
    openai = FakeOpenAI(
        [tool_call_reply({'query': 'вода'}), final_reply('не нашлось')]
    )
    agent = SearchAgent(
        openai,
        mcp_url='http://test/mcp',
        model='test-model',
        client_factory=lambda: mcp,
    )

    answer = await agent.ask(MESSAGES, chat_id=-100)

    assert answer is not None
    assert answer.text == 'не нашлось'
    tool_message = openai.chat.completions.requests[1]['messages'][-1]
    assert 'Ошибка вызова инструмента' in tool_message['content']
