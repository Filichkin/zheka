from zheka.context import BufferedMessage, ContextBuffer


def test_empty_chat_returns_empty_list() -> None:
    buffer = ContextBuffer(maxlen=3)

    assert buffer.get_recent(1) == []


def test_keeps_chronological_order() -> None:
    buffer = ContextBuffer(maxlen=3)

    buffer.add(1, 'Alice', 'first')
    buffer.add(1, 'Bob', 'second')

    assert buffer.get_recent(1) == [
        BufferedMessage(author='Alice', text='first'),
        BufferedMessage(author='Bob', text='second'),
    ]


def test_evicts_oldest_when_full() -> None:
    buffer = ContextBuffer(maxlen=2)

    buffer.add(1, 'Alice', 'first')
    buffer.add(1, 'Bob', 'second')
    buffer.add(1, 'Carol', 'third')

    recent = buffer.get_recent(1)
    assert len(recent) == 2
    assert recent == [
        BufferedMessage(author='Bob', text='second'),
        BufferedMessage(author='Carol', text='third'),
    ]


def test_chats_are_isolated() -> None:
    buffer = ContextBuffer(maxlen=3)

    buffer.add(1, 'Alice', 'in chat one')
    buffer.add(2, 'Bob', 'in chat two')

    assert buffer.get_recent(1) == [
        BufferedMessage(author='Alice', text='in chat one'),
    ]
    assert buffer.get_recent(2) == [
        BufferedMessage(author='Bob', text='in chat two'),
    ]
