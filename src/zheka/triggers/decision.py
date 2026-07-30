import random
from collections.abc import Callable
from datetime import UTC, datetime

from aiogram.types import Message
from loguru import logger

from zheka.config import Settings
from zheka.constants import STALE_MESSAGE_SECONDS
from zheka.ratelimit import RateLimiter


def is_stale(
    message_date: datetime,
    now: datetime | None = None,
) -> bool:
    """Устарело ли сообщение: старше STALE_MESSAGE_SECONDS.

    Такие сообщения приходят пачкой после простоя бота (очередь
    Telegram живёт до 24 часов) — отвечать на них поздно, они
    только сохраняются в контекст.
    """
    if now is None:
        now = datetime.now(UTC)
    age = (now - message_date).total_seconds()
    return age > STALE_MESSAGE_SECONDS


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
    mention = _is_mention(text, bot_username)
    reply_to_bot = _is_reply_to_bot(message, bot_id)
    keyword = _has_keyword(text, settings.keywords)
    random_hit = random_func() < settings.reply_probability_for(
        message.chat.id
    )
    is_candidate = mention or reply_to_bot or keyword or random_hit
    if is_candidate:
        logger.info(
            'Триггер ответа: chat={} mention={} reply={} keyword={} '
            'random={}',
            message.chat.id,
            mention,
            reply_to_bot,
            keyword,
            random_hit,
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
