"""Clocks: the real one and a fake one for tests."""

import time


class Clock:
    """Wall clock in seconds since the epoch."""

    def now(self):
        return time.time()

    def sleep(self, seconds):
        time.sleep(seconds)


class FakeClock(Clock):
    """A clock that only moves when told to."""

    def __init__(self, start=0.0):
        self.current = start

    def now(self):
        return self.current

    def sleep(self, seconds):
        self.current += seconds
