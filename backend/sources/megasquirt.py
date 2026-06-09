"""
Megasquirt / Speeduino USB serial source.

Uses the MS Serial protocol: send 'A' (0x41), receive a binary real-time
data block. This is the same wire protocol that TunerStudio uses, so any
ECU that works with TunerStudio should work here.

Supported firmware types:
  ms2extra   — Megasquirt 2 with MS2Extra firmware (most common MS2 build)
  ms3        — Megasquirt 3 / MS3Pro (compatible output channel layout)
  speeduino  — Speeduino (Arduino-based open-source ECU, very popular)
  ms1        — Megasquirt 1 (original firmware, 9600 baud, smaller block)

Config example:
  - type: megasquirt
    name: "MS2"
    port: /dev/ttyUSB0
    baud: 115200          # 115200 for MS2/MS3/Speeduino; 9600 for MS1
    firmware: ms2extra    # ms1 | ms2extra | ms3 | speeduino  (default: ms2extra)
    poll_hz: 10           # polling rate in Hz (default: 10)
    simulate: false

Published signals (MS2Extra / MS3):
  engine_rpm          rpm
  coolant_temp        °C
  intake_temp         °C     (manifold air temp)
  intake_map          kPa    (manifold absolute pressure)
  baro_pressure       kPa
  throttle_pos        %
  battery_voltage     V
  afr                 :1     (wide-band air-fuel ratio, e.g. 14.7)
  ignition_advance    °
  engine_load         %      (volumetric efficiency)

Speeduino adds:
  vehicle_speed       km/h   (if VSS is configured in Speeduino)
  fuel_pressure       kPa    (if sensor fitted)
  oil_pressure        kPa    (if sensor fitted)

Note: byte offsets are firmware-version-specific. These maps target
MS2Extra 3.4.x and Speeduino firmware ≥ 2020. If values look wrong,
compare the offsets below against your firmware's .ini file.
"""
import asyncio
import logging
import struct
from collections import namedtuple

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("megasquirt")

# ── Channel definition ────────────────────────────────────────────────────────
# real_value = (raw + raw_zero) * scale
_C = namedtuple('_C', ['offset', 'fmt', 'scale', 'raw_zero', 'name', 'unit'])

def _ch(offset, fmt, scale, name, unit, raw_zero=0):
    return _C(offset, fmt, scale, raw_zero, name, unit)


# ── MS2Extra (MS2Extra 3.4.x firmware, big-endian throughout) ────────────────
_MS2EXTRA_CHANNELS = (
    _ch( 5, '>H', 1.0,  'engine_rpm',        'rpm'),
    _ch( 7, '>h', 0.1,  'ignition_advance',  '°'),
    _ch(14, '>H', 0.1,  'baro_pressure',     'kPa'),
    _ch(16, '>H', 0.1,  'intake_map',        'kPa'),
    _ch(18, '>h', 0.1,  'intake_temp',       '°C'),
    _ch(20, '>h', 0.1,  'coolant_temp',      '°C'),
    _ch(22, '>H', 0.1,  'throttle_pos',      '%'),
    _ch(24, '>H', 0.1,  'battery_voltage',   'V'),
    _ch(26, '>H', 0.1,  'afr',               ':1'),
    _ch(46, '>H', 0.1,  'engine_load',       '%'),
)
_MS2EXTRA_MIN = 48

# ── Speeduino (comms.ino sendRealtime(), firmware ≥ 2020) ────────────────────
_SPEEDUINO_CHANNELS = (
    _ch( 4, '>H', 0.1,  'intake_map',        'kPa'),
    _ch( 6, '>h', 0.1,  'intake_temp',       '°C'),
    _ch( 8, '>h', 0.1,  'coolant_temp',      '°C'),
    _ch(12, '>H', 0.1,  'battery_voltage',   'V'),
    _ch(14, '>H', 0.1,  'afr',               ':1'),
    _ch(22, '>H', 1.0,  'engine_rpm',        'rpm'),
    _ch(24, '>h', 0.1,  'ignition_advance',  '°'),
    _ch(32, '>H', 0.1,  'throttle_pos',      '%'),
    _ch(59, '>H', 0.1,  'engine_load',       '%'),
    _ch(63, '>H', 0.1,  'vehicle_speed',     'km/h'),
    _ch(66, '>B', 1.0,  'fuel_pressure',     'kPa'),
    _ch(67, '>B', 1.0,  'oil_pressure',      'kPa'),
)
_SPEEDUINO_MIN = 68

# ── MS1 (original firmware, 22-byte response, unsigned temps stored as raw-40)
_MS1_CHANNELS = (
    _ch( 5, '>H', 1.0,       'engine_rpm',    'rpm'),
    _ch( 9, '>B', 1.0,       'intake_map',    'kPa'),
    _ch(10, '>B', 1.0,       'intake_temp',   '°C',  raw_zero=-40),
    _ch(11, '>B', 1.0,       'coolant_temp',  '°C',  raw_zero=-40),
    _ch(12, '>B', 100/255,   'throttle_pos',  '%'),
)
_MS1_MIN = 22

