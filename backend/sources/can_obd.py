"""
CAN OBD-II source — reads standard OBD-II PIDs directly over a CAN bus using
the ISO 15765-4 transport protocol (required for all vehicles since ~2008,
common since ~2003).

This complements the existing J1939 source. Use this when:
  - The vehicle doesn't broadcast J1939/proprietary data
  - You want standard OBD-II diagnostics on a modern vehicle
  - The vehicle uses CAN-based OBD-II (not K-line)

Hardware: same CAN interface as J1939 (PiCAN2, Waveshare CAN HAT, etc.)
Wiring:   CAN-H and CAN-L to the OBD-II port pins 6 and 14

CAN OBD-II protocol:
  - Requests sent to arbitration ID 0x7DF (functional broadcast)
    or 0x7E0–0x7E7 (physical address of specific ECU)
  - Responses received from 0x7E8–0x7EF (ECU response IDs)
  - Frame format: [length, service, PID, data_byte1, ...]

Config:
  - type: can_obd
    interface: can0
    bitrate: 500000       # most modern vehicles use 500 kbps; some use 250 kbps
    ecu_address: 0x7E0    # optional — omit to broadcast to all ECUs (0x7DF)
    pids: [0x05, 0x0C, 0x0D]   # optional — defaults to full standard set
    timeout_s: 0.1        # how long to wait for each PID response

Signals published: same as ELM327 source (engine_rpm, vehicle_speed, etc.)
"""
import asyncio
import logging

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("can_obd")

# Shared OBD-II PID table (name, unit, min_data_bytes, parse_fn)
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

_DEFAULT_PIDS   = list(_PIDS.keys())
_BROADCAST_ID   = 0x7DF
_RESPONSE_BASE  = 0x7E8
_POLL_HZ        = 5
_DTC_INTERVAL_S = 30


class CANOBDSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self._interface   = config.get("interface", "can0")
        self._bitrate     = config.get("bitrate", 500000)
        self._ecu_addr    = config.get("ecu_address", _BROADCAST_ID)
        self._pids        = config.get("pids", _DEFAULT_PIDS)
        self._timeout     = config.get("timeout_s", 0.1)

    async def _read_loop(self) -> None:
        try:
            import can
        except ImportError:
            log.error("python-can not installed")
            raise

        bus = can.interface.Bus(channel=self._interface,
                                bustype="socketcan",
                                bitrate=self._bitrate)
        log.info("CAN OBD-II on %s @ %d bps", self._interface, self._bitrate)

        interval   = 1.0 / _POLL_HZ
        dtc_timer  = _DTC_INTERVAL_S

        try:
            while self._running:
                for pid in self._pids:
                    if not self._running:
                        break
                    await self._poll_pid(bus, pid)

                dtc_timer -= interval
                if dtc_timer <= 0:
                    await self._poll_dtc_status(bus)
                    dtc_timer = _DTC_INTERVAL_S

                await asyncio.sleep(interval)
        finally:
            bus.shutdown()

    async def _send_request(self, bus, pid: int) -> None:
        import can
        frame = can.Message(
            arbitration_id=self._ecu_addr,
            data=[0x02, 0x01, pid, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC],
            is_extended_id=False,
        )
        await asyncio.get_running_loop().run_in_executor(None, bus.send, frame)

    async def _recv_response(self, bus, pid: int):
        """Wait for a 0x7E8–0x7EF response matching our PID request."""
        deadline = asyncio.get_running_loop().time() + self._timeout
        while asyncio.get_running_loop().time() < deadline:
            msg = await asyncio.get_running_loop().run_in_executor(
                None, bus.recv, self._timeout / 10)
            if msg is None:
                continue
            if _RESPONSE_BASE <= msg.arbitration_id <= _RESPONSE_BASE + 7:
                data = msg.data
                # ISO 15765-4 single frame: data[0]=length, data[1]=service+0x40, data[2]=PID
                if len(data) >= 3 and data[1] == 0x41 and data[2] == pid:
                    return data[3:]   # actual PID data bytes
        return None

    async def _poll_pid(self, bus, pid: int) -> None:
        if pid not in _PIDS:
            return
        name, unit, min_bytes, parse = _PIDS[pid]
        try:
            await self._send_request(bus, pid)
            data = await self._recv_response(bus, pid)
            if data and len(data) >= min_bytes:
                self.bus.publish(name, round(parse(data), 2), unit)
        except Exception as exc:
            log.debug("CAN OBD PID %02X error: %s", pid, exc)

    async def _poll_dtc_status(self, bus) -> None:
        """Mode 01 PID 01 — MIL and stored DTC count."""
        try:
            await self._send_request(bus, 0x01)
            data = await self._recv_response(bus, 0x01)
            if data and len(data) >= 4:
                mil   = (data[0] >> 7) & 1
                count = data[0] & 0x7F
                self.bus.publish("dtc_mil",   mil,   "")
                self.bus.publish("dtc_count", count, "")
        except Exception as exc:
            log.debug("CAN OBD DTC poll error: %s", exc)
