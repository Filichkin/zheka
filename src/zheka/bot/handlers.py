from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message
from loguru import logger


router = Router(name='group_messages')


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text,
)
async def on_group_message(message: Message) -> None:
    author = message.from_user.full_name if message.from_user else 'unknown'
    logger.info(
        'chat={} author={} text={}',
        message.chat.id,
        author,
        message.text,
    )
