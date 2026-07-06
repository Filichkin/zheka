from zheka.ratelimit import RateLimiter


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_until_minute_limit() -> None:
    clock = FakeClock()
    limiter = RateLimiter(max_per_minute=2, max_per_day=100, clock=clock)

    assert limiter.allow(1)
    limiter.register(1)
    assert limiter.allow(1)
    limiter.register(1)

    assert not limiter.allow(1)


def test_minute_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(max_per_minute=1, max_per_day=100, clock=clock)

    limiter.register(1)
    assert not limiter.allow(1)

    clock.advance(61)
    assert limiter.allow(1)


def test_chats_have_independent_minute_limits() -> None:
    clock = FakeClock()
    limiter = RateLimiter(max_per_minute=1, max_per_day=100, clock=clock)

    limiter.register(1)
    assert not limiter.allow(1)
    assert limiter.allow(2)


def test_daily_limit_is_global() -> None:
    clock = FakeClock()
    limiter = RateLimiter(max_per_minute=100, max_per_day=2, clock=clock)

    limiter.register(1)
    limiter.register(2)

    assert not limiter.allow(3)


def test_daily_limit_resets_next_day() -> None:
    clock = FakeClock()
    limiter = RateLimiter(max_per_minute=100, max_per_day=1, clock=clock)

    limiter.register(1)
    assert not limiter.allow(1)

    clock.advance(24 * 60 * 60)
    assert limiter.allow(1)
