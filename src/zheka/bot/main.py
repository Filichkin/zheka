import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from zheka.bot.handlers import router
from zheka.config import Settings
from zheka.context import ContextBuffer
from zheka.llm import LLMClient, load_persona
from zheka.logger import setup_logging
from zheka.ratelimit import RateLimiter


async def run() -> None:
    settings = Settings()
    bot = Bot(token=settings.bot_token)
    me = await bot.me()
    logger.info('Бот @{} id={}', me.username, me.id)
    dispatcher = Dispatcher(
        buffer=ContextBuffer(maxlen=settings.context_window),
        settings=settings,
        rate_limiter=RateLimiter(
            max_per_minute=settings.max_replies_per_minute,
            max_per_day=settings.max_replies_per_day,
        ),
        llm=LLMClient(settings),
        persona=load_persona(settings.persona_path),
        bot_id=me.id,
        bot_username=me.username or '',
        bot_name=me.first_name,
    )
    dispatcher.include_router(router)

    logger.info('Запускаю polling')
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    setup_logging()
    asyncio.run(run())


if __name__ == '__main__':
    main()
