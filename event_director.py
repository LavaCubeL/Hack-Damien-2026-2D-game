"""Threaded random-event scheduler.

The director only communicates with Game through a queue, which keeps all
Pygame object access on the main thread.
"""

from __future__ import annotations

import queue
import random
import threading
import time


class EventDirector:
    """Background event scheduler.

    This thread never touches Pygame objects. It only asks the main loop to
    consider a random event, which keeps rendering and sprite state stable.
    """

    def __init__(self, outbox: queue.Queue[str]) -> None:
        self.outbox = outbox
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            time.sleep(random.uniform(1.2, 2.8))
            try:
                self.outbox.put_nowait("random_event")
            except queue.Full:
                pass
