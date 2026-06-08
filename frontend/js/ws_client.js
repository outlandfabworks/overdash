/**
 * WSClient — WebSocket connection to the Pi Dash backend.
 *
 * Tracks signal freshness using local receive time (Date.now()), NOT the
 * server's wall-clock timestamp. This avoids false stale detections when the
 * Pi's clock drifts or hasn't synced NTP yet.
 *
 * A signal is considered stale if no update has been received for >STALE_AFTER_S.
 * The heartbeat message keeps the connection alive even when no signals change.
 */

const STALE_AFTER_MS = 5000;  // ms without an update → stale
const STALE_CHECK_HZ = 1;

export class WSClient {
  constructor(url) {
    this.url            = url;
    this._ws            = null;
    this._reconnectMs   = 2000;
    this._lastHeartbeat = 0;         // Date.now() of last heartbeat/data
    this._signalTs      = {};        // signal → Date.now() when last received
    this._staleSet      = new Set();

    this.onSignals      = () => {};
    this.onStatusChange = () => {};
    this.onStale        = () => {};
    this.onFresh        = () => {};

    setInterval(() => this._checkStaleness(), 1000 / STALE_CHECK_HZ);
  }

  connect() {
    this._ws = new WebSocket(this.url);

    this._ws.addEventListener('open', () => {
      this._lastHeartbeat = Date.now();
      this.onStatusChange(true);
    });

    this._ws.addEventListener('message', (ev) => {
      try {
        const msg = JSON.parse(ev.data);

        if (msg.type === 'heartbeat') {
          this._lastHeartbeat = Date.now();
          return;
        }

        if (msg.data) {
          const now = Date.now();
          this._lastHeartbeat = now;

          for (const key of Object.keys(msg.data)) {
            this._signalTs[key] = now;   // local receive time — no clock skew
            if (this._staleSet.has(key)) {
              this._staleSet.delete(key);
              this.onFresh(key);
            }
          }

          this.onSignals(msg.data);
        }
      } catch {}
    });

    this._ws.addEventListener('close', () => {
      this.onStatusChange(false);
      setTimeout(() => this.connect(), this._reconnectMs);
    });

    this._ws.addEventListener('error', () => {
      this._ws.close();
    });
  }

  isFresh(signal) {
    const ts = this._signalTs[signal];
    return ts != null && (Date.now() - ts) < STALE_AFTER_MS;
  }

  _checkStaleness() {
    const now = Date.now();
    for (const [sig, ts] of Object.entries(this._signalTs)) {
      if ((now - ts) > STALE_AFTER_MS && !this._staleSet.has(sig)) {
        this._staleSet.add(sig);
        this.onStale(sig);
      }
    }
  }
}
