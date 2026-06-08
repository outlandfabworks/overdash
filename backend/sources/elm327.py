"""
ELM327 source — reads standard OBD-II PIDs from any vehicle via an ELM327
adapter. Covers virtually every car/truck/SUV made after 1996 (OBD-II mandate).

The ELM327 chip auto-detects the vehicle's physical protocol:
  - ISO 9141-2 / KWP2000 (K-line)  — older European/Asian vehicles
  - SAE J1850 PWM                  — Ford vehicles
  - SAE J1850 VPW                  — GM vehicles
  - ISO 15765-4 (CAN)              — all post-2008 vehicles, most post-2003

Connection modes (set in vehicle YAML):

  # USB or wired serial
  - type: elm327
    connection: serial
    port: /dev/ttyUSB0
    baud: 38400

  # WiFi adapter (e.g. KONNWEI, Vgate iCar WiFi)
  - type: elm327
    connection: wifi
    host: 192.168.0.10
    port: 35000

  # Bluetooth adapter (pair first; it appears as a serial port)
  - type: elm327
    connection: bluetooth
    port: /dev/rfcomm0    # Linux Bluetooth serial
    baud: 9600

Optional — override which PIDs to poll (defaults to the full standard set):
  pids: [0x04, 0x05, 0x0C, 0x0D, 0x0F]

Signals published (standard OBD-II Mode 01):
  engine_load       %       PID 04
  coolant_temp      °C      PID 05
  intake_map        kPa     PID 0B
  engine_rpm        rpm     PID 0C
  vehicle_speed     km/h    PID 0D
  intake_temp       °C      PID 0F
  maf_rate          g/s     PID 10
  throttle_pos      %       PID 11
  fuel_level        %       PID 2F
  battery_voltage   V       PID 42
  oil_temp          °C      PID 5C
  dtc_mil           0/1     Mode 01 PID 01 (MIL lamp status)
  dtc_count         n       Mode 01 PID 01 (stored DTC count)
"""
import asyncio
import logging
import re

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("elm327")

# ── OBD-II PID definitions ────────────────────────────────────────────────────
# Each entry: (signal_name, unit, min_bytes, parse_fn)
# parse_fn receives the raw data bytes (after mode/PID bytes)

_PIDS: dict[int, tuple] = {
    0x04: ("engine_load",     "%",    1, lambda d: d[0] / 2.55),
    0x05: ("coolant_temp",    "°C",   1, lambda d: d[0] - 40),
    0x0B: ("intake_map",      "kPa",  1, lambda d: d[0]),
    0x0C: ("engine_rpm",      "rpm",  2, lambda d: (d[0] * 256 + d[1]) / 4),
    0x0D: ("vehicle_speed",   "km/h", 1, lambda d: d[0]),
    0x0F: ("intake_temp",     "°C",   1, lambda d: d[0] - 40),
    0x10: ("maf_rate",        "g/s",  2, lambda d: (d[0] * 256 + d[1]) / 100),
    0x11: ("throttle_pos",    "%",    1, lambda d: d[0] / 2.55),
    0x2F: ("fuel_level",      "%",    1, lambda d: d[0] / 2.55),
    0x42: ("battery_voltage", "V",    2, lambda d: (d[0] * 256 + d[1]) / 1000),
    0x5C: ("oil_temp",        "°C",   1, lambda d: d[0] - 40),
}

_DEFAULT_PIDS = list(_PIDS.keys())
_POLL_HZ      = 5    # OBD-II polling rate — faster risks timeouts
_DTC_INTERVAL = 30   # check for DTCs every N seconds


