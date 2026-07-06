from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from zheka.constants import CONTEXT_CLOSE, CONTEXT_HEADER, CONTEXT_OPEN
from zheka.context import BufferedMessage


def load_persona(path: str) -> str:
    """Читает характер бота из текстового файла."""
    return Path(path).read_text(encoding='utf-8').strip()


def _flatten(value: str) -> str:
    """Схлопывает переносы строк и лишние пробелы в один пробел.

    Не даёт подделать чужую реплику отдельной строкой внутри
    сообщения или имени автора.
    """
    return ' '.join(value.split())


def build_messages(
    persona: str,
    recent_messages: list[BufferedMessage],
    trigger_text: str,
) -> list[ChatCompletionMessageParam]:
    """Собирает messages для Chat Completions.

    Персона идёт системным сообщением, контекст чата — одним
    user-сообщением внутри явных разделителей (защита от подмены
    ролей), триггер — последним.
    """
    messages: list[ChatCompletionMessageParam] = [
        {'role': 'system', 'content': persona},
    ]
    if recent_messages:
        context_lines = '\n'.join(
            f'{_flatten(message.author)}: {_flatten(message.text)}'
            for message in recent_messages
        )
        messages.append(
            {
                'role': 'user',
                'content': (
                    f'{CONTEXT_HEADER}\n'
                    f'{CONTEXT_OPEN}\n'
                    f'{context_lines}\n'
                    f'{CONTEXT_CLOSE}'
                ),
            }
        )
    messages.append({'role': 'user', 'content': trigger_text})
    return messages
