import inspect
import logging
import os
import sys

from loguru import logger

from zheka.constants import LOG_FORMAT


class InterceptHandler(logging.Handler):
    """Перенаправляет записи stdlib logging (aiogram, openai) в loguru."""

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


def setup_logging(
    level: str | None = None,
    log_file: str = 'logs/app.log',
) -> None:
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    logger.remove()
    logger.add(sys.stderr, level=level, format=LOG_FORMAT)
    logger.add(
        log_file,
        level=level,
        format=LOG_FORMAT,
        rotation='10 MB',
        retention='14 days',
        compression='gz',
        encoding='utf-8',
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
