import { BaseGauge } from './base.js';

const DEG = Math.PI / 180;

export class CircularGauge extends BaseGauge {
  draw(value) {
    this._lastValue = value;
    const ctx = this.ctx;
    const W = this.w, H = this.h;
    if (!W || !H) return;

    ctx.clearRect(0, 0, W, H);

    const cfg        = this._cfg;
    const min        = cfg.min ?? 0;
    const max        = cfg.max ?? 100;
    const startDeg   = cfg.start_angle  ?? 135;
    const sweepDeg   = cfg.sweep_angle  ?? 270;
    const majorTicks = cfg.major_ticks  ?? 10;
    const minorTicks = cfg.minor_ticks  ?? 5;
    const zones      = cfg.zones ?? [];
    const label      = cfg.label ?? '';
    const conv       = cfg.unit_conversion ?? 1;
    const style      = cfg.style ?? 'oem';

    const cx = W / 2, cy = H / 2;
    const pad    = Math.min(W, H) * 0.03;
    const outerR = Math.min(W, H) / 2 - pad;
    const bezelW = outerR * 0.055;
    const faceR  = outerR - bezelW;

    const dispVal    = value === null ? null : value * conv;
    const valClamped = dispVal === null ? min : Math.max(min, Math.min(max, dispVal));
    const pct        = (valClamped - min) / (max - min);
    const needleDeg  = startDeg + pct * sweepDeg;

    const zoneColor  = dispVal === null
      ? 'rgba(255,255,255,0.25)'
      : this._zoneColor(valClamped, zones, '#ffffff');
    const displayStr = dispVal === null ? '--' : Math.round(valClamped).toString();

    const p = { cx, cy, outerR, bezelW, faceR,
                min, max, startDeg, sweepDeg, majorTicks, minorTicks,
                zones, label, pct, needleAng: needleDeg * DEG,
                zoneColor, displayStr, hasValue: dispVal !== null };

    if      (style === 'minimal') this._drawMinimal(ctx, p);
    else if (style === 'retro')   this._drawRetro(ctx, p);
    else                          this._drawOem(ctx, p);
  }

  // ── OEM — dark navy face, chrome bezel ───────────────────────

