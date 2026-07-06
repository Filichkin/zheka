from collections import deque
from typing import NamedTuple


class BufferedMessage(NamedTuple):
    author: str
    text: str


class ContextBuffer:
    """Скользящее окно последних сообщений по каждому чату, в памяти."""

    def __init__(self, maxlen: int) -> None:
        self._maxlen = maxlen
        self._chats: dict[int, deque[BufferedMessage]] = {}

    def add(self, chat_id: int, author: str, text: str) -> None:
        messages = self._chats.get(chat_id)
        if messages is None:
            messages = deque(maxlen=self._maxlen)
            self._chats[chat_id] = messages
        messages.append(BufferedMessage(author=author, text=text))

    def get_recent(self, chat_id: int) -> list[BufferedMessage]:
        return list(self._chats.get(chat_id, ()))
