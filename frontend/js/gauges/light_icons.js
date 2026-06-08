/**
 * Automotive warning light icons using real Material Design Icons SVG paths.
 * All paths use the standard 24×24 MDI viewBox.
 * Source: https://materialdesignicons.com (Apache 2.0 License)
 */

// ── Path data (24×24 viewBox) ─────────────────────────────────────────────────

const PATHS = {
  // Turn signals — arrow-left/right-bold
  left_turn:
    'M20,9V15H12V19.84L4.16,12L12,4.16V9H20Z',
  right_turn:
    'M4,15V9H12V4.16L19.84,12L12,19.84V15H4Z',

  // High beam — car-light-high
  high_beam:
    'M13,4.8C9,4.8 9,19.2 13,19.2C17,19.2 22,16.5 22,12C22,7.5 17,4.8 13,4.8M13.1,17.2C12.7,16.8 12,15 12,12C12,9 12.7,7.2 13.1,6.8C16,6.9 20,8.7 20,12C20,15.3 16,17.1 13.1,17.2M2,5H9.5C9.3,5.4 9,5.8 8.9,6.4C8.8,6.6 8.8,6.8 8.7,7H2V5M8,11H2V9H8.2C8.1,9.6 8.1,10.3 8,11M8.7,17C8.9,17.8 9.2,18.4 9.6,19H2.1V17H8.7M8.2,15H2V13H8C8.1,13.7 8.1,14.4 8.2,15Z',

  // Low beam — car-light-dimmed
  low_beam:
    'M13,4.8C9,4.8 9,19.2 13,19.2C17,19.2 22,16.5 22,12C22,7.5 17,4.8 13,4.8M13.1,17.2C12.7,16.8 12,15 12,12C12,9 12.7,7.2 13.1,6.8C16,6.9 20,8.7 20,12C20,15.3 15.9,17.1 13.1,17.2M8,10.5C8,11 7.9,11.5 7.9,12C7.9,12.2 7.9,12.4 7.9,12.6L2.4,14L1.9,12.1L8,10.5M2,7L9.4,5.1C9.2,5.4 9,5.8 8.9,6.3C8.8,6.6 8.7,7 8.6,7.4L2.5,8.9L2,7M8.2,15.5C8.3,16.2 8.5,16.9 8.7,17.4L2.4,19L1.9,17.1L8.2,15.5Z',

  // Check engine / MIL — engine
  mil:
    'M7,4V6H10V8H7L5,10V13H3V10H1V18H3V15H5V18H8L10,20H18V16H20V19H23V9H20V12H18V8H12V6H15V4H7Z',

  // Oil pressure — oil (can with drop)
  oil:
    'M22,12.5C22,12.5 24,14.67 24,16A2,2 0 0,1 22,18A2,2 0 0,1 20,16C20,14.67 22,12.5 22,12.5M6,6H10A1,1 0 0,1 11,7A1,1 0 0,1 10,8H9V10H11C11.74,10 12.39,10.4 12.73,11L19.24,7.24L22.5,9.13C23,9.4 23.14,10 22.87,10.5C22.59,10.97 22,11.14 21.5,10.86L19.4,9.65L15.75,15.97C15.41,16.58 14.75,17 14,17H5A2,2 0 0,1 3,15V12A2,2 0 0,1 5,10H7V8H6A1,1 0 0,1 5,7A1,1 0 0,1 6,6M5,12V15H14L16.06,11.43L12.6,13.43L11.69,12H5M0.38,9.21L2.09,7.5C2.5,7.11 3.11,7.11 3.5,7.5C3.89,7.89 3.89,8.5 3.5,8.91L1.79,10.62C1.4,11 0.77,11 0.38,10.62C0,10.23 0,9.6 0.38,9.21Z',

  // Coolant temperature — thermometer-high
  coolant:
    'M15 13V5A3 3 0 0 0 9 5V13A5 5 0 1 0 15 13M12 4A1 1 0 0 1 13 5H11A1 1 0 0 1 12 4Z',

  // ABS — car-brake-abs (the actual ABS symbol with letters)
  abs:
    'M24,12C24,15.31 22.66,18.31 20.5,20.5L19.42,19.42C21.32,17.5 22.5,14.9 22.5,12C22.5,9.11 21.32,6.5 19.42,4.58L20.5,3.5C22.66,5.69 24,8.69 24,12M20,9.6V8H16.8C15.92,8 15.2,8.72 15.2,9.6V11.2A1.6,1.6 0 0,0 16.8,12.8H18.4V14.4H15.2V16H18.4C19.28,16 20,15.28 20,14.4V12.8A1.6,1.6 0 0,0 18.4,11.2H16.8V9.6H20M8.42,6C9.47,5.37 10.69,5 12,5C13.31,5 14.53,5.37 15.58,6H18.69C17.05,4.16 14.66,3 12,3C9.34,3 6.95,4.16 5.31,6H8.42M13.2,12C13.84,12 14.4,12.56 14.4,13.2V14.4A1.6,1.6 0 0,1 12.8,16H9.6V8H12.8A1.6,1.6 0 0,1 14.4,9.6V10.8C14.4,11.44 13.84,12 13.2,12M12.8,12.8H11.2V14.4H12.8V12.8M12.8,9.6H11.2V11.2H12.8V9.6M4.58,4.58L3.5,3.5C1.34,5.69 0,8.69 0,12C0,15.31 1.34,18.31 3.5,20.5L4.58,19.42C2.68,17.5 1.5,14.9 1.5,12C1.5,9.11 2.68,6.5 4.58,4.58M7.2,16V12.8H5.6V16H4V9.6A1.6,1.6 0 0,1 5.6,8H7.2C8.08,8 8.8,8.72 8.8,9.6V16H7.2M7.2,11.2V9.6H5.6V11.2H7.2M15.58,18C14.53,18.63 13.31,19 12,19C10.69,19 9.47,18.63 8.42,18H5.31C6.95,19.84 9.34,21 12,21C14.66,21 17.05,19.84 18.69,18H15.58Z',

  // Battery warning — car-battery (rectangular car battery with terminals)
  battery:
    'M4,3V6H1V20H23V6H20V3H14V6H10V3H4M3,8H21V18H3V8M15,10V12H13V14H15V16H17V14H19V12H17V10H15M5,12V14H11V12H5Z',

  // Glow plug — rendered via SVG image (see _GLOW_IMG below), not a Path2D
  glow: '',

  // Reverse — alpha-r-box-outline (R in a square)
  reverse:
    'M9,7H13A2,2 0 0,1 15,9V11C15,11.84 14.5,12.55 13.76,12.85L15,17H13L11.8,13H11V17H9V7M11,9V11H13V9H11M5,3H19A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5A2,2 0 0,1 3,19V5A2,2 0 0,1 5,3M5,5V19H19V5H5Z',

  // Boost warning — car-turbocharger
  boost_warn:
    'M22 13V15H18.32C18.75 14.09 19 13.08 19 12C19 8.14 15.86 5 12 5H2V3H12C16.97 3 21 7.03 21 12C21 12.34 20.97 12.67 20.94 13H22M12 19C8.14 19 5 15.86 5 12C5 10.93 5.25 9.91 5.69 9H2V11H3.06C3.03 11.33 3 11.66 3 12C3 16.97 7.03 21 12 21H22V19H12M16.86 12.2C15.93 12.94 14.72 12.47 14 12.05V12C16.79 10.31 15.39 7.89 15.39 7.89S14.33 6.04 14.61 7.89C14.78 9.07 13.76 9.88 13.04 10.3L13 10.28C12.93 7 10.13 7 10.13 7S8 7 9.74 7.69C10.85 8.13 11.04 9.42 11.05 10.25L11 10.28C8.14 8.7 6.74 11.12 6.74 11.12S5.67 12.97 7.14 11.8C8.07 11.07 9.28 11.54 10 11.95V12C7.21 13.7 8.61 16.12 8.61 16.12S9.67 17.97 9.4 16.11C9.22 14.94 10.25 14.13 10.97 13.7L11 13.73C11.07 17 13.87 17 13.87 17S16 17 14.26 16.31C13.15 15.87 12.96 14.58 12.95 13.75L13 13.73C15.86 15.31 17.26 12.88 17.26 12.88S18.33 11.04 16.86 12.2Z',

  // Body DTC — car-outline
  body:
    'M18.9 6C18.7 5.4 18.1 5 17.5 5H6.5C5.8 5 5.3 5.4 5.1 6L3 12V20C3 20.5 3.5 21 4 21H5C5.6 21 6 20.5 6 20V19H18V20C18 20.5 18.5 21 19 21H20C20.5 21 21 20.5 21 20V12L18.9 6M6.8 7H17.1L18.2 10H5.8L6.8 7M19 17H5V12H19V17M7.5 13C8.3 13 9 13.7 9 14.5S8.3 16 7.5 16 6 15.3 6 14.5 6.7 13 7.5 13M16.5 13C17.3 13 18 13.7 18 14.5S17.3 16 16.5 16C15.7 16 15 15.3 15 14.5S15.7 13 16.5 13Z',

  // Network DTC — wifi-alert
  network:
    'M20.24 5H18V7.25C16.16 6.45 14.13 6 12 6C8.62 6 5.5 7.12 3 9L1.2 6.6C4.21 4.34 7.95 3 12 3C14.97 3 17.77 3.73 20.24 5M8.4 16.2L12 21L15.6 16.2C14.6 15.45 13.35 15 12 15S9.4 15.45 8.4 16.2M4.8 11.4L6.6 13.8C8.1 12.67 9.97 12 12 12S15.9 12.67 17.4 13.8L18 13V10.62C16.23 9.59 14.19 9 12 9C9.3 9 6.81 9.89 4.8 11.4M20 17H22V15H20V17M20 7V13H22V7H20Z',

  // Transmission — cog-outline
  trans:
    'M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10M10,22C9.75,22 9.54,21.82 9.5,21.58L9.13,18.93C8.5,18.68 7.96,18.34 7.44,17.94L4.95,18.95C4.73,19.03 4.46,18.95 4.34,18.73L2.34,15.27C2.21,15.05 2.27,14.78 2.46,14.63L4.57,12.97L4.5,12L4.57,11L2.46,9.37C2.27,9.22 2.21,8.95 2.34,8.73L4.34,5.27C4.46,5.05 4.73,4.96 4.95,5.05L7.44,6.05C7.96,5.66 8.5,5.32 9.13,5.07L9.5,2.42C9.54,2.18 9.75,2 10,2H14C14.25,2 14.46,2.18 14.5,2.42L14.87,5.07C15.5,5.32 16.04,5.66 16.56,6.05L19.05,5.05C19.27,4.96 19.54,5.05 19.66,5.27L21.66,8.73C21.79,8.95 21.73,9.22 21.54,9.37L19.43,11L19.5,12L19.43,13L21.54,14.63C21.73,14.78 21.79,15.05 21.66,15.27L19.66,18.73C19.54,18.95 19.27,19.04 19.05,18.95L16.56,17.95C16.04,18.34 15.5,18.68 14.87,18.93L14.5,21.58C14.46,21.82 14.25,22 14,22H10M11.25,4L10.88,6.61C9.68,6.86 8.62,7.5 7.85,8.39L5.44,7.35L4.69,8.65L6.8,10.2C6.4,11.37 6.4,12.64 6.8,13.8L4.68,15.36L5.43,16.66L7.86,15.62C8.63,16.5 9.68,17.14 10.87,17.38L11.24,20H12.76L13.13,17.39C14.32,17.14 15.37,16.5 16.14,15.62L18.57,16.66L19.32,15.36L17.2,13.81C17.6,12.64 17.6,11.37 17.2,10.2L19.31,8.65L18.56,7.35L16.15,8.39C15.38,7.5 14.32,6.86 13.12,6.62L12.75,4H11.25Z',
};