  _drawOem(ctx, p) {
    const { cx, cy, outerR, bezelW, faceR, min, max, startDeg, sweepDeg,
            majorTicks, minorTicks, zones, label, needleAng, zoneColor,
            displayStr, hasValue } = p;

    // Chrome bezel
    const bevelGrad = ctx.createLinearGradient(cx - outerR, cy - outerR, cx + outerR, cy + outerR);
    bevelGrad.addColorStop(0.00, '#707070');
    bevelGrad.addColorStop(0.25, '#d8d8d8');
    bevelGrad.addColorStop(0.50, '#a0a0a0');
    bevelGrad.addColorStop(0.75, '#585858');
    bevelGrad.addColorStop(1.00, '#404040');
    ctx.beginPath();
    ctx.arc(cx, cy, outerR - bezelW / 2, 0, Math.PI * 2);
    ctx.strokeStyle = bevelGrad;
    ctx.lineWidth   = bezelW;
    ctx.stroke();

    // Dark navy face
    const faceGrad = ctx.createRadialGradient(cx, cy - faceR * 0.2, faceR * 0.05, cx, cy, faceR);
    faceGrad.addColorStop(0, '#2a3050');
    faceGrad.addColorStop(0.6, '#161a28');
    faceGrad.addColorStop(1, '#0a0c12');
    ctx.beginPath();
    ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
    ctx.fillStyle = faceGrad;
    ctx.fill();

    // Inner shadow ring
    const shadowGrad = ctx.createRadialGradient(cx, cy, faceR * 0.80, cx, cy, faceR);
    shadowGrad.addColorStop(0, 'rgba(0,0,0,0)');
    shadowGrad.addColorStop(1, 'rgba(0,0,0,0.55)');
    ctx.beginPath();
    ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
    ctx.fillStyle = shadowGrad;
    ctx.fill();

    // Thin zone arcs near face edge
    const zoneR = faceR * 0.91;
    const zoneW = faceR * 0.055;
    for (const z of zones) {
      const a0 = (startDeg + ((z.min - min) / (max - min)) * sweepDeg) * DEG;
      const a1 = (startDeg + ((z.max - min) / (max - min)) * sweepDeg) * DEG;
      ctx.beginPath();
      ctx.arc(cx, cy, zoneR, a0, a1);
      ctx.strokeStyle = z.color + 'cc';
      ctx.lineWidth   = zoneW;
      ctx.stroke();
    }

    // Tick marks
    const tickOutR   = faceR * 0.83;
    const majLen     = faceR * 0.12;
    const minLen     = faceR * 0.065;
    const totalTicks = majorTicks * minorTicks;
    for (let i = 0; i <= totalTicks; i++) {
      const isMaj = i % minorTicks === 0;
      const ang   = (startDeg + (i / totalTicks) * sweepDeg) * DEG;
      const len   = isMaj ? majLen : minLen;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ang) * tickOutR, cy + Math.sin(ang) * tickOutR);
      ctx.lineTo(cx + Math.cos(ang) * (tickOutR - len), cy + Math.sin(ang) * (tickOutR - len));
      ctx.strokeStyle = isMaj ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.40)';
      ctx.lineWidth   = isMaj ? 2.5 : 1.2;
      ctx.lineCap     = 'round';
      ctx.stroke();
    }

    // Tick labels
    const lblR = tickOutR - majLen - faceR * 0.10;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `600 ${faceR * 0.125}px var(--font-mono)`;
    ctx.fillStyle    = 'rgba(255,255,255,0.72)';
    for (let i = 0; i <= majorTicks; i++) {
      const ang = (startDeg + (i / majorTicks) * sweepDeg) * DEG;
      const lv  = Math.round(min + (i / majorTicks) * (max - min));
      ctx.fillText(lv, cx + Math.cos(ang) * lblR, cy + Math.sin(ang) * lblR);
    }

    // Needle with shadow
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(needleAng);
    ctx.shadowColor   = 'rgba(0,0,0,0.7)';
    ctx.shadowBlur    = 8;
    ctx.shadowOffsetX = 3;
    ctx.shadowOffsetY = 3;
    ctx.beginPath();
    ctx.moveTo(-faceR * 0.20, 0);
    ctx.lineTo(tickOutR - majLen * 0.4, 0);
    ctx.strokeStyle = hasValue ? '#f0f0f0' : 'rgba(255,255,255,0.25)';
    ctx.lineWidth   = 2.5;
    ctx.lineCap     = 'round';
    ctx.stroke();
    ctx.restore();

    // Metallic hub
    const hubR    = faceR * 0.07;
    const hubGrad = ctx.createRadialGradient(cx - hubR * 0.3, cy - hubR * 0.3, 0, cx, cy, hubR);
    hubGrad.addColorStop(0, '#c0c0c0');
    hubGrad.addColorStop(0.5, '#606060');
    hubGrad.addColorStop(1, '#202020');
    ctx.beginPath();
    ctx.arc(cx, cy, hubR, 0, Math.PI * 2);
    ctx.fillStyle = hubGrad;
    ctx.fill();

    // Label + value
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `600 ${faceR * 0.13}px var(--font-mono)`;
    ctx.fillStyle    = 'rgba(255,255,255,0.75)';
    ctx.fillText(label, cx, cy + faceR * 0.28);
    ctx.font      = `700 ${faceR * 0.32}px var(--font-mono)`;
    ctx.fillStyle = zoneColor;
    ctx.fillText(displayStr, cx, cy + faceR * 0.52);
  }

  // ── Minimal — flat, modern, arc track + colored fill ─────────

  _drawMinimal(ctx, p) {
    const { cx, cy, faceR, min, max, startDeg, sweepDeg,
            majorTicks, minorTicks, zones, label, pct,
            needleAng, zoneColor, displayStr, hasValue } = p;

    const startRad = startDeg * DEG;
    const endRad   = (startDeg + sweepDeg) * DEG;

    // Flat dark face
    ctx.beginPath();
    ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
    ctx.fillStyle = '#0d0f14';
    ctx.fill();

    // Ghost track arc
    const trackR = faceR * 0.80;
    const trackW = faceR * 0.065;
    ctx.beginPath();
    ctx.arc(cx, cy, trackR, startRad, endRad);
    ctx.strokeStyle = 'rgba(255,255,255,0.09)';
    ctx.lineWidth   = trackW;
    ctx.lineCap     = 'butt';
    ctx.stroke();

    // Zone tints on track
    for (const z of zones) {
      const a0 = (startDeg + ((z.min - min) / (max - min)) * sweepDeg) * DEG;
      const a1 = (startDeg + ((z.max - min) / (max - min)) * sweepDeg) * DEG;
      ctx.beginPath();
      ctx.arc(cx, cy, trackR, a0, a1);
      ctx.strokeStyle = z.color + '44';
      ctx.lineWidth   = trackW;
      ctx.lineCap     = 'butt';
      ctx.stroke();
    }

    // Colored fill arc (value)
    if (hasValue && pct > 0.005) {
      ctx.beginPath();
      ctx.arc(cx, cy, trackR, startRad, startRad + pct * sweepDeg * DEG);
      ctx.strokeStyle = zoneColor;
      ctx.lineWidth   = trackW;
      ctx.lineCap     = 'round';
      ctx.shadowColor = zoneColor;
      ctx.shadowBlur  = 8;
      ctx.stroke();
      ctx.shadowBlur  = 0;
    }

    // Tick marks
    const tickOutR   = faceR * 0.69;
    const majLen     = faceR * 0.085;
    const minLen     = faceR * 0.045;
    const totalTicks = majorTicks * minorTicks;
    for (let i = 0; i <= totalTicks; i++) {
      const isMaj = i % minorTicks === 0;
      const ang   = (startDeg + (i / totalTicks) * sweepDeg) * DEG;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ang) * tickOutR, cy + Math.sin(ang) * tickOutR);
      ctx.lineTo(cx + Math.cos(ang) * (tickOutR - (isMaj ? majLen : minLen)),
                 cy + Math.sin(ang) * (tickOutR - (isMaj ? majLen : minLen)));
      ctx.strokeStyle = isMaj ? 'rgba(255,255,255,0.60)' : 'rgba(255,255,255,0.22)';
      ctx.lineWidth   = isMaj ? 1.5 : 0.8;
      ctx.lineCap     = 'round';
      ctx.stroke();
    }

    // Tick labels
    const lblR = tickOutR - majLen - faceR * 0.085;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `500 ${faceR * 0.10}px var(--font-mono)`;
    ctx.fillStyle    = 'rgba(255,255,255,0.40)';
    for (let i = 0; i <= majorTicks; i++) {
      const ang = (startDeg + (i / majorTicks) * sweepDeg) * DEG;
      const lv  = Math.round(min + (i / majorTicks) * (max - min));
      ctx.fillText(lv, cx + Math.cos(ang) * lblR, cy + Math.sin(ang) * lblR);
    }

    // Thin needle
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(needleAng);
    ctx.beginPath();
    ctx.moveTo(-faceR * 0.14, 0);
    ctx.lineTo(faceR * 0.58, 0);
    ctx.strokeStyle = hasValue ? zoneColor : 'rgba(255,255,255,0.18)';
    ctx.lineWidth   = 1.8;
    ctx.lineCap     = 'round';
    if (hasValue) { ctx.shadowColor = zoneColor; ctx.shadowBlur = 6; }
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();

    // Hub dot
    ctx.beginPath();
    ctx.arc(cx, cy, faceR * 0.038, 0, Math.PI * 2);
    ctx.fillStyle = hasValue ? zoneColor : 'rgba(255,255,255,0.25)';
    if (hasValue) { ctx.shadowColor = zoneColor; ctx.shadowBlur = 8; }
    ctx.fill();
    ctx.shadowBlur = 0;

    // Value + label centered below midpoint
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `700 ${faceR * 0.30}px var(--font-mono)`;
    ctx.fillStyle    = zoneColor;
    ctx.fillText(displayStr, cx, cy + faceR * 0.36);
    ctx.font      = `500 ${faceR * 0.11}px var(--font-mono)`;
    ctx.fillStyle = 'rgba(255,255,255,0.38)';
    ctx.fillText(label, cx, cy + faceR * 0.54);
  }

  // ── Retro — classic analog, bold ticks, red needle ───────────

  _drawRetro(ctx, p) {
    const { cx, cy, outerR, faceR, min, max, startDeg, sweepDeg,
            majorTicks, minorTicks, zones, label, needleAng, zoneColor,
            displayStr, hasValue } = p;

    // Face (dark charcoal, slight centre highlight)
    const faceGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, outerR);
    faceGrad.addColorStop(0, '#1c1e1c');
    faceGrad.addColorStop(1, '#080a08');
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
    ctx.fillStyle = faceGrad;
    ctx.fill();

    // Outer rim ring
    ctx.beginPath();
    ctx.arc(cx, cy, outerR - 1, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.28)';
    ctx.lineWidth   = 2.5;
    ctx.stroke();

    // Colored zone arcs near edge
    const zoneR = faceR * 0.92;
    const zoneW = faceR * 0.042;
    for (const z of zones) {
      const a0 = (startDeg + ((z.min - min) / (max - min)) * sweepDeg) * DEG;
      const a1 = (startDeg + ((z.max - min) / (max - min)) * sweepDeg) * DEG;
      ctx.beginPath();
      ctx.arc(cx, cy, zoneR, a0, a1);
      ctx.strokeStyle = z.color + 'dd';
      ctx.lineWidth   = zoneW;
      ctx.lineCap     = 'butt';
      ctx.stroke();
    }

    // Bold tick marks
    const tickOutR   = faceR * 0.86;
    const majLen     = faceR * 0.17;
    const minLen     = faceR * 0.085;
    const totalTicks = majorTicks * minorTicks;
    for (let i = 0; i <= totalTicks; i++) {
      const isMaj = i % minorTicks === 0;
      const ang   = (startDeg + (i / totalTicks) * sweepDeg) * DEG;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ang) * tickOutR, cy + Math.sin(ang) * tickOutR);
      ctx.lineTo(cx + Math.cos(ang) * (tickOutR - (isMaj ? majLen : minLen)),
                 cy + Math.sin(ang) * (tickOutR - (isMaj ? majLen : minLen)));
      ctx.strokeStyle = isMaj ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.48)';
      ctx.lineWidth   = isMaj ? 3 : 1.5;
      ctx.lineCap     = 'square';
      ctx.stroke();
    }

    // Tick labels — bold, bright
    const lblR = tickOutR - majLen - faceR * 0.115;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `700 ${faceR * 0.135}px var(--font-mono)`;
    ctx.fillStyle    = 'rgba(255,255,255,0.88)';
    for (let i = 0; i <= majorTicks; i++) {
      const ang = (startDeg + (i / majorTicks) * sweepDeg) * DEG;
      const lv  = Math.round(min + (i / majorTicks) * (max - min));
      ctx.fillText(lv, cx + Math.cos(ang) * lblR, cy + Math.sin(ang) * lblR);
    }

    // Red needle (shadow pass first)
    const needleLen = tickOutR - majLen * 0.5;
    const tailLen   = faceR * 0.22;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(needleAng);
    ctx.beginPath();
    ctx.moveTo(-tailLen + 2, 2);
    ctx.lineTo(needleLen + 2, 2);
    ctx.strokeStyle = 'rgba(0,0,0,0.55)';
    ctx.lineWidth   = 3;
    ctx.lineCap     = 'round';
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(-tailLen, 0);
    ctx.lineTo(needleLen, 0);
    ctx.strokeStyle = hasValue ? '#e82010' : 'rgba(200,60,60,0.3)';
    ctx.lineWidth   = 3;
    ctx.stroke();
    ctx.restore();

    // Hub — chrome ring + black fill + red pip
    const hubR = faceR * 0.065;
    ctx.beginPath();
    ctx.arc(cx, cy, hubR + 2.5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(210,210,210,0.85)';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx, cy, hubR, 0, Math.PI * 2);
    ctx.fillStyle = '#090909';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx, cy, hubR * 0.38, 0, Math.PI * 2);
    ctx.fillStyle = '#e82010';
    ctx.fill();

    // Value box + label
    const boxW = faceR * 0.54;
    const boxH = faceR * 0.22;
    const boxY = cy + faceR * 0.40;
    ctx.beginPath();
    ctx.roundRect(cx - boxW / 2, boxY - boxH / 2, boxW, boxH, 4);
    ctx.fillStyle   = 'rgba(0,0,0,0.60)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.14)';
    ctx.lineWidth   = 1;
    ctx.stroke();

    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.font         = `700 ${faceR * 0.22}px var(--font-mono)`;
    ctx.fillStyle    = hasValue ? '#ffffff' : 'rgba(255,255,255,0.22)';
    ctx.fillText(displayStr, cx, boxY);

    ctx.font      = `600 ${faceR * 0.12}px var(--font-mono)`;
    ctx.fillStyle = 'rgba(255,255,255,0.75)';
    ctx.fillText(label, cx, cy + faceR * 0.20);
  }
}
