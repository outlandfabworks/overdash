"""
Central in-memory signal store. Sources publish values; the WebSocket server
subscribes and batches them for broadcast. Thread-safe via asyncio only —
all callers must run in the same event loop.
"""
import asyncio
import time
from typing import Any


class DataBus:
    def __init__(self):
        self._signals: dict[str, dict] = {}
        self._queues: list[asyncio.Queue] = []

    def publish(self, signal: str, value: Any, unit: str = "") -> None:
        entry = {"value": value, "unit": unit, "ts": time.time()}
        self._signals[signal] = entry
        for q in self._queues:
            try:
                q.put_nowait({signal: entry})
            except asyncio.QueueFull:
                pass  # slow subscriber — drop rather than block

    def subscribe(self, maxsize: int = 256) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    def snapshot(self) -> dict:
        return dict(self._signals)
