import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from zheka.bot.handlers import router
from zheka.config import Settings
from zheka.context import ContextBuffer
from zheka.logger import setup_logging


async def run() -> None:
    settings = Settings()
    bot = Bot(token=settings.bot_token)
    buffer = ContextBuffer(maxlen=settings.context_window)
    dispatcher = Dispatcher(buffer=buffer)
    dispatcher.include_router(router)

    logger.info('Starting polling')
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    setup_logging()
    asyncio.run(run())


if __name__ == '__main__':
    main()
