/**
 * IndicatorGauge — a single warning icon that can be placed anywhere in the layout.
 *
 * Config shape (mirrors one entry from LightsGauge.lights[]):
 *   {
 *     id:        string   — icon key from LIGHT_ICONS (e.g. "high_beam")
 *     label:     string   — fallback text if no icon
 *     signal:    string   — data bus signal to watch
 *     color:     string   — active color  (default '#ffa726')
 *     trigger?:  'above'|'below'
 *     threshold?: number
 *   }
 */
import { BaseGauge }   from './base.js';
import { LIGHT_ICONS } from './light_icons.js';

export class IndicatorGauge extends BaseGauge {
  constructor(canvas, config) {
    super(canvas, config);
    // Single click handler registered once — checks active state at click time
    this._canvas.addEventListener('click', () => {
      if (this._active && this._cfg.id) {
        document.dispatchEvent(new CustomEvent('overdash:show-dtcs', {
          detail: { trigger: this._cfg.id },
        }));
      }
    });
  }

  getSignals() {
    return this._cfg.signal ? [this._cfg.signal] : [];
  }

  draw(value) {
    this._lastValue = value;
    this._render();
  }

  _isActive(val) {
    if (val === undefined || val === null) return false;
    if (this._cfg.trigger === 'above') return Number(val) > this._cfg.threshold;
    if (this._cfg.trigger === 'below') return Number(val) < this._cfg.threshold;
    return Boolean(val) && val !== 0;
  }

  _render() {
    const ctx = this.ctx;
    const W = this.w, H = this.h;
    if (!W || !H) return;
    ctx.clearRect(0, 0, W, H);

    const raw    = this._lastValue;
    const val    = (raw && typeof raw === 'object') ? raw.value : raw;
    const active = this._active = this._isActive(val);
    const color  = this._cfg.color ?? '#ffa726';
    const cx = W / 2, cy = H / 2;
    const sz = Math.min(W, H) * 0.82;

    const iconFn = LIGHT_ICONS[this._cfg.id];
    if (iconFn) {
      if (active) {
        ctx.shadowColor = color;
        ctx.shadowBlur  = Math.min(W, H) * 0.4;
      }
      iconFn(ctx, cx, cy, sz, active ? color : 'rgba(255,255,255,0.18)');
      ctx.shadowBlur = 0;
    } else {
      const fs = Math.min(W, H) * 0.38;
      ctx.font         = `700 ${fs}px var(--font-mono)`;
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle    = active ? color : 'rgba(255,255,255,0.18)';
      ctx.fillText(this._cfg.label ?? this._cfg.id ?? '?', cx, cy);
    }

  }
}
