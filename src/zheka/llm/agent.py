"""Агент: tool-calling цикл поверх MCP-инструментов поиска."""

import json
from collections.abc import Callable
from typing import Any

from fastmcp import Client
from loguru import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from zheka.constants import (
    CITATIONS_LIMIT,
    MAX_COMPLETION_TOKENS,
    MAX_TOOL_ROUNDS,
    MCP_TIMEOUT_SECONDS,
)
from zheka.llm.helpers import hit_to_citation
from zheka.llm.schemas import AgentAnswer, Citation
from zheka.mcp import (
    extract_hits,
    get_field,
    load_tool_schemas,
    result_to_tool_message,
)


class SearchAgent:
    """LLM с MCP-инструментами: поиск по истории чата или беседа.

    Клиент MCP создаётся на каждый вопрос: сервер — необязательная
    зависимость, его недоступность не должна ломать бота. Любая
    ошибка агента превращается в None — сигнал вызывающему коду
    ответить обычным путём персоны.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        mcp_url: str,
        model: str,
        client_factory: Callable[[], Client] | None = None,
    ) -> None:
        self._openai = openai_client
        self._model = model
        self._client_factory = client_factory or (
            lambda: Client(mcp_url, timeout=MCP_TIMEOUT_SECONDS)
        )
        self._tools: list[dict[str, Any]] | None = None

    async def ask(
        self,
        messages: list[ChatCompletionMessageParam],
        chat_id: int,
    ) -> AgentAnswer | None:
        """Отвечает с опциональным поиском; None — откат на персону."""
        try:
            async with self._client_factory() as mcp:
                return await self._run(mcp, list(messages), chat_id)
        except Exception as error:
            logger.warning(
                'Агент недоступен ({}), откат на обычный ответ', error
            )
            return None

    async def _tool_schemas(self, mcp: Client) -> list[dict[str, Any]]:
        """Загружает и кэширует схемы MCP-инструментов для OpenAI."""
        if self._tools is None:
            self._tools = await load_tool_schemas(mcp)
        return self._tools

    async def _run(
        self,
        mcp: Client,
        messages: list[Any],
        chat_id: int,
    ) -> AgentAnswer | None:
        """Гоняет цикл LLM -> инструменты до финального ответа."""
        tools = await self._tool_schemas(mcp)
        citations: dict[tuple[str, int], Citation] = {}
        searched = False

        for round_num in range(1, MAX_TOOL_ROUNDS + 1):
            logger.info(
                'Агент: раунд {}/{} в чате {}',
                round_num,
                MAX_TOOL_ROUNDS,
                chat_id,
            )
            completion = await self._openai.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )
            reply = completion.choices[0].message

            if not reply.tool_calls:
                return AgentAnswer(
                    text=(reply.content or '').strip(),
                    citations=list(citations.values())[:CITATIONS_LIMIT],
                    searched=searched,
                )

            messages.append(
                {
                    'role': 'assistant',
                    'content': reply.content,
                    'tool_calls': [
                        {
                            'id': call.id,
                            'type': 'function',
                            'function': {
                                'name': call.function.name,
                                'arguments': call.function.arguments,
                            },
                        }
                        for call in reply.tool_calls
                    ],
                }
            )
            for call in reply.tool_calls:
                searched = True
                content, hits = await self._call_tool(
                    mcp,
                    call.function.name,
                    call.function.arguments,
                    chat_id,
                )
                for hit in hits:
                    citation = hit_to_citation(hit)
                    key = (
                        citation.channel,
                        get_field(hit, 'msg_id_start'),
                    )
                    citations[key] = citation
                messages.append(
                    {
                        'role': 'tool',
                        'tool_call_id': call.id,
                        'content': content,
                    }
                )

        logger.warning(
            'Агент: лимит {} раундов исчерпан в чате {}',
            MAX_TOOL_ROUNDS,
            chat_id,
        )
        return None

    async def _call_tool(
        self,
        mcp: Client,
        name: str,
        arguments_json: str,
        chat_id: int,
    ) -> tuple[str, list[Any]]:
        """Вызывает инструмент, вернув текст для LLM и найденные hits.

        channel принудительно подставляется из chat_id — поиск всегда
        ограничен историей текущего чата, независимо от решения LLM.
        topic_id удаляется: ищем по всем темам группы.
        """
        try:
            arguments = json.loads(arguments_json or '{}')
            arguments['channel'] = str(chat_id)
            arguments.pop('topic_id', None)
            logger.info(
                'Агент: вызываю {} с аргументами {}', name, arguments
            )
            result = await mcp.call_tool(name, arguments)
            hits = extract_hits(result)
            logger.info(
                'Агент: инструмент {} вернул {} результат(ов)',
                name,
                len(hits),
            )
            return result_to_tool_message(result), hits
        except Exception as error:
            logger.warning(
                'Ошибка вызова инструмента {}: {}', name, error
            )
            return f'Ошибка вызова инструмента: {error}', []
