"""
J1939 CAN source. Decodes key PGNs from a 29-bit extended-frame CAN bus
using python-can. Signal definitions are merged from config so they can
be extended per vehicle without code changes.
"""
import asyncio
import struct

import can

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

# Default signal map: PGN -> list of (signal_name, byte_offset, length_bytes, scale, offset, unit)
# All values assume little-endian byte order per SAE J1939.
_DEFAULT_PGN_SIGNALS: dict[int, list[tuple]] = {
    61444: [  # EEC1 — Electronic Engine Controller 1
        ("engine_rpm",    3, 2, 0.125,  0,    "rpm"),
        ("throttle_pos",  1, 1, 0.4,    0,    "%"),
    ],
    65262: [  # ET1 — Engine Temperature 1
        ("coolant_temp",  0, 1, 0.03125, -273, "°C"),
        ("fuel_temp",     2, 1, 0.03125, -273, "°C"),
        ("oil_temp",      4, 2, 0.03125, -273, "°C"),
    ],
    65263: [  # EFL/P1 — Engine Fluid Level / Pressure 1
        ("fuel_delivery_pressure", 0, 1,  4.0,  0, "kPa"),
        ("oil_pressure",           3, 1,  4.0,  0, "kPa"),
    ],
    65265: [  # CCVS1 — Cruise Control / Vehicle Speed
        ("vehicle_speed", 1, 2, 0.00390625, 0, "km/h"),
    ],
    65271: [  # VEP1 — Vehicle Electrical Power 1
        ("battery_voltage", 4, 2, 0.05, 0, "V"),
    ],
    65276: [  # DD — Dash Display
        ("fuel_level", 1, 2, 0.0025, 0, "%"),
    ],
}


def _pgn_from_can_id(can_id: int) -> int:
    """Extract PGN from a 29-bit J1939 CAN ID."""
    pdu_format = (can_id >> 16) & 0xFF
    pdu_specific = (can_id >> 8) & 0xFF
    data_page = (can_id >> 24) & 0x01
    if pdu_format >= 0xF0:
        # PDU2 — peer-to-peer addressed, PGN includes PS field
        return (data_page << 17) | (pdu_format << 8) | pdu_specific
    else:
        return (data_page << 17) | (pdu_format << 8)


class J1939Source(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self.interface = config.get("interface", "can0")
        self.bitrate = config.get("bitrate", 250_000)
        # Merge default + config-defined signals
        self._pgn_map: dict[int, list[tuple]] = dict(_DEFAULT_PGN_SIGNALS)
        for sig in config.get("extra_signals", []):
            pgn = sig["pgn"]
            entry = (
                sig["name"],
                sig["byte_offset"],
                sig["length"],
                sig.get("scale", 1.0),
                sig.get("offset", 0.0),
                sig.get("unit", ""),
            )
            self._pgn_map.setdefault(pgn, []).append(entry)

    async def _read_loop(self) -> None:
        loop = asyncio.get_running_loop()
        can_bus = can.interface.Bus(
            channel=self.interface,
            bustype="socketcan",
            bitrate=self.bitrate,
        )
        self.log.info("CAN J1939 listening on %s", self.interface)
        try:
            while self._running:
                msg: can.Message = await loop.run_in_executor(None, can_bus.recv, 0.1)
                if msg is None:
                    continue
                if not msg.is_extended_id:
                    continue
                pgn = _pgn_from_can_id(msg.arbitration_id)
                signals = self._pgn_map.get(pgn)
                if not signals:
                    continue
                data = bytes(msg.data)
                for name, offset, length, scale, off, unit in signals:
                    if offset + length > len(data):
                        continue
                    raw = int.from_bytes(data[offset:offset + length], "little")
                    value = round(raw * scale + off, 3)
                    self.bus.publish(name, value, unit)
        finally:
            can_bus.shutdown()
