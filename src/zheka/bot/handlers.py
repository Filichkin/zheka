from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import ChatMemberUpdated, ErrorEvent, Message
from loguru import logger

from zheka.config import Settings
from zheka.constants import TELEGRAM_MESSAGE_LIMIT
from zheka.context import ContextBuffer
from zheka.llm import LLMClient, build_messages
from zheka.ratelimit import RateLimiter
from zheka.triggers import is_stale, should_respond


router = Router(name='group_messages')


@router.errors()
async def on_handler_error(event: ErrorEvent) -> None:
    """Ошибка на одном сообщении не должна останавливать бота."""
    logger.exception('Unhandled error in handler: {}', event.exception)


async def _leave_chat_quietly(bot: Bot, chat_id: int) -> None:
    """Выходит из чата; «уже не участник» — не ошибка, цель достигнута."""
    try:
        await bot.leave_chat(chat_id)
    except TelegramAPIError as error:
        logger.warning('Could not leave chat={}: {}', chat_id, error)


@router.my_chat_member()
async def on_bot_membership_change(
    event: ChatMemberUpdated,
    bot: Bot,
    settings: Settings,
) -> None:
    """Логирует добавления/удаления бота и уходит из чужих чатов."""
    chat = event.chat
    status = event.new_chat_member.status
    logger.info(
        'Bot membership change: chat={} title={!r} status={}',
        chat.id,
        chat.title,
        status,
    )
    if chat.type == ChatType.PRIVATE:
        return
    if status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        return
    if not settings.chat_allowed(chat.id):
        logger.warning(
            'Chat {} ({!r}) is not whitelisted, leaving',
            chat.id,
            chat.title,
        )
        await _leave_chat_quietly(bot, chat.id)


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def on_group_message(
    message: Message,
    bot: Bot,
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

    if not settings.chat_allowed(chat_id):
        logger.warning(
            'Message from non-whitelisted chat={}, leaving', chat_id
        )
        await _leave_chat_quietly(bot, chat_id)
        return

    logger.info('chat={} author={} text={}', chat_id, author, text)

    recent = buffer.get_recent(chat_id)
    buffer.add(chat_id, author, text)

    if is_stale(message.date):
        logger.info(
            'Пропускаю устаревшее сообщение в чате {} (отправлено {})',
            chat_id,
            message.date,
        )
        return

    if not should_respond(
        message, bot_id, bot_username, settings, rate_limiter
    ):
        return

    logger.info('Generating reply in chat={}', chat_id)
    trigger_author = ' '.join(author.split())
    messages = build_messages(persona, recent, f'{trigger_author}: {text}')
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
