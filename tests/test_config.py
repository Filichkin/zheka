from typing import Any

from zheka.config import Settings


def make_settings(**overrides: Any) -> Settings:
    params: dict[str, Any] = {
        'TG_BOT_TOKEN': 'test-token',
        'OPEN_AI_KEY': 'test-key',
        'llm_model': 'test-model',
    }
    params.update(overrides)
    return Settings(_env_file=None, **params)


def test_allowed_chats_parsed_from_csv() -> None:
    settings = make_settings(allowed_chat_ids='-1001103887282, -1001687070692')

    assert settings.allowed_chats == {-1001103887282, -1001687070692}


def test_whitelisted_chat_is_allowed() -> None:
    settings = make_settings(allowed_chat_ids='-100')

    assert settings.chat_allowed(-100)
    assert not settings.chat_allowed(-200)


def test_empty_whitelist_allows_any_chat() -> None:
    settings = make_settings(allowed_chat_ids='')

    assert settings.chat_allowed(-100500)
