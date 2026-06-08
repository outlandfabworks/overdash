"""
Analog ADC source — reads 0–5 V analog sensors via an SPI or I2C ADC chip.

Supported chips:
  MCP3208   — 8-channel, 12-bit, SPI   (recommended for expansion HAT)
  MCP3204   — 4-channel, 12-bit, SPI
  MCP3008   — 8-channel, 10-bit, SPI
  ADS1115   — 4-channel, 16-bit, I2C   (higher precision, slower)

Common use cases:
  - Wideband O2 controller (Innovate LC-2, AEM UEGO) — 0–5 V lambda output
  - EGT (exhaust gas temperature) — thermocouple amplifier with 0–5 V output
  - Boost / MAP sensor — pressure transducer with 0–5 V output
  - Fuel pressure transducer
  - Oil pressure (analog sender)
  - Coolant temperature (analog sender)

Hardware (MCP3208):
  Connect via Pi SPI0:
    MCP3208 VDD  → 3.3 V or 5 V
    MCP3208 VREF → same as VDD (or separate precision reference)
    MCP3208 CLK  → GPIO 11 (SPI0 CLK, pin 23)
    MCP3208 DIN  → GPIO 10 (SPI0 MOSI, pin 19)
    MCP3208 DOUT → GPIO 9  (SPI0 MISO, pin 21)
    MCP3208 CS   → GPIO 8  (SPI0 CE0, pin 24)
    MCP3208 AGND → GND

Enable SPI: add `dtparam=spi=on` to /boot/config.txt, reboot.

Config example:
  - type: analog_adc
    name: "Analog Sensors"
    chip: mcp3208           # mcp3208 | mcp3204 | mcp3008 | ads1115
    spi_bus: 0              # MCP: SPI bus number
    spi_device: 0           # MCP: chip-select index (0 = CE0)
    i2c_address: 0x48       # ADS1115 only
    vref: 5.0               # reference voltage
    poll_rate_hz: 10
    channels:
      - channel: 0
        signal: wideband_lambda
        label: Wideband O2
        unit: λ
        v_min: 0.0          # sensor output at value_min
        v_max: 5.0          # sensor output at value_max
        value_min: 0.68     # Innovate LC-2: 0 V = 0.68 lambda (rich)
        value_max: 1.36     # Innovate LC-2: 5 V = 1.36 lambda (lean)
        decimals: 3

      - channel: 1
        signal: egt_celsius
        label: Exhaust Temp
        unit: °C
        v_min: 0.0
        v_max: 5.0
        value_min: 0
        value_max: 1200
        decimals: 0

      - channel: 2
        signal: boost_kpa
        label: Boost Pressure
        unit: kPa
        v_min: 0.5          # typical MAP sensor: 0.5 V at 0 kPa absolute
        v_max: 4.5          # 4.5 V at 300 kPa absolute
        value_min: 0
        value_max: 300
        decimals: 1
"""
import asyncio
import logging

from backend.data_bus import DataBus
from backend.sources.base import BaseSource

log = logging.getLogger("analog_adc")


def _scale(raw: int, raw_max: int, v_ref: float,
           v_min: float, v_max: float,
           val_min: float, val_max: float) -> float:
    """Convert a raw ADC reading to an engineering value via linear interpolation."""
    voltage = (raw / raw_max) * v_ref
    voltage = max(v_min, min(v_max, voltage))
    t = (voltage - v_min) / (v_max - v_min) if (v_max - v_min) != 0 else 0
    return val_min + t * (val_max - val_min)


