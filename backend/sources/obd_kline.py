"""
OBD-II K-line source (ISO 9141-2 / KWP2000 slow-init).

Uses pyserial for the 5-baud init and subsequent 10.4 kbaud communication.
Polls a configurable list of Mode 01 PIDs on a round-robin schedule.

Optional DTC monitoring (enabled via poll_dtcs: true in config):
  - Mode 01 PID 0x01 — MIL on/off + confirmed DTC count
  - Mode 03            — Read stored DTCs
  - Mode 07            — Read pending DTCs
  Runs every dtc_poll_interval_s seconds (default 30) interleaved with live PIDs.

Published signals when poll_dtcs is enabled:
  dtc_mil          — 1 if MIL is on, 0 if off
  dtc_count        — number of confirmed DTCs
  dtc_list         — JSON array of {code, desc, type, source} objects
  dtc_last_scan    — Unix timestamp of last DTC poll
  dtc_P_active     — 1 if any P-code (powertrain) is active
  dtc_B_active     — 1 if any B-code (body) is active
  dtc_C_active     — 1 if any C-code (chassis/ABS) is active
  dtc_U_active     — 1 if any U-code (network) is active
"""
import asyncio
import json
import logging
import time

import serial

from backend.data_bus import DataBus
from backend.sources.base import BaseSource


# ── Mode 01 PID definitions ────────────────────────────────────────────────
def _rpm(d):        return ((d[0] << 8) | d[1]) / 4.0
def _speed(d):      return d[0]
def _coolant(d):    return d[0] - 40
def _iat(d):        return d[0] - 40
def _throttle(d):   return round(d[0] * 100 / 255, 1)
def _fuel_level(d): return round(d[0] * 100 / 255, 1)
def _maf(d):        return round(((d[0] << 8) | d[1]) / 100.0, 2)
def _map_kpa(d):    return d[0]
def _baro(d):       return d[0]

_DEFAULT_PIDS: dict[int, tuple] = {
    0x04: ("engine_load",     lambda d: round(d[0] * 100 / 255, 1), "%"),
    0x05: ("coolant_temp",    _coolant,   "°C"),
    0x0B: ("intake_map",      _map_kpa,   "kPa"),
    0x0C: ("engine_rpm",      _rpm,       "rpm"),
    0x0D: ("vehicle_speed",   _speed,     "km/h"),
    0x0F: ("intake_air_temp", _iat,       "°C"),
    0x10: ("maf",             _maf,       "g/s"),
    0x11: ("throttle_pos",    _throttle,  "%"),
    0x2F: ("fuel_level",      _fuel_level, "%"),
    0x33: ("baro_pressure",   _baro,      "kPa"),
}

# ── Protocol constants ─────────────────────────────────────────────────────
_HEADER   = 0x68
_DEST_ECU = 0x6A
_SRC      = 0xF1

_DTC_CATEGORIES = {0b00: "P", 0b01: "C", 0b10: "B", 0b11: "U"}


def _checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def _decode_dtc(b0: int, b1: int) -> str | None:
    """Decode a 2-byte OBD-II DTC into its 5-character code string."""
    if b0 == 0x00 and b1 == 0x00:
        return None  # padding / no code
    cat = _DTC_CATEGORIES.get((b0 >> 6) & 0x03, "P")
    num = ((b0 & 0x3F) << 8) | b1
    return f"{cat}{num:04X}"


