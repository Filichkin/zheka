"""Мост между fastmcp.Client и OpenAI tool-calling."""

import json
from typing import Any

from fastmcp import Client
from fastmcp.client.client import CallToolResult


def get_field(obj: Any, name: str) -> Any:
    """Достаёт поле из dict или объекта (data бывает и тем, и тем)."""
    return obj[name] if isinstance(obj, dict) else getattr(obj, name)


async def load_tool_schemas(client: Client) -> list[dict[str, Any]]:
    """Забирает список MCP-инструментов в формате OpenAI tools."""
    tools = await client.list_tools()
    return [
        {
            'type': 'function',
            'function': {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.inputSchema,
            },
        }
        for tool in tools
    ]


def extract_hits(result: CallToolResult) -> list[Any]:
    """Достаёт список найденных чанков (hits) из результата вызова."""
    if result.data is None:
        return []
    return list(get_field(result.data, 'hits') or [])


def result_to_tool_message(result: CallToolResult) -> str:
    """Сериализует результат вызова инструмента для ответа LLM."""
    if result.structured_content is not None:
        return json.dumps(
            result.structured_content, default=str, ensure_ascii=False
        )
    text_parts = [
        block.text for block in result.content if hasattr(block, 'text')
    ]
    return '\n'.join(text_parts)
