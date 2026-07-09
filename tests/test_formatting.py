from datetime import datetime

from zheka.constants import TELEGRAM_MESSAGE_LIMIT
from zheka.llm import AgentAnswer, Citation
from zheka.llm.formatting import render_answer
from zheka.llm.helpers import format_date


def make_citation(
    link: str | None = 'https://t.me/c/1103887282/42',
    topic_title: str | None = 'Общие вопросы',
    date: datetime | str | None = '2026-07-01T10:00:00+03:00',
) -> Citation:
    return Citation(
        channel='-1001103887282',
        topic_title=topic_title,
        date=date,
        link=link,
    )


def test_format_date_variants() -> None:
    assert format_date(None) is None
    assert format_date(datetime(2026, 7, 1, 10, 0)) == '2026-07-01'
    assert format_date('2026-07-01T10:00:00+03:00') == '2026-07-01'


def test_text_only_without_citations() -> None:
    answer = AgentAnswer(text='просто ответ')

    assert render_answer(answer) == 'просто ответ'


def test_sources_block_with_topic_and_date() -> None:
    answer = AgentAnswer(text='нашёл', citations=[make_citation()])

    rendered = render_answer(answer)

    assert rendered == (
        'Вот что я нашёл в истории чатов — может, вам поможет:\n'
        'нашёл\n\n'
        'Источники:\n'
        '1. Общие вопросы, 2026-07-01 — https://t.me/c/1103887282/42'
    )


def test_citation_without_topic_and_date_is_bare_link() -> None:
    citation = make_citation(topic_title=None, date=None)
    answer = AgentAnswer(text='нашёл', citations=[citation])

    assert render_answer(answer).endswith(
        '\n1. https://t.me/c/1103887282/42'
    )


def test_citations_without_link_are_skipped() -> None:
    answer = AgentAnswer(
        text='нашёл',
        citations=[make_citation(link=None), make_citation()],
    )

    rendered = render_answer(answer)

    assert rendered.count('https://') == 1
    assert '1. Общие вопросы' in rendered


def test_no_linked_citations_means_no_sources_block() -> None:
    answer = AgentAnswer(
        text='нашёл', citations=[make_citation(link=None)]
    )

    rendered = render_answer(answer)

    assert 'Источники:' not in rendered
    assert rendered.endswith('\nнашёл')


def test_no_prefix_without_citations() -> None:
    answer = AgentAnswer(text='просто болтаю')

    assert 'нашёл в истории' not in render_answer(answer)


def test_truncation_keeps_sources_intact() -> None:
    answer = AgentAnswer(
        text='х' * (TELEGRAM_MESSAGE_LIMIT + 100),
        citations=[make_citation()],
    )

    rendered = render_answer(answer)

    assert len(rendered) <= TELEGRAM_MESSAGE_LIMIT
    assert rendered.endswith('https://t.me/c/1103887282/42')
    assert 'Источники:' in rendered
