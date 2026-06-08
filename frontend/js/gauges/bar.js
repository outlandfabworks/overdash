import { BaseGauge } from './base.js';

const FONTS = {
  rajdhani: 'Rajdhani, monospace',
  arial:    'Arial, sans-serif',
  impact:   'Impact, sans-serif',
  mono:     '"Courier New", monospace',
};

export class BarGauge extends BaseGauge {
  draw(value) {
    this._lastValue = value;
    const ctx = this.ctx;
    const W = this.w, H = this.h;
    if (!W || !H) return;

    ctx.clearRect(0, 0, W, H);

    const cfg   = this._cfg;
    const min   = cfg.min ?? 0;
    const max   = cfg.max ?? 100;
    const label = cfg.label ?? '';
    const unit  = cfg.unit ?? '';
    const vert  = (cfg.orientation ?? 'vertical') === 'vertical';
    const zones = cfg.zones;
    const conv  = cfg.unit_conversion ?? 1;
    const ff    = FONTS[cfg.font_family ?? 'rajdhani'] ?? FONTS.rajdhani;

    const dispVal    = value === null ? null : value * conv;
    const valClamped = dispVal === null ? min : Math.max(min, Math.min(max, dispVal));
    const pct        = (valClamped - min) / (max - min);
    const color      = dispVal === null ? 'rgba(255,255,255,0.2)'
                                        : this._zoneColor(valClamped, zones, '#00e676');

    const pad   = 8;
    const labelH = H * 0.14;
    const valH   = H * 0.12;

    // Label at top
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'top';
    ctx.font         = `600 ${labelH * 0.9}px ${ff}`;
    ctx.fillStyle    = 'rgba(255,255,255,0.55)';
    ctx.fillText(label, W / 2, pad);

    // Value text at bottom
    const displayVal = dispVal === null ? '--' : Math.round(valClamped);
    ctx.textBaseline = 'bottom';
    ctx.font         = `700 ${valH}px ${ff}`;
    ctx.fillStyle    = value === null ? 'rgba(255,255,255,0.3)' : color;
    ctx.fillText(`${displayVal}${unit}`, W / 2, H - pad);

    // Bar area
    const bx = pad * 2;
    const by = pad + labelH + pad;
    const bw = W - bx * 2;
    const bh = H - by - valH - pad * 2;

    // Background track
    ctx.fillStyle = 'rgba(255,255,255,0.05)';
    ctx.beginPath();
    ctx.roundRect(bx, by, bw, bh, 6);
    ctx.fill();
    // Track border
    ctx.strokeStyle = 'rgba(255,255,255,0.10)';
    ctx.lineWidth   = 1;
    ctx.stroke();

    // Zone segments as background stripes
    if (zones) {
      for (const z of zones) {
        const p0 = (z.min - min) / (max - min);
        const p1 = (z.max - min) / (max - min);
        if (vert) {
          const y0 = by + bh * (1 - p1);
          const h0 = bh * (p1 - p0);
          ctx.fillStyle = z.color + '28';
          ctx.beginPath();
          ctx.roundRect(bx, y0, bw, h0, 2);
          ctx.fill();
        } else {
          const x0 = bx + bw * p0;
          const w0 = bw * (p1 - p0);
          ctx.fillStyle = z.color + '28';
          ctx.beginPath();
          ctx.roundRect(x0, by, w0, bh, 2);
          ctx.fill();
        }
      }
    }

    // Fill bar
    ctx.shadowColor = color;
    ctx.shadowBlur  = 8;
    if (vert) {
      const fillH = bh * pct;
      const fillY = by + bh - fillH;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(bx, fillY, bw, fillH, 6);
      ctx.fill();
    } else {
      const fillW = bw * pct;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(bx, by, fillW, bh, 6);
      ctx.fill();
    }
    ctx.shadowBlur = 0;

    // Tick lines
    const steps = 5;
    ctx.strokeStyle = 'rgba(0,0,0,0.4)';
    ctx.lineWidth   = 1;
    for (let i = 1; i < steps; i++) {
      const frac = i / steps;
      if (vert) {
        const y = by + bh * (1 - frac);
        ctx.beginPath(); ctx.moveTo(bx, y); ctx.lineTo(bx + bw, y); ctx.stroke();
      } else {
        const x = bx + bw * frac;
        ctx.beginPath(); ctx.moveTo(x, by); ctx.lineTo(x, by + bh); ctx.stroke();
      }
    }
  }
}
