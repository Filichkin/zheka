import inspect
import logging
import sys

from loguru import logger


LOG_FORMAT = (
    '<green>{time:YYYY-MM-DD HH:mm:ss}</green> '
    '| <level>{level: <8}</level> '
    '| <cyan>{name}</cyan>:<cyan>{function}</cyan> '
    '- <level>{message}</level>'
)


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging records (aiogram, openai) to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (
            depth == 0 or frame.f_code.co_filename == logging.__file__
        ):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = 'INFO') -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, format=LOG_FORMAT)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
