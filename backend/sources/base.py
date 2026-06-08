"""Abstract base for all data sources."""
import asyncio
import logging
from abc import ABC, abstractmethod

from backend.data_bus import DataBus


class BaseSource(ABC):
    def __init__(self, bus: DataBus, config: dict,
                 sim_registry: dict | None = None):
        self.bus          = bus
        self.config       = config
        self.name         = config.get("name", self.__class__.__name__)
        self.log          = logging.getLogger(self.name)
        self._running     = False
        # sim_registry is a shared {name: bool} dict owned by main.py.
        # It lets the API toggle simulation at runtime without restarting.
        self._sim_registry: dict = sim_registry if sim_registry is not None else {}
        # Seed registry from config so YAML simulate: true still works
        if config.get("simulate", False):
            self._sim_registry[self.name] = True

    def is_simulating(self) -> bool:
        """True if this source is currently in simulation mode."""
        return self._sim_registry.get(self.name, False)

    def set_simulating(self, enabled: bool) -> None:
        """Toggle simulation mode. Takes effect on the next loop iteration."""
        self._sim_registry[self.name] = enabled
        self._publish_sim(enabled)
        self.log.info("Source '%s' simulation %s",
                      self.name, "ENABLED" if enabled else "DISABLED")

    # ── Health / simulation signals ───────────────────────────────────────────

    def _publish_health(self, ok: bool) -> None:
        key = "_src_" + self.name.replace(" ", "_")
        self.bus.publish(key, 1 if ok else 0, "")

    def _publish_sim(self, simulating: bool) -> None:
        key = "_sim_" + self.name.replace(" ", "_")
        self.bus.publish(key, 1 if simulating else 0, "")

    # ── Run loop ──────────────────────────────────────────────────────────────

    async def run(self) -> None:
        self._running = True
        self.log.info("Starting source: %s", self.name)
        self._publish_health(True)
        self._publish_sim(self.is_simulating())
        while self._running:
            try:
                await self._read_loop()
                self._publish_health(True)
            except Exception as exc:
                self.log.error("Source error (%s): %s — retrying in 5s", self.name, exc)
                self._publish_health(False)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self._running = False
        self._publish_health(False)

    @abstractmethod
    async def _read_loop(self) -> None:
        """Open hardware, read forever, call self.bus.publish(). Re-raise to trigger retry."""
