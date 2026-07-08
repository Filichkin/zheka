from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from zheka.bot.handlers import on_group_message
from zheka.config import Settings
from zheka.context import ContextBuffer
from zheka.llm import AgentAnswer, Citation
from zheka.ratelimit import RateLimiter


CHAT_ID = -1001103887282
BOT_USERNAME = 'zheka_bot'


def make_settings(**overrides: Any) -> Settings:
    params: dict[str, Any] = {
        'TG_BOT_TOKEN': 'test-token',
        'OPEN_AI_KEY': 'test-key',
        'llm_model': 'test-model',
        'RAG_MCP_URL': 'http://127.0.0.1:8765/mcp',
        'SEARCH_CHAT_IDS': str(CHAT_ID),
    }
    params.update(overrides)
    return Settings(_env_file=None, **params)


class FakeMessage:
    """Сообщение группы с упоминанием бота (кандидат на ответ)."""

    def __init__(self, text: str, chat_id: int = CHAT_ID) -> None:
        self.text = text
        self.chat = SimpleNamespace(id=chat_id)
        self.from_user = SimpleNamespace(full_name='Иван Иванов')
        self.date = datetime.now(UTC)
        self.reply_to_message = None
        self.replies: list[str] = []

    async def reply(self, text: str) -> None:
        self.replies.append(text)


class FakeLLM:
    def __init__(self, reply: str | None = 'обычный ответ') -> None:
        self._reply = reply
        self.calls: list[Any] = []

    async def generate(self, messages: Any) -> str | None:
        self.calls.append(messages)
        return self._reply


class FakeAgent:
    def __init__(self, answer: AgentAnswer | None) -> None:
        self._answer = answer
        self.calls: list[tuple[Any, int]] = []

    async def ask(
        self, messages: Any, chat_id: int
    ) -> AgentAnswer | None:
        self.calls.append((messages, chat_id))
        return self._answer


def found_answer() -> AgentAnswer:
    citation = Citation(
        channel=str(CHAT_ID),
        topic_title='Общие вопросы',
        date='2026-07-01T10:00:00+03:00',
        link='https://t.me/c/1103887282/42',
    )
    return AgentAnswer(text='нашёл сантехника', citations=[citation])


async def call_handler(
    message: FakeMessage,
    settings: Settings,
    llm: FakeLLM,
    search_agent: FakeAgent | None,
) -> ContextBuffer:
    buffer = ContextBuffer(maxlen=15)
    await on_group_message(
        message,  # type: ignore[arg-type]
        bot=SimpleNamespace(),  # type: ignore[arg-type]
        buffer=buffer,
        settings=settings,
        rate_limiter=RateLimiter(max_per_minute=10, max_per_day=100),
        llm=llm,  # type: ignore[arg-type]
        persona='персона',
        search_agent=search_agent,  # type: ignore[arg-type]
        agent_persona='персона + инструкции',
        bot_id=1,
        bot_username=BOT_USERNAME,
        bot_name='Жека',
    )
    return buffer


@pytest.mark.asyncio
async def test_agent_answer_with_sources_sent() -> None:
    message = FakeMessage(f'@{BOT_USERNAME} кто знает сантехника?')
    llm = FakeLLM()
    agent = FakeAgent(found_answer())

    buffer = await call_handler(message, make_settings(), llm, agent)

    assert len(agent.calls) == 1
    assert agent.calls[0][1] == CHAT_ID
    assert llm.calls == []
    assert len(message.replies) == 1
    assert 'нашёл сантехника' in message.replies[0]
    assert 'Источники:' in message.replies[0]
    assert 'https://t.me/c/1103887282/42' in message.replies[0]
    assert buffer.get_recent(CHAT_ID)[-1].text == message.replies[0]


@pytest.mark.asyncio
async def test_agent_failure_falls_back_to_persona() -> None:
    message = FakeMessage(f'@{BOT_USERNAME} кто знает сантехника?')
    llm = FakeLLM(reply='отвечаю как обычно')
    agent = FakeAgent(answer=None)

    await call_handler(message, make_settings(), llm, agent)

    assert len(agent.calls) == 1
    assert len(llm.calls) == 1
    assert message.replies == ['отвечаю как обычно']


@pytest.mark.asyncio
async def test_chat_outside_search_list_skips_agent() -> None:
    message = FakeMessage(f'@{BOT_USERNAME} привет')
    llm = FakeLLM()
    agent = FakeAgent(found_answer())
    settings = make_settings(SEARCH_CHAT_IDS='-42')

    await call_handler(message, settings, llm, agent)

    assert agent.calls == []
    assert len(llm.calls) == 1
    assert message.replies == ['обычный ответ']


@pytest.mark.asyncio
async def test_without_agent_uses_persona_path() -> None:
    message = FakeMessage(f'@{BOT_USERNAME} привет')
    llm = FakeLLM()

    await call_handler(message, make_settings(), llm, search_agent=None)

    assert len(llm.calls) == 1
    assert message.replies == ['обычный ответ']


@pytest.mark.asyncio
async def test_agent_empty_text_falls_back_to_persona() -> None:
    message = FakeMessage(f'@{BOT_USERNAME} кто знает сантехника?')
    llm = FakeLLM(reply='запасной ответ')
    agent = FakeAgent(AgentAnswer(text='', citations=[]))

    await call_handler(message, make_settings(), llm, agent)

    assert len(llm.calls) == 1
    assert message.replies == ['запасной ответ']