class ELM327Source(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self._conn_type = config.get("connection", "serial").lower()
        self._port      = config.get("port",     "/dev/ttyUSB0")  # serial/BT device
        self._baud      = config.get("baud",     38400)
        self._host      = config.get("host",     "192.168.0.10")
        self._tcp_port  = config.get("tcp_port", 35000)           # WiFi port (separate key)
        self._pids      = config.get("pids", _DEFAULT_PIDS)
        self._reader    = None
        self._writer    = None

    # ── Connection ─────────────────────────────────────────────────────────────

    async def _connect(self):
        if self._conn_type == "wifi":
            self._reader, self._writer = await asyncio.open_connection(
                self._host, self._tcp_port)
            log.info("ELM327 connected via WiFi %s:%d", self._host, self._tcp_port)
        else:
            # Serial (USB or Bluetooth)
            import serial_asyncio
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._port, baudrate=self._baud)
            log.info("ELM327 connected via serial %s @ %d", self._port, self._baud)

    async def _disconnect(self):
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = self._writer = None

    # ── AT commands ────────────────────────────────────────────────────────────

    async def _cmd(self, cmd: str, timeout: float = 2.0) -> str:
        """Send an AT/OBD command and return the response string."""
        self._writer.write((cmd + "\r").encode())
        await self._writer.drain()
        buf = b""
        try:
            async with asyncio.timeout(timeout):
                while True:
                    chunk = await self._reader.read(256)
                    if not chunk:
                        break
                    buf += chunk
                    if b">" in buf:   # ELM327 prompt = ready for next command
                        break
        except asyncio.TimeoutError:
            pass
        return buf.decode(errors="replace").strip()

    async def _init_adapter(self):
        await self._cmd("ATZ",  timeout=3)   # reset
        await self._cmd("ATE0")              # echo off
        await self._cmd("ATL0")              # linefeeds off
        await self._cmd("ATH0")              # headers off
        await self._cmd("ATS0")              # spaces off
        await self._cmd("ATSP0")             # auto-detect protocol
        log.info("ELM327 initialised")

    # ── PID reading ────────────────────────────────────────────────────────────

    async def _read_pid(self, pid: int) -> None:
        if pid not in _PIDS:
            return
        name, unit, min_bytes, parse = _PIDS[pid]
        raw = await self._cmd(f"01{pid:02X}")
        raw = re.sub(r"[^0-9A-Fa-f]", "", raw)   # strip spaces/noise
        if not raw or len(raw) < (min_bytes + 2) * 2:
            return  # no data / not supported
        try:
            data_bytes = bytes.fromhex(raw[4:])    # skip mode+pid echo bytes
            if len(data_bytes) < min_bytes:
                return
            value = parse(data_bytes)
            self.bus.publish(name, round(value, 2), unit)
        except Exception as exc:
            log.debug("PID %02X parse error: %s", pid, exc)

    async def _check_dtcs(self) -> None:
        """Mode 01 PID 01 — MIL status and DTC count."""
        raw = await self._cmd("0101")
        raw = re.sub(r"[^0-9A-Fa-f]", "", raw)
        if len(raw) < 8:
            return
        try:
            b = bytes.fromhex(raw[4:8])
            mil   = (b[0] >> 7) & 1
            count = b[0] & 0x7F
            self.bus.publish("dtc_mil",   mil,   "")
            self.bus.publish("dtc_count", count, "")
        except Exception:
            pass

    # ── Main loop ──────────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        if self.is_simulating():
            await self._simulate_loop()
            return

        await self._connect()
        await self._init_adapter()

        interval      = 1.0 / _POLL_HZ
        dtc_countdown = _DTC_INTERVAL * _POLL_HZ

        while self._running:
            for pid in self._pids:
                if not self._running:
                    break
                await self._read_pid(pid)

            dtc_countdown -= 1
            if dtc_countdown <= 0:
                await self._check_dtcs()
                dtc_countdown = _DTC_INTERVAL * _POLL_HZ

            await asyncio.sleep(interval)

        await self._disconnect()

    async def _simulate_loop(self) -> None:
        import math, time
        log.info("ELM327 running in SIMULATION mode")
        t0 = time.monotonic()
        interval = 1.0 / _POLL_HZ
        while self._running:
            t = time.monotonic() - t0
            self.bus.publish("engine_rpm",     round(800 + 2000 * abs(math.sin(t / 15)), 0), "rpm")
            self.bus.publish("vehicle_speed",  round(max(0, 60 + 40 * math.sin(t / 20)),  1), "km/h")
            self.bus.publish("coolant_temp",   round(85 + 5 * math.sin(t / 60),           1), "°C")
            self.bus.publish("throttle_pos",   round(max(0, 20 + 15 * math.sin(t / 8)),   1), "%")
            self.bus.publish("fuel_level",     round(max(0, 75 - t / 3600),               1), "%")
            self.bus.publish("battery_voltage",round(14.2 + 0.3 * math.sin(t / 5),        2), "V")
            self.bus.publish("dtc_mil", 0, "")
            await asyncio.sleep(interval)
