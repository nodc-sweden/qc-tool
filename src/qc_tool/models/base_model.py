from collections import defaultdict
from typing import Callable, Iterable

from qc_tool.callback_queue import CallbackQueue


class BaseModel:
    def __init__(self, message_queue: CallbackQueue):
        self._message_queue = message_queue
        self._listeners = defaultdict(list)

    def register_listener(self, event: str | Iterable[str], callback: Callable[[], None]):
        if isinstance(event, str):
            event = [event]
        for event_name in event:
            self._listeners[event_name].append(callback)

    def _notify_listeners(self, event_name: str):
        self._message_queue.add_callbacks(self._listeners.get(event_name, []))
