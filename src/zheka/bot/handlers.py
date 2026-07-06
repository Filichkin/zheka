from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message
from loguru import logger

from zheka.context import ContextBuffer


router = Router(name='group_messages')


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def on_group_message(
    message: Message,
    buffer: ContextBuffer,
) -> None:
    author = message.from_user.full_name if message.from_user else 'unknown'
    text = message.text or ''
    logger.info(
        'chat={} author={} text={}',
        message.chat.id,
        author,
        text,
    )
    buffer.add(message.chat.id, author, text)
