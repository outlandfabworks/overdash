"""
Pi Dash — backend entry point.

Usage:
    python -m backend.main configs/vehicles/tdi_discovery.yaml
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

from backend.config import load_config
from backend.data_bus import DataBus
from backend.sources.can_j1939 import J1939Source
from backend.sources.can_compushift import CompuShiftSource
from backend.sources.can_obd import CANOBDSource
from backend.sources.obd_kline import OBDKlineSource
from backend.sources.elm327 import ELM327Source
from backend.sources.gpio_inputs import GPIOInputSource
from backend.sources.gps_nmea import GPSNMEASource
from backend.sources.analog_adc import AnalogADCSource
from backend.sources.frequency_counter import FrequencyCounterSource
from backend.sources.mock_vehicle import MockVehicleSource
from backend.server.websocket import WebSocketServer
from backend.server.http_api import run_server as run_http, _load_or_create_token
from backend.processors.odometer import OdometerProcessor

_SOURCE_TYPES = {
    # CAN bus
    "can_j1939":        J1939Source,
    "can_compushift":   CompuShiftSource,
    "can_obd":          CANOBDSource,
    # Serial / OBD-II
    "obd_kline":        OBDKlineSource,
    "elm327":           ELM327Source,
    # GPS
    "gps_nmea":         GPSNMEASource,
    # Analog / digital expansion
    "analog_adc":       AnalogADCSource,
    "frequency_counter":FrequencyCounterSource,
    "gpio_inputs":      GPIOInputSource,
    # Testing
    "mock_vehicle":     MockVehicleSource,
}


async def _run(config_path: str) -> None:
    cfg          = load_config(config_path)
    bus          = DataBus()
    project_root = Path(__file__).resolve().parent.parent  # backend/ -> project root

    # Shared simulation registry: {source_name: bool}
    # Owned here, passed to every source and to the HTTP API.
    sim_registry: dict = {}

    sources = []
    for src_cfg in cfg.get("sources", []):
        cls = _SOURCE_TYPES.get(src_cfg["type"])
        if cls is None:
            logging.warning("Unknown source type: %s", src_cfg["type"])
            continue
        sources.append(cls(bus, src_cfg, sim_registry=sim_registry))

    if not sources:
        logging.warning("No data sources configured — dashboard will be static.")

    gpio_source = next((s for s in sources if isinstance(s, GPIOInputSource)), None)

    srv_cfg    = cfg.get("server", {})
    auth_token = _load_or_create_token(project_root)
    ws         = WebSocketServer(bus, srv_cfg, auth_token=auth_token)
    odometer   = OdometerProcessor(bus, project_root)

    http_host = srv_cfg.get("host", "0.0.0.0")
    http_port = srv_cfg.get("http_port", 8080)

    await asyncio.gather(
        *[s.run() for s in sources],
        ws.run(),
        odometer.run(),
        run_http(bus, project_root, http_host, http_port,
                 odometer=odometer, gpio_source=gpio_source,
                 sources=sources),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Pi Dash backend")
    parser.add_argument("config", help="Vehicle config YAML path")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(_run(args.config))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
