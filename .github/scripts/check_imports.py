"""
Verify every backend module can be imported without errors.

All hardware-specific packages (RPi.GPIO, spidev, smbus2, serial_asyncio)
are lazy-loaded inside methods, so this runs cleanly without Pi hardware
or any stubs. A failure here means a module-level import is broken.
"""
from backend import data_bus, config                    # noqa: F401
from backend.processors import odometer                 # noqa: F401
from backend.server import websocket, http_api          # noqa: F401
from backend.sources import (                           # noqa: F401
    base,
    can_j1939, can_compushift, can_obd,
    obd_kline, elm327, megasquirt,
    gps_nmea, analog_adc, frequency_counter,
    gpio_inputs, mock_vehicle,
)

print("All backend modules imported successfully.")
