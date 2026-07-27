import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from zheka.bot.handlers import router
from zheka.config import Settings
from zheka.context import ContextBuffer
from zheka.llm import (
    LLMClient,
    SearchAgent,
    SearchClassifier,
    load_persona,
)
from zheka.logger import setup_logging
from zheka.ratelimit import RateLimiter


def create_search_agent(
    settings: Settings,
    llm: LLMClient,
) -> tuple[SearchAgent | None, str, SearchClassifier | None]:
    """Собирает агента, инструкции и классификатор, если поиск
    включён в конфиге."""

    if not settings.mcp_url:
        return None, '', None
    agent = SearchAgent(llm.client, settings.mcp_url, settings.llm_model)
    instructions = load_persona(settings.agent_prompt_path)
    classifier = SearchClassifier(
        llm.client,
        settings.llm_model,
        load_persona(settings.classifier_prompt_path),
    )
    logger.info('Агент-поиск включён: {}', settings.mcp_url)
    return agent, instructions, classifier


async def run() -> None:
    settings = Settings()
    bot = Bot(token=settings.bot_token)
    me = await bot.me()
    logger.info('Бот @{} id={}', me.username, me.id)
    llm = LLMClient(settings)
    default_persona = load_persona(settings.persona_path)
    personas = {
        chat_id: load_persona(path)
        for chat_id, path in settings.persona_paths.items()
    }
    search_agent, agent_instructions, classifier = create_search_agent(
        settings, llm
    )
    dispatcher = Dispatcher(
        buffer=ContextBuffer(maxlen=settings.context_window),
        settings=settings,
        rate_limiter=RateLimiter(
            max_per_minute=settings.max_replies_per_minute,
            max_per_day=settings.max_replies_per_day,
        ),
        llm=llm,
        personas=personas,
        default_persona=default_persona,
        search_agent=search_agent,
        agent_instructions=agent_instructions,
        classifier=classifier,
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