class AnalogADCSource(BaseSource):
    def __init__(self, bus: DataBus, config: dict, sim_registry=None):
        super().__init__(bus, config, sim_registry=sim_registry)
        self._chip       = config.get("chip", "mcp3208").lower()
        self._spi_bus    = config.get("spi_bus", 0)
        self._spi_device = config.get("spi_device", 0)
        self._i2c_addr   = config.get("i2c_address", 0x48)
        self._vref       = config.get("vref", 5.0)
        self._poll_hz    = config.get("poll_rate_hz", 10)
        self._channels   = config.get("channels", [])

    # ── Chip readers ──────────────────────────────────────────────────────────

    def _read_mcp320x(self, spi, channel: int, bits: int) -> int:
        """Read one channel from MCP3208/3204/3008 via spidev."""
        max_ch = 7 if self._chip in ("mcp3208", "mcp3008") else 3
        channel = max(0, min(max_ch, channel))
        # Build SPI request bytes
        start    = 0x01
        sgl_diff = 0x80   # single-ended
        cmd      = (sgl_diff | (channel << 4)) & 0xF0
        r = spi.xfer2([start, cmd, 0x00])
        raw = ((r[1] & (0x03 if bits == 12 else 0x01)) << 8) | r[2]
        return raw

    def _read_ads1115(self, i2c, channel: int) -> int:
        """Read one channel from ADS1115 via smbus2 (single-ended, ±6.144V range)."""
        mux = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}.get(channel, 0x4000)
        config = (0x8000 |   # start conversion
                  mux       |   # input mux
                  0x0000 |   # ±6.144V PGA — allows 0–5V sensors without clipping
                  0x0100 |   # single shot
                  0x0080 |   # 128 SPS
                  0x0003)    # disable comparator
        i2c.write_i2c_block_data(self._i2c_addr, 0x01,
                                  [(config >> 8) & 0xFF, config & 0xFF])
        import time; time.sleep(0.01)
        data = i2c.read_i2c_block_data(self._i2c_addr, 0x00, 2)
        raw  = (data[0] << 8) | data[1]
        if raw > 32767:
            raw -= 65536
        return max(0, raw)   # clamp to positive (single-ended)

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        if not self._channels:
            log.warning("No channels configured for analog_adc — nothing to read")
            return

        if self.is_simulating():
            await self._simulate_loop()
            return

        # Determine raw_max based on chip
        bits    = 12 if self._chip in ("mcp3208", "mcp3204") else (10 if self._chip == "mcp3008" else 16)
        raw_max = (1 << bits) - 1

        hw = None
        is_spi = self._chip.startswith("mcp")

        if is_spi:
            import spidev
            hw = spidev.SpiDev()
            hw.open(self._spi_bus, self._spi_device)
            hw.max_speed_hz = 1_000_000
            hw.mode = 0
            log.info("ADC %s on SPI%d.%d", self._chip.upper(),
                     self._spi_bus, self._spi_device)
        else:
            import smbus2
            hw = smbus2.SMBus(1)
            log.info("ADS1115 on I2C 0x%02X", self._i2c_addr)

        interval = 1.0 / max(1, self._poll_hz)
        try:
            while self._running:
                for ch_cfg in self._channels:
                    ch      = ch_cfg.get("channel", 0)
                    signal  = ch_cfg.get("signal", f"adc_ch{ch}")
                    unit    = ch_cfg.get("unit", "V")
                    v_min   = ch_cfg.get("v_min", 0.0)
                    v_max   = ch_cfg.get("v_max", self._vref)
                    val_min = ch_cfg.get("value_min", 0.0)
                    val_max = ch_cfg.get("value_max", 100.0)
                    dec     = ch_cfg.get("decimals", 2)

                    try:
                        if is_spi:
                            raw = self._read_mcp320x(hw, ch, bits)
                        else:
                            raw = self._read_ads1115(hw, ch)
                        value = _scale(raw, raw_max, self._vref,
                                       v_min, v_max, val_min, val_max)
                        self.bus.publish(signal, round(value, dec), unit)
                    except Exception as exc:
                        log.debug("ADC channel %d error: %s", ch, exc)

                await asyncio.sleep(interval)
        finally:
            if hw and is_spi:
                hw.close()

    async def _simulate_loop(self) -> None:
        import math, time
        log.info("Analog ADC running in SIMULATION mode")
        t0 = time.monotonic()
        interval = 1.0 / max(1, self._poll_hz)
        while self._running:
            t = time.monotonic() - t0
            for i, ch_cfg in enumerate(self._channels):
                signal  = ch_cfg.get("signal", f"adc_ch{i}")
                unit    = ch_cfg.get("unit", "V")
                val_min = ch_cfg.get("value_min", 0.0)
                val_max = ch_cfg.get("value_max", 5.0)
                dec     = ch_cfg.get("decimals", 2)
                mid     = (val_min + val_max) / 2
                amp     = (val_max - val_min) / 4
                value   = mid + amp * math.sin(t / (5 + i * 3))
                self.bus.publish(signal, round(value, dec), unit)
            await asyncio.sleep(interval)
