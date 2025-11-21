from collections import deque
from typing import Callable


class CallbackQueue:
    """Simplistic callback queue that runs strictly in sync. This will make sure that
    callbacks are called in the order they were added even if callbacks are trigegred by
    a callback."""

    def __init__(self):
        self._callbacks: deque[Callable] = deque()
        self._consuming = False

    def add_callbacks(self, callbacks: list[Callable]):
        self._callbacks.extend(callbacks)
        if not self._consuming:
            self.consume()

    def consume(self):
        self._consuming = True
        while self._callbacks:
            callback = self._callbacks.popleft()
            callback()
        self._consuming = False
