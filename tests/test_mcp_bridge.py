import json
from types import SimpleNamespace
from typing import Any

import pytest

from zheka.mcp import (
    build_message_link,
    extract_hits,
    get_field,
    load_tool_schemas,
    result_to_tool_message,
)


class FakeClient:
    """Клиент с одним инструментом для проверки конвертации схем."""

    async def list_tools(self) -> list[Any]:
        return [
            SimpleNamespace(
                name='search_messages',
                description='Поиск по чатам',
                inputSchema={'type': 'object', 'properties': {}},
            )
        ]


def make_result(
    data: Any = None,
    structured_content: dict[str, Any] | None = None,
    content: list[Any] | None = None,
) -> Any:
    return SimpleNamespace(
        data=data,
        structured_content=structured_content,
        content=content or [],
    )


def test_get_field_from_dict_and_object() -> None:
    assert get_field({'channel': '-100'}, 'channel') == '-100'
    assert get_field(SimpleNamespace(channel='-100'), 'channel') == '-100'


@pytest.mark.asyncio
async def test_load_tool_schemas_converts_to_openai_format() -> None:
    schemas = await load_tool_schemas(FakeClient())

    assert schemas == [
        {
            'type': 'function',
            'function': {
                'name': 'search_messages',
                'description': 'Поиск по чатам',
                'parameters': {'type': 'object', 'properties': {}},
            },
        }
    ]


def test_extract_hits_from_dict_data() -> None:
    result = make_result(data={'hits': [{'chunk_id': 1}]})

    assert extract_hits(result) == [{'chunk_id': 1}]


def test_extract_hits_from_object_data() -> None:
    hit = SimpleNamespace(chunk_id=1)
    result = make_result(data=SimpleNamespace(hits=[hit]))

    assert extract_hits(result) == [hit]


def test_extract_hits_without_data() -> None:
    assert extract_hits(make_result(data=None)) == []


def test_extract_hits_with_empty_hits() -> None:
    assert extract_hits(make_result(data={'hits': None})) == []


def test_result_to_tool_message_prefers_structured_content() -> None:
    result = make_result(
        structured_content={'count': 1, 'query': 'бензин'},
        content=[SimpleNamespace(text='ignored')],
    )

    message = result_to_tool_message(result)

    assert json.loads(message) == {'count': 1, 'query': 'бензин'}


def test_result_to_tool_message_falls_back_to_text_blocks() -> None:
    result = make_result(
        content=[
            SimpleNamespace(text='строка 1'),
            SimpleNamespace(no_text=True),
            SimpleNamespace(text='строка 2'),
        ],
    )

    assert result_to_tool_message(result) == 'строка 1\nстрока 2'


def test_link_for_private_supergroup() -> None:
    link = build_message_link('-1001103887282', 42)

    assert link == 'https://t.me/c/1103887282/42'


def test_link_for_forum_topic_includes_topic_id() -> None:
    link = build_message_link('-1001103887282', 303991, topic_id=203154)

    assert link == 'https://t.me/c/1103887282/203154/303991'


def test_link_for_public_username() -> None:
    link = build_message_link('@oleg_payload', 7)

    assert link == 'https://t.me/oleg_payload/7'


def test_link_for_public_forum_topic() -> None:
    link = build_message_link('@some_forum', 7, topic_id=3)

    assert link == 'https://t.me/some_forum/3/7'


def test_link_for_unknown_format_is_none() -> None:
    assert build_message_link('12345', 1) is None
    assert build_message_link('-100abc', 1, topic_id=2) is None
