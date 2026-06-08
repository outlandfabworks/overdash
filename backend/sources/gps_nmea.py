"""
GPS / NMEA 0183 source — reads position, speed, altitude and heading from any
standard serial GPS module.

Hardware: any USB or UART GPS module that outputs NMEA 0183 sentences.
Common options:
  - u-blox NEO-6M / NEO-M8N (popular, cheap, accurate)
  - GlobalTop PA6H
  - Any module with 3.3 V UART TX connected to Pi UART RX

Wiring (UART module):
  GPS TX  →  Pi GPIO 15 (UART RX, pin 10)
  GPS VCC →  Pi 3.3 V or 5 V (check module spec)
  GPS GND →  Pi GND

Config:
  - type: gps_nmea
    port: /dev/ttyAMA0    # or /dev/ttyUSB0 for USB module
    baud: 9600            # most modules default to 9600

Signals published:
  gps_speed_kmh     km/h    ground speed from GPS (independent of ECU)
  gps_latitude      °       decimal degrees, negative = south
  gps_longitude     °       decimal degrees, negative = west
  gps_altitude_m    m       altitude above sea level
  gps_heading       °       true heading / course over ground (0–359.9)
  gps_fix           0/1     1 = valid fix, 0 = no fix
  gps_satellites    n       number of satellites in use
  gps_hdop          -       horizontal dilution of precision (lower = better)
"""
import asyncio
import logging

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("gps_nmea")


def _parse_lat(value: str, hemi: str) -> float:
    if not value:
        return 0.0
    deg = float(value[:2])
    mins = float(value[2:])
    result = deg + mins / 60.0
    return -result if hemi.upper() == "S" else result


def _parse_lon(value: str, hemi: str) -> float:
    if not value:
        return 0.0
    deg = float(value[:3])
    mins = float(value[3:])
    result = deg + mins / 60.0
    return -result if hemi.upper() == "W" else result


class GPSNMEASource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self._port = config.get("port", "/dev/ttyAMA0")
        self._baud = config.get("baud", 9600)

    def _parse_sentence(self, line: str) -> None:
        """Parse a single NMEA sentence and publish relevant signals."""
        line = line.strip()
        if not line.startswith("$"):
            return

        # Verify checksum
        if "*" in line:
            body, chk = line[1:].rsplit("*", 1)
            expected = 0
            for c in body:
                expected ^= ord(c)
            if expected != int(chk[:2], 16):
                return

        parts = line.split(",")
        sentence = parts[0][1:]   # e.g. "GPRMC" or "GNRMC"

        try:
            if sentence.endswith("RMC") and len(parts) >= 9:
                # $GxRMC — recommended minimum (speed, position, heading)
                status = parts[2]
                self.bus.publish("gps_fix", 1 if status == "A" else 0, "")
                if status == "A":
                    self.bus.publish("gps_latitude",  _parse_lat(parts[3], parts[4]), "°")
                    self.bus.publish("gps_longitude", _parse_lon(parts[5], parts[6]), "°")
                    speed_knots = float(parts[7]) if parts[7] else 0.0
                    self.bus.publish("gps_speed_kmh", round(speed_knots * 1.852, 1), "km/h")
                    if parts[8]:
                        self.bus.publish("gps_heading", round(float(parts[8]), 1), "°")

            elif sentence.endswith("GGA") and len(parts) >= 11:
                # $GxGGA — fix data (altitude, satellites, HDOP)
                fix_quality = int(parts[6]) if parts[6] else 0
                self.bus.publish("gps_fix", 1 if fix_quality > 0 else 0, "")
                if fix_quality > 0:
                    self.bus.publish("gps_latitude",   _parse_lat(parts[2], parts[3]), "°")
                    self.bus.publish("gps_longitude",  _parse_lon(parts[4], parts[5]), "°")
                    self.bus.publish("gps_satellites", int(parts[7]) if parts[7] else 0, "")
                    if parts[8]:
                        self.bus.publish("gps_hdop", float(parts[8]), "")
                    if parts[9]:
                        self.bus.publish("gps_altitude_m", float(parts[9]), "m")

        except (ValueError, IndexError) as exc:
            log.debug("NMEA parse error (%s): %s", sentence, exc)

    async def _read_loop(self) -> None:
        if self.is_simulating():
            await self._simulate_loop()
            return

        import serial_asyncio
        reader, _ = await serial_asyncio.open_serial_connection(
            url=self._port, baudrate=self._baud)

        log.info("GPS reading from %s @ %d baud", self._port, self._baud)
        while self._running:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                self._parse_sentence(line.decode(errors="replace"))
            except asyncio.TimeoutError:
                log.warning("GPS: no data for 5 s — check wiring")
                self.bus.publish("gps_fix", 0, "")

    async def _simulate_loop(self) -> None:
        import math, time
        log.info("GPS running in SIMULATION mode")
        t0 = time.monotonic()
        while self._running:
            t = time.monotonic() - t0
            self.bus.publish("gps_fix",        1,                                           "")
            self.bus.publish("gps_latitude",   round(49.2827 + 0.001 * math.sin(t / 30),  6), "°")
            self.bus.publish("gps_longitude",  round(-123.12 + 0.001 * math.cos(t / 30),  6), "°")
            self.bus.publish("gps_altitude_m", round(50 + 5 * math.sin(t / 60),           1), "m")
            self.bus.publish("gps_speed_kmh",  round(max(0, 60 + 20 * math.sin(t / 19)),  1), "km/h")
            self.bus.publish("gps_heading",    round((t * 3) % 360,                        1), "°")
            self.bus.publish("gps_satellites", 8,                                           "")
            await asyncio.sleep(1.0)
