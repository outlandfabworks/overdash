"""
Frequency counter source — measures pulse frequency on GPIO pins.

Useful for any sensor that outputs a square wave proportional to a rate:
  - Tachometer signal from ignition coil / distributor (RPM)
  - Wheel speed sensor (vehicle speed, wheel slip detection)
  - Fuel flow meter (fuel consumption)
  - Turbo speed sensor
  - Transmission output shaft speed

Hardware: wire signal to any available GPIO pin on the Pi or expansion HAT.
Signal must be 3.3 V logic level (use an optocoupler or resistor divider
if the sensor output is 5 V or 12 V).

The GPIO HAT optocouplers are ideal for this — the signal is already
level-shifted and isolated.

Config:
  - type: frequency_counter
    name: "Tach + Speed"
    poll_rate_hz: 10      # how often to calculate and publish values
    channels:
      # Tachometer — 2-cylinder diesel typically fires once per rev per cylinder
      - gpio: 12
        signal: engine_rpm
        label: Tachometer
        unit: rpm
        mode: rpm                   # rpm | speed_kmh | flow_lph | raw_hz
        pulses_per_rev: 1           # pulses per crankshaft revolution

      # Wheel speed sensor — count pulses, calculate km/h
      - gpio: 16
        signal: wheel_speed_kmh
        label: Wheel Speed
        unit: km/h
        mode: speed_kmh
        pulses_per_rev: 48          # teeth on tone ring
        wheel_circumference_m: 2.1  # π × diameter (e.g. 0.72 m diameter tyre)

      # Fuel flow meter (raw Hz if you want to calculate consumption yourself)
      - gpio: 20
        signal: fuel_flow_hz
        label: Fuel Flow
        unit: Hz
        mode: raw_hz

Modes:
  rpm         → (pulses_per_second / pulses_per_rev) × 60
  speed_kmh   → (pulses_per_second / pulses_per_rev) × circumference_m × 3.6
  flow_lph    → pulses_per_second × ml_per_pulse × 3600 / 1000
  raw_hz      → pulses per second (unscaled)
"""
import asyncio
import logging
import time

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("frequency_counter")


class _PulseCounter:
    """Counts pulses on a single GPIO pin using edge interrupts."""
    def __init__(self, gpio_pin: int, gpio_module):
        self._pin   = gpio_pin
        self._gpio  = gpio_module
        self._count = 0
        gpio_module.setup(gpio_pin, gpio_module.IN, pull_up_down=gpio_module.PUD_UP)
        gpio_module.add_event_detect(gpio_pin, gpio_module.RISING,
                                     callback=self._on_pulse)

    def _on_pulse(self, _channel):
        self._count += 1

    def read_and_reset(self) -> int:
        count, self._count = self._count, 0
        return count

    def cleanup(self):
        self._gpio.remove_event_detect(self._pin)


class FrequencyCounterSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self._poll_hz  = config.get("poll_rate_hz", 10)
        self._channels = config.get("channels", [])

    async def _read_loop(self) -> None:
        if not self._channels:
            log.warning("No channels configured for frequency_counter")
            return

        if self.is_simulating():
            await self._simulate_loop()
            return

        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)

        counters = {}
        for ch in self._channels:
            pin = ch.get("gpio")
            if pin is not None:
                try:
                    counters[pin] = _PulseCounter(pin, GPIO)
                except Exception as exc:
                    log.error("Cannot set up GPIO %d: %s", pin, exc)

        log.info("Frequency counter active on pins: %s",
                 [ch.get("gpio") for ch in self._channels])

        interval = 1.0 / max(1, self._poll_hz)
        try:
            while self._running:
                await asyncio.sleep(interval)
                for ch in self._channels:
                    pin     = ch.get("gpio")
                    if pin not in counters:
                        continue
                    pulses  = counters[pin].read_and_reset()
                    hz      = pulses * self._poll_hz   # pulses / interval
                    value   = self._convert(hz, ch)
                    signal  = ch.get("signal", f"freq_gpio{pin}")
                    unit    = ch.get("unit", "Hz")
                    dec     = ch.get("decimals", 0)
                    self.bus.publish(signal, round(value, dec), unit)
        finally:
            for c in counters.values():
                c.cleanup()
            GPIO.cleanup()

    @staticmethod
    def _convert(hz: float, ch: dict) -> float:
        mode = ch.get("mode", "raw_hz")
        if mode == "rpm":
            ppr = ch.get("pulses_per_rev", 1)
            return (hz / ppr) * 60
        elif mode == "speed_kmh":
            ppr  = ch.get("pulses_per_rev", 1)
            circ = ch.get("wheel_circumference_m", 2.0)
            return (hz / ppr) * circ * 3.6
        elif mode == "flow_lph":
            mpp = ch.get("ml_per_pulse", 1.0)
            return hz * mpp * 3.6
        return hz   # raw_hz

    async def _simulate_loop(self) -> None:
        import math
        log.info("FrequencyCounter running in SIMULATION mode")
        t0 = time.monotonic()
        interval = 1.0 / max(1, self._poll_hz)
        while self._running:
            t = time.monotonic() - t0
            for i, ch in enumerate(self._channels):
                mock_hz = 25 + 15 * math.sin(t / (10 + i * 3))
                value   = self._convert(max(0, mock_hz), ch)
                signal  = ch.get("signal", f"freq_ch{i}")
                unit    = ch.get("unit", "Hz")
                dec     = ch.get("decimals", 0)
                self.bus.publish(signal, round(value, dec), unit)
            await asyncio.sleep(interval)
