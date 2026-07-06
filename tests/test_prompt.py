from zheka.constants import CONTEXT_HEADER
from zheka.context import BufferedMessage
from zheka.llm import build_messages


PERSONA = 'Ты — Жека.'


def test_system_message_first_trigger_last() -> None:
    recent = [BufferedMessage(author='Alice', text='привет')]

    messages = build_messages(PERSONA, recent, 'как дела?')

    assert messages[0] == {'role': 'system', 'content': PERSONA}
    assert messages[-1] == {'role': 'user', 'content': 'как дела?'}
    assert len(messages) == 3


def test_context_is_compact_user_message() -> None:
    recent = [
        BufferedMessage(author='Alice', text='привет'),
        BufferedMessage(author='Bob', text='здорово'),
    ]

    messages = build_messages(PERSONA, recent, 'что нового?')

    context = messages[1]
    assert context['role'] == 'user'
    assert context['content'] == (
        f'{CONTEXT_HEADER}\nAlice: привет\nBob: здорово'
    )


def test_empty_context_skips_context_message() -> None:
    messages = build_messages(PERSONA, [], 'эй!')

    assert len(messages) == 2
    assert messages[0]['role'] == 'system'
    assert messages[1] == {'role': 'user', 'content': 'эй!'}
