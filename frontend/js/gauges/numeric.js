import { BaseGauge } from './base.js';

const FONTS = {
  rajdhani: 'Rajdhani, monospace',
  arial:    'Arial, sans-serif',
  impact:   'Impact, sans-serif',
  mono:     '"Courier New", monospace',
};

export class NumericGauge extends BaseGauge {
  draw(value) {
    this._lastValue = value;
    const ctx = this.ctx;
    const W = this.w, H = this.h;
    if (!W || !H) return;

    ctx.clearRect(0, 0, W, H);

    const cfg   = this._cfg;
    const label = cfg.label ?? '';
    const unit  = cfg.unit  ?? '';
    const dec   = cfg.decimals ?? 0;
    const ratio = cfg.font_size_ratio ?? 0.4;
    const conv  = cfg.unit_conversion ?? 1;
    const ff    = FONTS[cfg.font_family ?? 'rajdhani'] ?? FONTS.rajdhani;

    // If label is blank, show the unit as the header — avoids double-labelling
    const headerText = label || unit;
    // Show unit in corner only when it differs from the header
    const showUnit = !!(unit && headerText.toLowerCase() !== unit.toLowerCase());

    // Resolve display value and color
    let displayStr, color;
    if (value === null) {
      displayStr = '--';
      color      = 'rgba(255,255,255,0.25)';
    } else if (cfg.value_map) {
      displayStr = cfg.value_map[String(value)] ?? String(value);
      color      = (cfg.color_map ?? {})[String(value)] ?? (cfg.color ?? '#e0e0e0');
    } else {
      const converted = typeof value === 'number' ? value * conv : value;
      displayStr      = typeof converted === 'number' ? converted.toFixed(dec) : String(converted);
      color           = cfg.color ?? '#e0e0e0';
      if (cfg.thresholds && typeof converted === 'number') {
        for (const t of cfg.thresholds) {
          if (converted <= t.max) { color = t.color; break; }
        }
      }
    }

    const pad = Math.max(3, Math.min(W, H) * 0.04);
    const r   = Math.min(10, H * 0.10);

    // Panel background (can be disabled via cfg.panel_bg === false)
    if (cfg.panel_bg !== false) {
      const bg = ctx.createLinearGradient(0, 0, 0, H);
      bg.addColorStop(0, 'rgba(16, 18, 30, 0.90)');
      bg.addColorStop(1, 'rgba( 8, 10, 20, 0.96)');
      ctx.beginPath();
      ctx.roundRect(pad, pad, W - pad * 2, H - pad * 2, r);
      ctx.fillStyle = bg;
      ctx.fill();

      // Accent line at top in value color
      const accentH = Math.max(2, H * 0.022);
      ctx.beginPath();
      ctx.roundRect(pad, pad, W - pad * 2, accentH, [r, r, 0, 0]);
      ctx.fillStyle   = color;
      ctx.globalAlpha = value === null ? 0.2 : 0.75;
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    const fontSize  = Math.min(W, H) * ratio;
    const labelSize = Math.max(9, fontSize * 0.30);
    const accentH   = cfg.panel_bg !== false ? Math.max(2, H * 0.022) : 0;

    // Header label (top-center)
    if (headerText) {
      ctx.textAlign    = 'center';
      ctx.textBaseline = 'top';
      ctx.font         = `500 ${labelSize}px ${ff}`;
      ctx.fillStyle    = 'rgba(255,255,255,0.38)';
      ctx.fillText(headerText, W / 2, pad + accentH + labelSize * 0.3);
    }

    // Main value with glow
    ctx.shadowColor  = color;
    ctx.shadowBlur   = fontSize * 0.20;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `700 ${fontSize}px ${ff}`;
    ctx.fillStyle    = color;
    ctx.fillText(displayStr, W / 2, H * 0.58);
    ctx.shadowBlur   = 0;

    // Unit corner (only when different from header)
    if (showUnit && value !== null) {
      const unitSize = Math.max(8, fontSize * 0.28);
      ctx.textAlign    = 'right';
      ctx.textBaseline = 'bottom';
      ctx.font         = `500 ${unitSize}px ${ff}`;
      ctx.fillStyle    = 'rgba(255,255,255,0.30)';
      ctx.fillText(unit, W - pad - 5, H - pad - 4);
    }
  }
}
