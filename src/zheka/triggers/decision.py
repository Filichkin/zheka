import random
from collections.abc import Callable

from aiogram.types import Message

from zheka.config import Settings
from zheka.ratelimit import RateLimiter


def should_respond(
    message: Message,
    bot_id: int,
    bot_username: str,
    settings: Settings,
    rate_limiter: RateLimiter,
    random_func: Callable[[], float] = random.random,
) -> bool:
    """Решает, отвечать ли на сообщение.

    Кандидат на ответ: упоминание бота, reply на его сообщение,
    ключевое слово или случайный шанс. Кандидат дополнительно
    проходит проверку лимитов частоты.
    """
    text = (message.text or '').lower()
    is_candidate = (
        _is_mention(text, bot_username)
        or _is_reply_to_bot(message, bot_id)
        or _has_keyword(text, settings.keywords)
        or random_func() < settings.reply_probability
    )
    if not is_candidate:
        return False
    return rate_limiter.allow(message.chat.id)


def _is_mention(text: str, bot_username: str) -> bool:
    return bool(bot_username) and f'@{bot_username.lower()}' in text


def _is_reply_to_bot(message: Message, bot_id: int) -> bool:
    reply = message.reply_to_message
    return (
        reply is not None
        and reply.from_user is not None
        and reply.from_user.id == bot_id
    )


def _has_keyword(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
