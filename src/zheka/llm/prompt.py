from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from zheka.constants import CONTEXT_HEADER
from zheka.context import BufferedMessage


def load_persona(path: str) -> str:
    """Читает характер бота из текстового файла."""
    return Path(path).read_text(encoding='utf-8').strip()


def build_messages(
    persona: str,
    recent_messages: list[BufferedMessage],
    trigger_text: str,
) -> list[ChatCompletionMessageParam]:
    """Собирает messages для Chat Completions.

    Персона идёт системным сообщением, контекст чата — одним
    компактным user-сообщением, триггер — последним.
    """
    messages: list[ChatCompletionMessageParam] = [
        {'role': 'system', 'content': persona},
    ]
    if recent_messages:
        context_lines = '\n'.join(
            f'{message.author}: {message.text}' for message in recent_messages
        )
        messages.append(
            {
                'role': 'user',
                'content': f'{CONTEXT_HEADER}\n{context_lines}',
            }
        )
    messages.append({'role': 'user', 'content': trigger_text})
    return messages
