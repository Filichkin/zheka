import time
from collections import deque
from collections.abc import Callable
from datetime import date

from zheka.constants import MINUTE_WINDOW_SECONDS


class RateLimiter:
    """Ограничитель частоты: лимит на чат в минуту и общий в день."""

    def __init__(
        self,
        max_per_minute: int,
        max_per_day: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._max_per_minute = max_per_minute
        self._max_per_day = max_per_day
        self._clock = clock
        self._per_chat: dict[int, deque[float]] = {}
        self._day: date = date.fromtimestamp(clock())
        self._replies_today = 0

    def allow(self, chat_id: int) -> bool:
        """Можно ли сейчас ответить в этом чате."""
        now = self._clock()
        self._reset_day_if_changed(now)
        if self._replies_today >= self._max_per_day:
            return False
        timestamps = self._per_chat.get(chat_id)
        if timestamps is None:
            return self._max_per_minute > 0
        self._trim_window(timestamps, now)
        return len(timestamps) < self._max_per_minute

    def register(self, chat_id: int) -> None:
        """Отметить состоявшийся ответ в чате."""
        now = self._clock()
        self._reset_day_if_changed(now)
        timestamps = self._per_chat.setdefault(chat_id, deque())
        self._trim_window(timestamps, now)
        timestamps.append(now)
        self._replies_today += 1

    def _reset_day_if_changed(self, now: float) -> None:
        today = date.fromtimestamp(now)
        if today != self._day:
            self._day = today
            self._replies_today = 0

    def _trim_window(self, timestamps: deque[float], now: float) -> None:
        while timestamps and now - timestamps[0] >= MINUTE_WINDOW_SECONDS:
            timestamps.popleft()
