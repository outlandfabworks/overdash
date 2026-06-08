"""
Mock vehicle source — generates realistic fake signals for local testing.
No hardware required. Simulates a driving cycle with slowly varying values.

Add to any vehicle YAML:
  sources:
    - type: mock_vehicle
      name: "Mock"
"""
import asyncio
import math
import time
import logging
from .base import BaseSource

log = logging.getLogger("mock_vehicle")


class MockVehicleSource(BaseSource):
    """Always-simulated source — no real hardware path exists."""

    def is_simulating(self) -> bool:
        return True   # mock is always simulated; cannot be toggled off

    def set_simulating(self, enabled: bool) -> None:
        # Mock source is permanently simulated — the enabled flag is ignored,
        # but we still publish the correct (always-true) state.
        self._sim_registry[self.name] = True
        self._publish_sim(True)

    async def _read_loop(self):
        self._publish_sim(True)   # mock is always simulated
        log.info("Mock vehicle source started — generating fake signals")
        t0   = time.monotonic()
        gear = 1

        while self._running:
            t = time.monotonic() - t0

            # Slowly oscillating speed 0–120 km/h over a 120s cycle
            speed_kmh = max(0.0, 60 + 55 * math.sin(t / 19.0))

            # RPM tracks speed loosely with gear shifts every ~15s
            gear      = max(1, min(6, int(t / 15) % 6 + 1))
            rpm       = 800 + (speed_kmh / gear) * 28 + 200 * math.sin(t / 3)
            rpm       = max(800, min(4800, rpm))

            # Temps warm up from cold over first 5 minutes
            warmup    = min(1.0, t / 300)
            coolant   = 20  + warmup * 68 + 3 * math.sin(t / 7)
            trans     = 20  + warmup * 60 + 2 * math.sin(t / 11)

            # Boost: only when moving above 30 km/h
            boost     = 101 + max(0, (speed_kmh - 30) * 0.8) + 10 * math.sin(t / 2)

            # Battery voltage: 14.4V running, 12.4V when stopped
            batt      = 14.4 if speed_kmh > 5 else 12.4 + 0.3 * math.sin(t / 5)

            # Fuel slowly draining
            fuel      = max(0, 80 - t / 360)

            # Oil pressure: high at speed, low at idle
            oil       = 30 + speed_kmh * 0.7 + 5 * math.sin(t / 4)

            # Signals
            self.bus.publish("engine_rpm",     round(rpm,       0), "rpm")
            self.bus.publish("vehicle_speed",  round(speed_kmh, 1), "km/h")
            self.bus.publish("coolant_temp",   round(coolant,   1), "°C")
            self.bus.publish("trans_temp",     round(trans,     1), "°C")
            self.bus.publish("intake_map",     round(boost,     1), "kPa")
            self.bus.publish("battery_voltage",round(batt,      2), "V")
            self.bus.publish("fuel_level",     round(fuel,      1), "%")
            self.bus.publish("oil_pressure",   round(oil,       1), "kPa")

            # Transmission
            gear_labels = {1:"1", 2:"2", 3:"3", 4:"4", 5:"5", 6:"6"}
            self.bus.publish("trans_current_gear_label", gear_labels[gear])
            self.bus.publish("trans_shift_mode_label",   "D")
            self.bus.publish("trans_tcc_lockup",         1 if speed_kmh > 60 else 0)

            # Indicators (blink left turn every 30s for 5s)
            cycle = t % 30
            self.bus.publish("left_turn",  1 if cycle < 5 else 0)
            self.bus.publish("right_turn", 0)
            self.bus.publish("high_beam",  0)
            self.bus.publish("reverse",    0)

            # DTCs — all clear
            self.bus.publish("dtc_mil",      0)
            self.bus.publish("dtc_P_active", 0)
            self.bus.publish("dtc_C_active", 0)
            self.bus.publish("dtc_B_active", 0)
            self.bus.publish("dtc_U_active", 0)

            await asyncio.sleep(0.1)   # 10 Hz updates
