"""
WebSocket server. Sends a full snapshot on connect, then streams deltas
at the configured broadcast rate. All signal values include their unit
so the frontend never needs to hard-code units.
"""
import asyncio
import json
import logging
import secrets
import time
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.server import WebSocketServerProtocol

from backend.data_bus import DataBus

log = logging.getLogger("ws_server")


class WebSocketServer:
    def __init__(self, bus: DataBus, config: dict, auth_token: str = ""):
        self.bus = bus
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 8765)
        self.broadcast_hz = config.get("broadcast_hz", 30)
        self._auth_token = auth_token
        self._clients: set[WebSocketServerProtocol] = set()

    async def run(self) -> None:
        async with websockets.serve(self._handle, self.host, self.port):
            log.info("WebSocket server on ws://%s:%d", self.host, self.port)
            await asyncio.Future()  # run forever

    async def _handle(self, ws: WebSocketServerProtocol) -> None:
        # Validate token if one is configured
        if self._auth_token:
            qs     = parse_qs(urlparse(ws.request.path).query)
            token  = qs.get("token", [""])[0]
            if not secrets.compare_digest(token, self._auth_token):
                await ws.close(1008, "Unauthorized")
                log.warning("WebSocket rejected from %s — bad token", ws.remote_address)
                return

        self._clients.add(ws)
        q = self.bus.subscribe()
        log.info("Client connected: %s  (total=%d)", ws.remote_address, len(self._clients))

        # Full snapshot on connect
        try:
            await ws.send(json.dumps({"type": "snapshot", "data": self.bus.snapshot()}))
        except websockets.ConnectionClosed:
            self._cleanup(ws, q)
            return

        # Stream deltas, batched at broadcast_hz
        interval      = 1.0 / self.broadcast_hz
        heartbeat_int = 2.0   # send heartbeat every 2 s even if no data changes
        pending: dict = {}
        last_flush     = asyncio.get_event_loop().time()
        last_heartbeat = asyncio.get_event_loop().time()

        try:
            while True:
                # Drain all queued updates without blocking
                while True:
                    try:
                        update = q.get_nowait()
                        pending.update(update)
                    except asyncio.QueueEmpty:
                        break

                now = asyncio.get_event_loop().time()
                if pending and (now - last_flush) >= interval:
                    await ws.send(json.dumps({"type": "update", "data": pending}))
                    pending = {}
                    last_flush     = now
                    last_heartbeat = now   # data counts as a heartbeat

                # Heartbeat keeps the frontend alive when signals aren't changing
                if (now - last_heartbeat) >= heartbeat_int:
                    await ws.send(json.dumps({"type": "heartbeat", "ts": time.time()}))
                    last_heartbeat = now

                await asyncio.sleep(interval / 2)  # check queue at 2× broadcast rate
        except websockets.ConnectionClosed:
            pass
        finally:
            self._cleanup(ws, q)

    def _cleanup(self, ws: WebSocketServerProtocol, q: asyncio.Queue) -> None:
        self._clients.discard(ws)
        self.bus.unsubscribe(q)
        log.info("Client disconnected  (total=%d)", len(self._clients))
