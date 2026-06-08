"""
GPIO input source — reads optocoupler-isolated digital inputs via RPi.GPIO.

Config is loaded from configs/gpio_inputs.json at startup and can be
hot-reloaded via update_inputs() without restarting the backend.

Each input is active-low: GPIO pulled high to 3.3V; opto pulls low
when 12V signal is present → published as value 1 (active).

Default HAT pin map (used if gpio_inputs.json doesn't exist):
  GPIO4  → IN1    GPIO17 → IN2    GPIO27 → IN3    GPIO22 → IN4
  GPIO5  → IN5    GPIO6  → IN6    GPIO13 → IN7    GPIO19 → IN8
"""
import asyncio
import json
import logging
from pathlib import Path

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("gpio_inputs")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_FILE  = _PROJECT_ROOT / "configs" / "gpio_inputs.json"

_DEFAULT_INPUTS = [
    {"gpio": 4,  "signal": "left_turn",      "label": "Left Turn Signal"},
    {"gpio": 17, "signal": "right_turn",     "label": "Right Turn Signal"},
    {"gpio": 27, "signal": "high_beam",      "label": "High Beam"},
    {"gpio": 22, "signal": "parking_lights", "label": "Parking Lights"},
    {"gpio": 5,  "signal": "hazards",        "label": "Hazard Lights"},
    {"gpio": 6,  "signal": "reverse",        "label": "Reverse"},
    {"gpio": 13, "signal": "illumination",   "label": "Illumination"},
    {"gpio": 19, "signal": "speed_pulse",    "label": "Speed Pulse"},
]


def load_gpio_config() -> list[dict]:
    """Load inputs from gpio_inputs.json, falling back to defaults."""
    try:
        data = json.loads(_CONFIG_FILE.read_text())
        inputs = data.get("inputs", [])
        if inputs:
            return inputs
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning("Failed to read gpio_inputs.json: %s — using defaults", e)
    return list(_DEFAULT_INPUTS)


def save_gpio_config(inputs: list[dict]) -> None:
    """Write inputs list to gpio_inputs.json."""
    _CONFIG_FILE.write_text(json.dumps({"inputs": inputs}, indent=2))


class GPIOInputSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self.poll_rate = config.get("poll_rate_hz", 30)
        # Load from JSON (overrides any 'inputs' key in the YAML config)
        self._inputs = load_gpio_config()
        self._gpio_module = None  # set when RPi.GPIO is available

    # ── Called by http_api to apply changes live ──────────────────────────

    def update_inputs(self, new_inputs: list[dict]) -> None:
        """Hot-swap the input mapping. Takes effect on the next poll tick."""
        if self._gpio_module is not None:
            GPIO = self._gpio_module
            # Set up any new pins
            for inp in new_inputs:
                try:
                    GPIO.setup(inp["gpio"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
                except Exception:
                    pass
        self._inputs = list(new_inputs)
        log.info("GPIO inputs updated: %s", [i["signal"] for i in self._inputs])

    # ── Main loop ─────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        if self.is_simulating():
            await self._simulate_loop()
            return

        import RPi.GPIO as GPIO
        self._gpio_module = GPIO

        GPIO.setmode(GPIO.BCM)
        for inp in self._inputs:
            GPIO.setup(inp["gpio"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

        log.info("GPIO inputs active: %s", [i["signal"] for i in self._inputs])
        interval = 1.0 / max(self.poll_rate, 1)

        try:
            while self._running:
                for inp in self._inputs:
                    if not inp.get("signal"):
                        continue
                    value = 0 if GPIO.input(inp["gpio"]) else 1
                    self.bus.publish(inp["signal"], value, "")
                await asyncio.sleep(interval)
        finally:
            GPIO.cleanup()

    async def _simulate_loop(self) -> None:
        """Simulate GPIO inputs toggling — for testing without hardware."""
        import math, time
        log.info("GPIO inputs running in SIMULATION mode")
        t0 = time.monotonic()
        interval = 1.0 / max(self.poll_rate, 1)
        while self._running:
            t = time.monotonic() - t0
            for i, inp in enumerate(self._inputs):
                if inp.get("signal"):
                    # Each input toggles at a different rate
                    value = 1 if math.sin(t / (3 + i * 1.5)) > 0.7 else 0
                    self.bus.publish(inp["signal"], value, "")
            await asyncio.sleep(interval)
