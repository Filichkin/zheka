from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import ErrorEvent, Message
from loguru import logger

from zheka.config import Settings
from zheka.constants import TELEGRAM_MESSAGE_LIMIT
from zheka.context import ContextBuffer
from zheka.llm import LLMClient, build_messages
from zheka.ratelimit import RateLimiter
from zheka.triggers import should_respond


router = Router(name='group_messages')


@router.errors()
async def on_handler_error(event: ErrorEvent) -> None:
    """Ошибка на одном сообщении не должна останавливать бота."""
    logger.exception('Unhandled error in handler: {}', event.exception)


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def on_group_message(
    message: Message,
    buffer: ContextBuffer,
    settings: Settings,
    rate_limiter: RateLimiter,
    llm: LLMClient,
    persona: str,
    bot_id: int,
    bot_username: str,
    bot_name: str,
) -> None:
    author = message.from_user.full_name if message.from_user else 'unknown'
    text = message.text or ''
    chat_id = message.chat.id
    logger.info('chat={} author={} text={}', chat_id, author, text)

    recent = buffer.get_recent(chat_id)
    buffer.add(chat_id, author, text)

    if not should_respond(
        message, bot_id, bot_username, settings, rate_limiter
    ):
        return

    logger.info('Generating reply in chat={}', chat_id)
    messages = build_messages(persona, recent, f'{author}: {text}')
    reply = await llm.generate(messages)
    if not reply:
        logger.warning('No reply generated for chat={}', chat_id)
        return

    reply = reply[:TELEGRAM_MESSAGE_LIMIT]
    try:
        await message.reply(reply)
    except TelegramRetryAfter as error:
        logger.warning(
            'Telegram rate limit in chat={}, skipping reply (retry_after={}s)',
            chat_id,
            error.retry_after,
        )
        return
    except TelegramAPIError as error:
        logger.error('Failed to send reply in chat={}: {}', chat_id, error)
        return
    rate_limiter.register(chat_id)
    buffer.add(chat_id, bot_name, reply)
    logger.info('Replied in chat={}: {}', chat_id, reply)
