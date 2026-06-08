/**
 * LightsGauge — horizontal strip of warning indicator lights.
 *
 * Each light watches its own signal. A light can activate two ways:
 *   - "truthy": signal value is non-zero / non-false  (default)
 *   - threshold: { trigger: "above"|"below", threshold: N }
 *
 * Config shape:
 *   {
 *     lights: [
 *       { id, label, signal, color, trigger?, threshold? },
 *       ...
 *     ]
 *   }
 *
 * This is a multi-signal gauge: it registers itself for every signal in
 * the lights array. LayoutManager passes the full signal snapshot to draw().
 */
import { BaseGauge }   from './base.js';
import { LIGHT_ICONS } from './light_icons.js';

export class LightsGauge extends BaseGauge {
  constructor(canvas, config) {
    super(canvas, config);
    this._isMultiSignal = true;
    this._snapshot = {};
    this._clickHandlerAttached = false;
  }

  /** Called by LayoutManager to know which signals to subscribe to. */
  getSignals(def) {
    return (this._cfg.lights ?? []).map(l => l.signal).filter(Boolean);
  }

  draw(snapshot) {
    if (snapshot && typeof snapshot === 'object') {
      Object.assign(this._snapshot, snapshot);
    }
    this._lastValue = this._snapshot;
    this._render();
  }

  // ── rendering ──────────────────────────────────────────────

  _isActive(light) {
    const raw = this._snapshot[light.signal];
    const val = (raw && typeof raw === 'object') ? raw.value : raw;
    if (val === undefined || val === null) return false;
    if (light.trigger === 'above')  return Number(val) > light.threshold;
    if (light.trigger === 'below')  return Number(val) < light.threshold;
    return Boolean(val) && val !== 0;
  }

  _render() {
    const ctx = this.ctx;
    const W = this.w, H = this.h;
    if (!W || !H) return;

    ctx.clearRect(0, 0, W, H);
    const lights = this._cfg.lights ?? [];
    if (!lights.length) return;

    const pad = 4;
    const gap = 4;
    const n   = lights.length;

    // Wrap to multiple rows if individual cells would be narrower than 44px
    const minCell = 44;
    const cols    = Math.max(1, Math.min(n, Math.floor((W - pad * 2 + gap) / (minCell + gap))));
    const rows    = Math.ceil(n / cols);
    const lw      = (W - pad * 2 - gap * (cols - 1)) / cols;
    const lh      = (H - pad * 2 - gap * (rows - 1)) / rows;
    const r       = Math.min(lw, lh) * 0.15;

    lights.forEach((light, i) => {
      const active = this._isActive(light);
      const col = i % cols;
      const row = Math.floor(i / cols);
      const x   = pad + col * (lw + gap);
      const y   = pad + row * (lh + gap);
      const color = light.color ?? '#ffa726';

      // Background
      ctx.beginPath();
      ctx.roundRect(x, y, lw, lh, r);
      ctx.fillStyle = active
        ? color + '22'
        : 'rgba(255,255,255,0.04)';
      ctx.fill();

      // Border
      ctx.strokeStyle = active ? color : 'rgba(255,255,255,0.1)';
      ctx.lineWidth   = active ? 1.5 : 1;
      ctx.stroke();

      // Glow when active
      if (active) {
        ctx.shadowColor  = color;
        ctx.shadowBlur   = 8;
        ctx.beginPath();
        ctx.roundRect(x, y, lw, lh, r);
        ctx.strokeStyle = color;
        ctx.lineWidth   = 1.5;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // Icon or fallback text label
      const iconColor = active ? color : 'rgba(255,255,255,0.2)';
      const iconFn    = LIGHT_ICONS[light.id];
      if (iconFn) {
        if (active) { ctx.shadowColor = color; ctx.shadowBlur = 6; }
        iconFn(ctx, x + lw / 2, y + lh / 2, Math.min(lw, lh) * 0.72, iconColor);
        ctx.shadowBlur = 0;
      } else {
        const fontSize = Math.min(lh * 0.44, lw * 0.52, 16);
        ctx.font         = `700 ${fontSize}px var(--font-mono)`;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle    = iconColor;
        ctx.fillText(light.label ?? light.id, x + lw / 2, y + lh / 2);
      }
    });

    // Attach click handler once (to open DTC panel)
    if (!this._clickHandlerAttached) {
      this._canvas.addEventListener('click', (e) => this._onClick(e, lights));
      this._clickHandlerAttached = true;
    }
  }

  _onClick(e, lights) {
    const W = this.w, H = this.h;
    const pad = 4, gap = 4, n = lights.length;
    const minCell = 44;
    const cols = Math.max(1, Math.min(n, Math.floor((W - pad * 2 + gap) / (minCell + gap))));
    const lw   = (W - pad * 2 - gap * (cols - 1)) / cols;
    const lh   = (H - pad * 2 - gap * (Math.ceil(n / cols) - 1)) / Math.ceil(n / cols);

    const rect = this._canvas.getBoundingClientRect();
    const mx   = (e.clientX - rect.left) * (W / rect.width);
    const my   = (e.clientY - rect.top)  * (H / rect.height);
    const col  = Math.floor((mx - pad) / (lw + gap));
    const row  = Math.floor((my - pad) / (lh + gap));
    const i    = row * cols + col;

    if (i >= 0 && i < lights.length && this._isActive(lights[i])) {
      document.dispatchEvent(new CustomEvent('pidash:show-dtcs', {
        detail: { trigger: lights[i].id },
      }));
    }
  }
}
