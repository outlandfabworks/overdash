"""
HTTP API server (aiohttp). Serves the frontend static files and exposes
a minimal REST API for the visual editor.

Authentication
--------------
Read-only endpoints (signals, layout GET, gpio GET) are open — the dashboard
needs to work without any login.

Write endpoints (layout PUT, reset_trip, set_odometer, gpio PUT) require a
Bearer token in the Authorization header:

    Authorization: Bearer <token>

The token is generated once on startup and stored in data/auth_token.txt.
It is injected into the served index.html so the browser-based frontend
receives it automatically without any manual login step.

Routes
------
  GET  /                        → frontend/index.html  (token injected)
  GET  /api/signals             → current signal snapshot  (open)
  GET  /api/layouts             → list layout names         (open)
  GET  /api/layout/:name        → layout JSON               (open)
  PUT  /api/layout/:name        → save layout JSON          (auth required)
  POST /api/reset_trip          → reset trip counter        (auth required)
  POST /api/set_odometer        → set odometer value        (auth required)
  GET  /api/gpio_inputs         → GPIO input config         (open)
  PUT  /api/gpio_inputs         → save GPIO input config    (auth required)
"""
import json
import logging
import re
import secrets
from pathlib import Path

from aiohttp import web

log = logging.getLogger("http_api")

_SAFE_NAME    = re.compile(r'^[\w\-]{1,64}$')
_TOKEN_MARKER = b'__PIDASH_TOKEN__'   # placeholder replaced in index.html at serve time


# ── Token management ──────────────────────────────────────────────────────────

def _load_or_create_token(project_root: Path) -> str:
    token_file = project_root / "data" / "auth_token.txt"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    if token_file.exists():
        token = token_file.read_text().strip()
        if token:
            return token
    token = secrets.token_urlsafe(32)
    token_file.write_text(token)
    log.info("Generated new API auth token (stored in data/auth_token.txt)")
    return token


def _check_auth(request: web.Request) -> bool:
    """Return True if the request carries the correct bearer token."""
    expected = request.app["auth_token"]
    header   = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return secrets.compare_digest(header[7:], expected)
    # Also accept token as a query param for WebSocket compatibility
    return secrets.compare_digest(request.rel_url.query.get("token", ""), expected)


def _require_auth(request: web.Request) -> None:
    if not _check_auth(request):
        raise web.HTTPUnauthorized(reason="Invalid or missing auth token")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(bus, project_root: Path, odometer=None, gpio_source=None,
               sources=None) -> web.Application:
    token = _load_or_create_token(project_root)

    app = web.Application()
    app["bus"]          = bus
    app["root"]         = project_root
    app["odometer"]     = odometer
    app["gpio_source"]  = gpio_source
    app["auth_token"]   = token
    app["sources"]      = {s.name: s for s in (sources or [])}

    # Open (read-only)
    app.router.add_get("/api/signals",        _get_signals)
    app.router.add_get("/api/layouts",        _get_layouts)
    app.router.add_get("/api/layout/{name}",  _get_layout)
    app.router.add_get("/api/gpio_inputs",    _get_gpio_inputs)
    app.router.add_get("/api/simulate",       _get_simulate)

    # Auth-required (writes)
    app.router.add_put ("/api/layout/{name}",  _put_layout)
    app.router.add_post("/api/reset_trip",     _reset_trip)
    app.router.add_post("/api/set_odometer",   _set_odometer)
    app.router.add_put ("/api/gpio_inputs",    _put_gpio_inputs)
    app.router.add_post("/api/simulate",       _post_simulate)

    # Serve index.html with token injected, then static files
    frontend = project_root / "frontend"
    app.router.add_get("/", lambda r: _serve_index(r, frontend))
    app.router.add_static("/", frontend, show_index=False)

    return app


# ── Index with token injection ────────────────────────────────────────────────

async def _serve_index(request: web.Request, frontend: Path) -> web.Response:
    """Serve index.html with the auth token injected so the frontend can use it."""
    html   = (frontend / "index.html").read_bytes()
    token  = request.app["auth_token"].encode()
    html   = html.replace(_TOKEN_MARKER, token)
    return web.Response(body=html, content_type="text/html")


# ── Read-only endpoints ───────────────────────────────────────────────────────

async def _get_signals(request: web.Request) -> web.Response:
    snapshot = request.app["bus"].snapshot()
    return web.json_response({k: v["value"] for k, v in snapshot.items()})


