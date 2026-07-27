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
    settings = make_settings(allowed_chat_ids='-1001000000001, -1001000000002')

    assert settings.allowed_chats == {-1001000000001, -1001000000002}


def test_whitelisted_chat_is_allowed() -> None:
    settings = make_settings(allowed_chat_ids='-100')

    assert settings.chat_allowed(-100)
    assert not settings.chat_allowed(-200)


def test_empty_whitelist_allows_any_chat() -> None:
    settings = make_settings(allowed_chat_ids='')

    assert settings.chat_allowed(-100500)


def test_allowed_topics_parsed_from_csv() -> None:
    settings = make_settings(allowed_topic_ids='-100:12, -100:34')

    assert settings.allowed_topics == {(-100, 12), (-100, 34)}


def test_topic_in_whitelist_is_allowed() -> None:
    settings = make_settings(allowed_topic_ids='-100:12')

    assert settings.topic_allowed(-100, 12)
    assert not settings.topic_allowed(-100, 34)


def test_chat_without_topic_entries_allows_any_topic() -> None:
    settings = make_settings(allowed_topic_ids='-200:12')

    assert settings.topic_allowed(-100, 999)


def test_general_topic_always_allowed() -> None:
    settings = make_settings(allowed_topic_ids='-100:12')

    assert settings.topic_allowed(-100, None)


def test_persona_paths_parsed_from_csv() -> None:
    settings = make_settings(
        chat_persona_paths='-100:infra/a.txt, -200:infra/b.txt'
    )

    assert settings.persona_paths == {-100: 'infra/a.txt', -200: 'infra/b.txt'}


def test_reply_probabilities_parsed_and_capped() -> None:
    settings = make_settings(chat_reply_probabilities='-100:0.5, -200:0.95')

    assert settings.reply_probabilities == {-100: 0.5, -200: 0.8}


def test_reply_probability_for_uses_override_or_default() -> None:
    settings = make_settings(
        reply_probability=0.02, chat_reply_probabilities='-100:0.8'
    )

    assert settings.reply_probability_for(-100) == 0.8
    assert settings.reply_probability_for(-999) == 0.02


def test_search_chats_parsed_from_csv() -> None:
    settings = make_settings(SEARCH_CHAT_IDS='-100, -200')

    assert settings.search_chats == {-100, -200}


def test_search_allowed_requires_mcp_url_and_chat() -> None:
    settings = make_settings(
        RAG_MCP_URL='http://127.0.0.1:8765/mcp',
        SEARCH_CHAT_IDS='-100',
    )

    assert settings.search_allowed(-100)
    assert not settings.search_allowed(-200)


def test_search_disabled_without_mcp_url() -> None:
    settings = make_settings(RAG_MCP_URL='', SEARCH_CHAT_IDS='-100')

    assert not settings.search_allowed(-100)


def test_search_disabled_with_empty_chat_list() -> None:
    settings = make_settings(
        RAG_MCP_URL='http://127.0.0.1:8765/mcp',
        SEARCH_CHAT_IDS='',
    )

    assert not settings.search_allowed(-100)