// ── Pre-build Path2D objects once at module load ───────────────────────────────

const CACHED = {};
for (const [id, d] of Object.entries(PATHS)) {
  CACHED[id] = new Path2D(d);
}

// Icons that should be drawn as stroked outlines instead of filled shapes
const STROKE_IDS = new Set([]);

// ── Draw helper ───────────────────────────────────────────────────────────────
// Renders a 24×24 MDI path centred at (cx, cy) with the given icon size (sz).

function drawMDI(ctx, cx, cy, sz, color, id) {
  const p = CACHED[id];
  if (!p) return;
  ctx.save();
  ctx.translate(cx - sz / 2, cy - sz / 2);
  ctx.scale(sz / 24, sz / 24);
  if (STROKE_IDS.has(id)) {
    ctx.strokeStyle = color;
    ctx.lineWidth   = 2.5;
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.stroke(p);
  } else {
    ctx.fillStyle = color;
    ctx.fill(p);
  }
  ctx.restore();
}

// ── Public icon map ───────────────────────────────────────────────────────────
// Each entry: (ctx, cx, cy, sz, color) — called by LightsGauge._render()

export const LIGHT_ICONS = {};

for (const id of Object.keys(PATHS)) {
  LIGHT_ICONS[id] = (ctx, cx, cy, sz, color) => drawMDI(ctx, cx, cy, sz, color, id);
}

// ── Glow plug: drawn from the actual SVG asset ────────────────────────────────
// The SVG has white fill; we composite-fill it with the requested color at draw time.
const _glowImg  = new Image();
const _glowCache = new Map();   // `${sz}:${color}` → offscreen canvas
_glowImg.src = '/icons/glow.svg';

LIGHT_ICONS['glow'] = function drawGlow(ctx, cx, cy, sz, color) {
  if (!_glowImg.complete || !_glowImg.naturalWidth) return;
  const key = `${sz}:${color}`;
  if (!_glowCache.has(key)) {
    const off = document.createElement('canvas');
    off.width = off.height = sz;
    const oc = off.getContext('2d');
    oc.drawImage(_glowImg, 0, 0, sz, sz);
    oc.globalCompositeOperation = 'source-in';
    oc.fillStyle = color;
    oc.fillRect(0, 0, sz, sz);
    _glowCache.set(key, off);
  }
  ctx.drawImage(_glowCache.get(key), cx - sz / 2, cy - sz / 2);
};