async def _get_layouts(request: web.Request) -> web.Response:
    layouts_dir = request.app["root"] / "configs" / "layouts"
    names = [p.stem for p in sorted(layouts_dir.glob("*.json"))]
    return web.json_response(names)


async def _get_layout(request: web.Request) -> web.Response:
    name = request.match_info["name"]
    if not _SAFE_NAME.match(name):
        raise web.HTTPBadRequest(reason="Invalid layout name")
    path = request.app["root"] / "configs" / "layouts" / f"{name}.json"
    if not path.exists():
        raise web.HTTPNotFound()
    return web.Response(text=path.read_text(), content_type="application/json")


async def _get_gpio_inputs(request: web.Request) -> web.Response:
    from backend.sources.gpio_inputs import load_gpio_config
    src    = request.app["gpio_source"]
    inputs = src._inputs if src is not None else load_gpio_config()
    return web.json_response({"inputs": inputs})


# ── Auth-required endpoints ───────────────────────────────────────────────────

async def _put_layout(request: web.Request) -> web.Response:
    _require_auth(request)
    name = request.match_info["name"]
    if not _SAFE_NAME.match(name):
        raise web.HTTPBadRequest(reason="Invalid layout name")
    try:
        data = await request.json()
    except Exception:
        raise web.HTTPBadRequest(reason="Invalid JSON")
    path = request.app["root"] / "configs" / "layouts" / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))
    log.info("Layout saved: %s", path)
    return web.Response(text="ok")


async def _reset_trip(request: web.Request) -> web.Response:
    _require_auth(request)
    odo = request.app["odometer"]
    if odo is None:
        raise web.HTTPServiceUnavailable(reason="Odometer not running")
    odo.reset_trip()
    return web.json_response({"status": "ok"})


async def _set_odometer(request: web.Request) -> web.Response:
    _require_auth(request)
    odo = request.app["odometer"]
    if odo is None:
        raise web.HTTPServiceUnavailable(reason="Odometer not running")
    try:
        body     = await request.json()
        value_km = float(body["value_km"])
    except Exception:
        raise web.HTTPBadRequest(reason="Expected JSON {value_km: number}")
    odo.set_odometer(value_km)
    return web.json_response({"status": "ok"})


async def _put_gpio_inputs(request: web.Request) -> web.Response:
    _require_auth(request)
    from backend.sources.gpio_inputs import save_gpio_config
    try:
        body   = await request.json()
        inputs = body["inputs"]
        if not isinstance(inputs, list):
            raise ValueError
    except Exception:
        raise web.HTTPBadRequest(reason="Expected JSON {inputs: [...]}")
    save_gpio_config(inputs)
    src = request.app["gpio_source"]
    if src is not None:
        src.update_inputs(inputs)
    log.info("GPIO inputs saved (%d channels)", len(inputs))
    return web.json_response({"status": "ok", "count": len(inputs)})


# ── Server entry point ────────────────────────────────────────────────────────

async def _get_simulate(request: web.Request) -> web.Response:
    """Return simulation state for all sources.
    Values: true | false | "always"
    "always" means the source is permanently simulated (e.g. mock_vehicle)
    and cannot be toggled.
    """
    from backend.sources.mock_vehicle import MockVehicleSource
    sources = request.app["sources"]
    result  = {}
    for name, src in sources.items():
        if isinstance(src, MockVehicleSource):
            result[name] = "always"
        else:
            result[name] = src.is_simulating()
    return web.json_response(result)


async def _post_simulate(request: web.Request) -> web.Response:
    """Toggle simulation mode for ALL sources at once.

    Partial simulation (some sources live, some simulated) is not permitted —
    mixing real and fake data on the same dashboard is a safety risk.

    Body: {"enabled": true|false}
    """
    _require_auth(request)
    try:
        body    = await request.json()
        enabled = bool(body["enabled"])
    except Exception:
        raise web.HTTPBadRequest(reason='Expected {"enabled": true|false}')

    sources = request.app["sources"]
    for src in sources.values():
        src.set_simulating(enabled)

    log.info("Simulation %s for all sources", "ON" if enabled else "OFF")
    return web.json_response({
        "status":  "ok",
        "enabled": enabled,
        "sources": list(sources.keys()),
    })


async def run_server(bus, project_root: Path, host: str, port: int,
                     odometer=None, gpio_source=None, sources=None) -> None:
    app = create_app(bus, project_root, odometer=odometer,
                     gpio_source=gpio_source, sources=sources)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    log.info("HTTP API on http://%s:%d", host, port)
    import asyncio
    await asyncio.Future()