# ── Source class ──────────────────────────────────────────────────────────
class OBDKlineSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self.port      = config.get("port", "/dev/ttyAMA0")
        self.address   = config.get("ecu_address", 0x33)
        self.poll_rate = config.get("poll_rate_hz", 5)
        self.source_label = config.get("name", self.port)

        pids_cfg = config.get("pids")
        if pids_cfg is not None:
            self._pids = {p: _DEFAULT_PIDS[p] for p in pids_cfg if p in _DEFAULT_PIDS}
        else:
            self._pids = dict(_DEFAULT_PIDS)

        self._poll_dtcs       = config.get("poll_dtcs", False)
        self._dtc_interval    = config.get("dtc_poll_interval_s", 30)
        self._last_dtc_poll   = 0.0

    # ── Low-level serial helpers (blocking, run in executor) ──────────────

    def _five_baud_init(self, ser: serial.Serial) -> bool:
        ser.baudrate = 5
        ser.write(bytes([self.address]))
        ser.flush()
        time.sleep(0.2)

        ser.baudrate = 10400
        sync = ser.read(1)
        if sync != b"\x55":
            self.log.warning("K-line: expected 0x55, got %s", sync.hex() if sync else "nothing")
            return False
        kw1 = ser.read(1)
        kw2 = ser.read(1)
        self.log.info("K-line init: KW1=%02X KW2=%02X", kw1[0], kw2[0])
        time.sleep(0.025)
        ser.write(bytes([~kw2[0] & 0xFF]))
        ack = ser.read(1)
        if not ack or ack[0] != (~self.address & 0xFF):
            self.log.warning("K-line: unexpected init ACK: %s", ack.hex() if ack else "none")
        return True

    def _send_request(self, ser: serial.Serial, mode: int, pid: int | None = None) -> bytes | None:
        """Send a mode [+pid] request and return the data payload bytes."""
        if pid is not None:
            payload = bytes([_HEADER, _DEST_ECU, _SRC, 0x02, mode, pid])
        else:
            payload = bytes([_HEADER, _DEST_ECU, _SRC, 0x01, mode])
        frame = payload + bytes([_checksum(payload)])
        ser.write(frame)
        ser.flush()

        resp = ser.read(4)
        if len(resp) < 4:
            return None
        data_len = resp[3]
        data = ser.read(data_len + 1)
        if len(data) < data_len + 1:
            return None
        expected_cs = _checksum(resp + data[:-1])
        if data[-1] != expected_cs:
            self.log.debug("K-line checksum mismatch mode=%02X pid=%s", mode, pid)
        return data[:data_len]

    def _poll_live_pids(self, ser: serial.Serial) -> None:
        for pid, (name, parse_fn, unit) in self._pids.items():
            try:
                raw = self._send_request(ser, 0x01, pid)
                if raw and len(raw) >= 2:
                    self.bus.publish(name, parse_fn(raw[2:]), unit)
            except Exception as exc:
                self.log.debug("PID %02X error: %s", pid, exc)

    def _poll_dtc_data(self, ser: serial.Serial) -> None:
        """Read MIL status (Mode 01 PID 01), stored DTCs (Mode 03), and pending DTCs (Mode 07)."""
        dtcs: list[dict] = []

        # ── MIL + DTC count ──────────────────────────────────────────────
        try:
            raw = self._send_request(ser, 0x01, 0x01)
            if raw and len(raw) >= 3:
                mil_byte = raw[2]
                mil_on   = bool(mil_byte & 0x80)
                dtc_count = mil_byte & 0x7F
                self.bus.publish("dtc_mil",   int(mil_on),  "")
                self.bus.publish("dtc_count", dtc_count,    "")
        except Exception as exc:
            self.log.debug("DTC status read error: %s", exc)

        # ── Stored DTCs (Mode 03) ────────────────────────────────────────
        dtcs += self._read_dtc_mode(ser, mode=0x03, dtype="stored")

        # ── Pending DTCs (Mode 07) ───────────────────────────────────────
        dtcs += self._read_dtc_mode(ser, mode=0x07, dtype="pending")

        # ── Publish aggregated results ───────────────────────────────────
        categories = {d["code"][0] for d in dtcs if d.get("code")}
        self.bus.publish("dtc_list",     json.dumps(dtcs),           "")
        self.bus.publish("dtc_last_scan", time.time(),               "")
        self.bus.publish("dtc_P_active", int("P" in categories),     "")
        self.bus.publish("dtc_B_active", int("B" in categories),     "")
        self.bus.publish("dtc_C_active", int("C" in categories),     "")
        self.bus.publish("dtc_U_active", int("U" in categories),     "")

        if dtcs:
            codes = [d["code"] for d in dtcs]
            self.log.info("DTCs from %s: %s", self.source_label, ", ".join(codes))

    def _read_dtc_mode(self, ser: serial.Serial, mode: int, dtype: str) -> list[dict]:
        """Read DTCs for a given mode (03=stored, 07=pending). Returns list of dicts."""
        results = []
        try:
            raw = self._send_request(ser, mode)
            if not raw or len(raw) < 2:
                return results
            # Payload after the mode echo byte: pairs of (b0, b1)
            payload = raw[1:]
            for i in range(0, len(payload) - 1, 2):
                code = _decode_dtc(payload[i], payload[i + 1])
                if code:
                    results.append({
                        "code":   code,
                        "desc":   None,     # resolved on the frontend
                        "type":   dtype,
                        "source": self.source_label,
                    })
        except Exception as exc:
            self.log.debug("Mode %02X read error: %s", mode, exc)
        return results

    # ── Async read loop ──────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        loop = asyncio.get_running_loop()
        interval = 1.0 / max(self.poll_rate, 1)

        ser = await loop.run_in_executor(
            None,
            lambda: serial.Serial(
                self.port,
                baudrate=10400,
                bytesize=8, parity="N", stopbits=1,
                timeout=0.5,
            ),
        )
        try:
            ok = await loop.run_in_executor(None, self._five_baud_init, ser)
            if not ok:
                raise RuntimeError("K-line 5-baud init failed")

            self.log.info("K-line OBD connected on %s (ecu=0x%02X)", self.port, self.address)

            while self._running:
                t0 = loop.time()

                await loop.run_in_executor(None, self._poll_live_pids, ser)

                # DTC polling on a slower cadence
                if self._poll_dtcs and (loop.time() - self._last_dtc_poll) >= self._dtc_interval:
                    await loop.run_in_executor(None, self._poll_dtc_data, ser)
                    self._last_dtc_poll = loop.time()

                await asyncio.sleep(max(0, interval - (loop.time() - t0)))
        finally:
            ser.close()
