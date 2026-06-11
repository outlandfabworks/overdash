"""
Odometer processor — integrates vehicle_speed into cumulative distance.

vehicle_speed is expected in km/h (native J1939 / OBD-II PID 0x0D unit).

Publishes signals:
  odometer  — lifetime total (km, persisted across reboots)
  trip      — resettable trip counter (km, persisted)

Use unit_conversion in the gauge config to display in miles (× 0.621371).
Persists to <project_root>/data/odometer.json every 100 m and on trip reset.
"""
import asyncio
import json
import logging
import time
from pathlib import Path

log = logging.getLogger("odometer")

_KM_TO_MI       = 0.621371
_SAMPLE_HZ      = 10          # integration rate
_SAVE_EVERY_KM  = 0.1         # write to disk every 100 m


class OdometerProcessor:
    def __init__(self, bus, project_root: Path):
        self._bus       = bus
        self._data_file = project_root / "data" / "odometer.json"
        self._odo_km    = 0.0
        self._trip_km   = 0.0
        self._saved_km  = 0.0
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        if self._data_file.exists():
            try:
                d = json.loads(self._data_file.read_text())
                self._odo_km   = float(d.get("odometer_km", 0.0))
                self._trip_km  = float(d.get("trip_km",     0.0))
                self._saved_km = self._odo_km
                log.info("Odometer loaded: %.1f km  trip: %.1f km",
                         self._odo_km, self._trip_km)
            except Exception as exc:
                log.warning("Could not load odometer data: %s", exc)

    def _save(self):
        # Atomic write: write to a temp file then rename so a power loss
        # mid-write never leaves a corrupt odometer.json.
        tmp = self._data_file.with_suffix('.tmp')
        try:
            tmp.write_text(json.dumps({
                "odometer_km": round(self._odo_km,  3),
                "trip_km":     round(self._trip_km, 3),
            }, indent=2))
            tmp.replace(self._data_file)   # atomic on POSIX filesystems
            self._saved_km = self._odo_km
        except Exception as exc:
            log.warning("Could not save odometer data: %s", exc)
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Public API ────────────────────────────────────────────────────────────

    def reset_trip(self):
        self._trip_km = 0.0
        self._save()
        self._publish()
        log.info("Trip odometer reset")

    def set_odometer(self, value_km: float):
        self._odo_km  = max(0.0, float(value_km))
        self._save()
        self._publish()
        log.info("Odometer set to %.1f km", self._odo_km)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _publish(self):
        self._bus.publish("odometer", round(self._odo_km,  2), "km")
        self._bus.publish("trip",     round(self._trip_km, 2), "km")

    async def run(self):
        dt = 1.0 / _SAMPLE_HZ
        log.info("Odometer started at %d Hz", _SAMPLE_HZ)
        self._publish()   # seed the DataBus with persisted values immediately

        while True:
            await asyncio.sleep(dt)

            entry = self._bus.snapshot().get("vehicle_speed")
            if entry is None:
                continue

            # Skip integration if the speed reading is stale (>5s old).
            # This prevents phantom km accumulation when the speed source disconnects.
            if (time.time() - entry.get("ts", 0)) > 5.0:
                continue

            speed_kmh = max(0.0, float(entry.get("value") or 0))
            delta_km  = speed_kmh * (dt / 3600.0)

            if delta_km <= 0:
                continue

            self._odo_km  += delta_km
            self._trip_km += delta_km
            self._publish()

            if self._odo_km - self._saved_km >= _SAVE_EVERY_KM:
                self._save()
