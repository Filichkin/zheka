from types import SimpleNamespace
from typing import Any

from zheka.config import Settings
from zheka.ratelimit import RateLimiter
from zheka.triggers import should_respond


BOT_ID = 42
BOT_USERNAME = 'zheka_bot'


def make_settings(**overrides: Any) -> Settings:
    params: dict[str, Any] = {
        'TG_BOT_TOKEN': 'test-token',
        'OPEN_AI_KEY': 'test-key',
        'llm_model': 'test-model',
        'reply_probability': 0.0,
        'trigger_keywords': '',
    }
    params.update(overrides)
    return Settings(_env_file=None, **params)


def make_message(
    text: str,
    chat_id: int = 1,
    reply_to_bot: bool = False,
) -> Any:
    reply = None
    if reply_to_bot:
        reply = SimpleNamespace(from_user=SimpleNamespace(id=BOT_ID))
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        reply_to_message=reply,
    )


def make_limiter(allow: bool = True) -> RateLimiter:
    limiter = RateLimiter(max_per_minute=1 if allow else 0, max_per_day=100)
    return limiter


def test_mention_triggers_response() -> None:
    message = make_message(f'привет, @{BOT_USERNAME}!')

    assert should_respond(
        message, BOT_ID, BOT_USERNAME, make_settings(), make_limiter()
    )


def test_reply_to_bot_triggers_response() -> None:
    message = make_message('согласен', reply_to_bot=True)

    assert should_respond(
        message, BOT_ID, BOT_USERNAME, make_settings(), make_limiter()
    )


def test_keyword_triggers_response() -> None:
    settings = make_settings(trigger_keywords='жека, бот')
    message = make_message('Жека, ты тут?')

    assert should_respond(
        message, BOT_ID, BOT_USERNAME, settings, make_limiter()
    )


def test_plain_message_is_ignored() -> None:
    message = make_message('обычное сообщение')

    assert not should_respond(
        message, BOT_ID, BOT_USERNAME, make_settings(), make_limiter()
    )


def test_probability_one_always_responds() -> None:
    settings = make_settings(reply_probability=1.0)
    message = make_message('обычное сообщение')

    assert should_respond(
        message,
        BOT_ID,
        BOT_USERNAME,
        settings,
        make_limiter(),
        random_func=lambda: 0.5,
    )


def test_exhausted_limit_blocks_mention() -> None:
    message = make_message(f'@{BOT_USERNAME}, ответь')

    assert not should_respond(
        message,
        BOT_ID,
        BOT_USERNAME,
        make_settings(),
        make_limiter(allow=False),
    )
