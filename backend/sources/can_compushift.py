"""
CompuShift Sport TCM CAN source (ZF4HP22EH / ZF5HP24 etc.).

US Shift does not publish a formal DBC, so the message layout is derived
from community reverse-engineering. Byte mappings can be overridden in the
vehicle config under `sources[type=can_compushift].messages`.

Default message map (CAN IDs and byte layouts confirmed for Sport firmware ≥2.x):
  0x3E0  Gear / TCC status
  0x3E1  Temperatures
  0x3E2  Pressures / diagnostics
"""
import asyncio
import can

from backend.data_bus import DataBus
from backend.sources.base import BaseSource


# (can_id -> list of (signal_name, byte, scale, offset, unit, is_bitfield, bit_mask, bit_shift))
_DEFAULT_MESSAGES: dict[int, list[dict]] = {
    0x3E0: [
        {"name": "trans_current_gear",  "byte": 0, "scale": 1,    "offset": 0,   "unit": ""},
        {"name": "trans_target_gear",   "byte": 1, "scale": 1,    "offset": 0,   "unit": ""},
        {"name": "trans_tcc_lockup",    "byte": 2, "mask": 0x01,  "shift": 0,    "unit": ""},
        {"name": "trans_shift_mode",    "byte": 2, "mask": 0x06,  "shift": 1,    "unit": ""},
    ],
    0x3E1: [
        {"name": "trans_temp",          "byte": 0, "scale": 1,    "offset": -40, "unit": "°C"},
        {"name": "trans_temp_raw",      "byte": 1, "scale": 1,    "offset": 0,   "unit": ""},
    ],
    0x3E2: [
        {"name": "trans_line_pressure", "byte": 0, "scale": 1,    "offset": 0,   "unit": "psi"},
        {"name": "trans_error_code",    "byte": 4, "scale": 1,    "offset": 0,   "unit": ""},
    ],
}

GEAR_LABELS = {0: "P", 1: "R", 2: "N", 3: "D", 4: "3", 5: "2", 6: "1"}
SHIFT_MODE_LABELS = {0: "D", 1: "S", 2: "M", 3: "W"}


class CompuShiftSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self.interface = config.get("interface", "can0")
        self.bitrate = config.get("bitrate", 250_000)

        self._msg_map: dict[int, list[dict]] = {}
        for can_id_str, signals in _DEFAULT_MESSAGES.items():
            self._msg_map[can_id_str] = list(signals)

        # Config overrides / additions
        for override in config.get("messages", []):
            cid = override["can_id"]
            self._msg_map[cid] = override["signals"]

    def _parse_signal(self, sig: dict, data: bytes) -> float | int | None:
        b = sig["byte"]
        if b >= len(data):
            return None
        raw = data[b]
        if "mask" in sig:
            return (raw & sig["mask"]) >> sig.get("shift", 0)
        return raw * sig.get("scale", 1) + sig.get("offset", 0)

    async def _read_loop(self) -> None:
        loop = asyncio.get_running_loop()
        can_bus = can.interface.Bus(
            channel=self.interface,
            bustype="socketcan",
            bitrate=self.bitrate,
        )
        self.log.info("CompuShift CAN listening on %s", self.interface)
        try:
            while self._running:
                msg: can.Message = await loop.run_in_executor(None, can_bus.recv, 0.1)
                if msg is None:
                    continue
                signals = self._msg_map.get(msg.arbitration_id)
                if not signals:
                    continue
                data = bytes(msg.data)
                for sig in signals:
                    value = self._parse_signal(sig, data)
                    if value is None:
                        continue
                    # Publish human-readable gear label alongside raw
                    if sig["name"] in ("trans_current_gear", "trans_target_gear"):
                        self.bus.publish(sig["name"] + "_label", GEAR_LABELS.get(int(value), "?"), "")
                    if sig["name"] == "trans_shift_mode":
                        self.bus.publish("trans_shift_mode_label", SHIFT_MODE_LABELS.get(int(value), "?"), "")
                    self.bus.publish(sig["name"], value, sig.get("unit", ""))
        finally:
            can_bus.shutdown()
