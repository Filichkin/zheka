from pathlib import Path

from loguru import logger

from zheka.logger import setup_logging


def test_setup_logging_writes_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / 'app.log'

    setup_logging(level='INFO', log_file=str(log_file))
    logger.info('файловый sink работает')
    logger.remove()

    assert 'файловый sink работает' in log_file.read_text(encoding='utf-8')


def test_setup_logging_respects_level(tmp_path: Path) -> None:
    log_file = tmp_path / 'app.log'

    setup_logging(level='INFO', log_file=str(log_file))
    logger.debug('отладка не должна попасть в файл')
    logger.remove()

    assert 'отладка' not in log_file.read_text(encoding='utf-8')