# firmware_name -> (channels, default_baud, min_frame_size)
_FIRMWARE: dict[str, tuple] = {
    'ms1':       (_MS1_CHANNELS,      9600,   _MS1_MIN),
    'ms2extra':  (_MS2EXTRA_CHANNELS, 115200, _MS2EXTRA_MIN),
    'ms2':       (_MS2EXTRA_CHANNELS, 115200, _MS2EXTRA_MIN),
    'ms3':       (_MS2EXTRA_CHANNELS, 115200, _MS2EXTRA_MIN),
    'speeduino': (_SPEEDUINO_CHANNELS, 115200, _SPEEDUINO_MIN),
}

_READ_TIMEOUT = 0.15   # seconds to collect a full frame after sending 'A'


class MegasquirtSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        firmware = config.get('firmware', 'ms2extra').lower()
        if firmware not in _FIRMWARE:
            self.log.warning("Unknown firmware '%s', defaulting to ms2extra", firmware)
            firmware = 'ms2extra'
        self._channels, default_baud, self._min_size = _FIRMWARE[firmware]
        self._port     = config.get('port',     '/dev/ttyUSB0')
        self._baud     = config.get('baud',     default_baud)
        self._poll_hz  = config.get('poll_hz',  10)
        self._firmware = firmware
        self._reader   = None
        self._writer   = None

    # ── Serial connection ─────────────────────────────────────────────────────

    async def _connect(self) -> None:
        import serial_asyncio
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self._port, baudrate=self._baud)
        self.log.info("Megasquirt connected: %s @ %d baud (%s)",
                      self._port, self._baud, self._firmware)

    async def _disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = self._writer = None

    # ── Frame I/O ─────────────────────────────────────────────────────────────

    async def _request_frame(self) -> bytes | None:
        """Send 'A', read response bytes until min_size is collected or timeout."""
        self._writer.write(b'A')
        await self._writer.drain()

        buf      = bytearray()
        loop     = asyncio.get_running_loop()
        deadline = loop.time() + _READ_TIMEOUT

        while len(buf) < self._min_size:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                async with asyncio.timeout(remaining):
                    chunk = await self._reader.read(256)
                    if not chunk:
                        break
                    buf.extend(chunk)
            except asyncio.TimeoutError:
                break

        if len(buf) < self._min_size:
            self.log.debug("Short frame: %d bytes (need %d)", len(buf), self._min_size)
            return None
        return bytes(buf)

    def _parse_frame(self, data: bytes) -> None:
        for ch in self._channels:
            end = ch.offset + struct.calcsize(ch.fmt)
            if end > len(data):
                continue
            try:
                (raw,) = struct.unpack_from(ch.fmt, data, ch.offset)
                self.bus.publish(ch.name, round((raw + ch.raw_zero) * ch.scale, 2), ch.unit)
            except struct.error:
                pass

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        if self.is_simulating():
            await self._simulate_loop()
            return

        await self._connect()
        interval = 1.0 / max(self._poll_hz, 1)
        loop     = asyncio.get_running_loop()

        try:
            while self._running:
                t0    = loop.time()
                frame = await self._request_frame()
                if frame:
                    self._parse_frame(frame)
                await asyncio.sleep(max(0.0, interval - (loop.time() - t0)))
        finally:
            await self._disconnect()

    async def _simulate_loop(self) -> None:
        import math, time
        self.log.info("Megasquirt running in SIMULATION mode (%s)", self._firmware)
        t0       = time.monotonic()
        interval = 1.0 / max(self._poll_hz, 1)

        while self._running:
            t = time.monotonic() - t0
            self.bus.publish('engine_rpm',        round(800 + 2800 * abs(math.sin(t / 20)), 0), 'rpm')
            self.bus.publish('coolant_temp',      round(85  +    5 * math.sin(t / 60),      1), '°C')
            self.bus.publish('intake_temp',       round(35  +    5 * math.sin(t / 45),      1), '°C')
            self.bus.publish('intake_map',        round(101 +   60 * abs(math.sin(t / 10)), 1), 'kPa')
            self.bus.publish('baro_pressure',     round(101.3,                               1), 'kPa')
            self.bus.publish('throttle_pos',      round(max(0, 20 + 30 * math.sin(t / 8)),  1), '%')
            self.bus.publish('battery_voltage',   round(14.2 + 0.3 * math.sin(t / 5),       2), 'V')
            self.bus.publish('afr',               round(14.7 + 1.5 * math.sin(t / 12),      2), ':1')
            self.bus.publish('ignition_advance',  round(20   +   5 * math.sin(t / 7),       1), '°')
            self.bus.publish('engine_load',       round(40   +  30 * abs(math.sin(t / 15)), 1), '%')
            await asyncio.sleep(interval)
