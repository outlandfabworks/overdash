import { GaugeRegistry } from './gauge_registry.js';

export class LayoutManager {
  constructor(root, layoutCfg) {
    this._root    = root;
    this._layout  = layoutCfg;
    this._gauges  = new Map(); // signal -> [gauge, ...]
    this._wrappers = new Map(); // gaugeId -> wrapper HTMLElement
    this._ro      = null;
    this._signals = {};
  }

  build() {
    const { columns, rows, gap_px } = this._layout.grid;
    const g = gap_px ?? 8;

    this._root.style.cssText = [
      'display: grid',
      `grid-template-columns: repeat(${columns}, 1fr)`,
      `grid-template-rows: repeat(${rows}, 1fr)`,
      `gap: ${g}px`,
      'width: 100%',
      'height: 100%',
      `padding: ${g}px`,
      'box-sizing: border-box',
      'position: relative',
    ].join('; ');

    for (const def of this._layout.gauges) {
      const wrapper = document.createElement('div');

      if (def.pos) {
        // Free-float overlay — positioned as % of dash-root
        const { x = 0, y = 0, w = 8, h = 8 } = def.pos;
        wrapper.style.cssText = [
          'position: absolute',
          `left: ${x}%`, `top: ${y}%`,
          `width: ${w}%`, `height: ${h}%`,
          'overflow: hidden',
          'z-index: 10',
        ].join('; ');
      } else {
        const { col, row, colspan = 1, rowspan = 1 } = def.grid;
        wrapper.style.cssText = [
          `grid-column: ${col + 1} / span ${colspan}`,
          `grid-row: ${row + 1} / span ${rowspan}`,
          'position: relative',
          'overflow: hidden',
        ].join('; ');
      }
      wrapper.dataset.gaugeId = def.id;

      const canvas = document.createElement('canvas');
      canvas.style.cssText = 'width:100%; height:100%;';
      wrapper.appendChild(canvas);
      this._root.appendChild(wrapper);
      this._wrappers.set(def.id, wrapper);

      let gauge;
      try {
        gauge = GaugeRegistry.create(def.type, canvas, def.config ?? {});
      } catch (e) {
        console.warn('Gauge create failed:', def.id, e);
        continue;
      }

      // Register for every signal this gauge cares about
      const signalKeys = gauge.getSignals(def);
      for (const key of signalKeys) {
        if (!this._gauges.has(key)) this._gauges.set(key, []);
        this._gauges.get(key).push(gauge);
      }

      // Initial draw — multi-signal gauges get the full snapshot
      if (gauge._isMultiSignal) {
        gauge.draw(this._flatSnapshot());
      } else {
        gauge.draw(this._signals[def.signal]?.value ?? null);
      }
    }

    if (this._layout.meta?.bg_color) {
      document.documentElement.style.setProperty('--bg', this._layout.meta.bg_color);
    }

    if (this._layout.meta?.bg_image) {
      this._root.style.backgroundImage    = `url(${this._layout.meta.bg_image})`;
      this._root.style.backgroundSize     = 'cover';
      this._root.style.backgroundPosition = 'center';
      this._root.classList.add('has-bg-image');
      this._root.style.setProperty('--bg-dim', this._layout.meta.bg_dim ?? 0.3);
    } else {
      this._root.style.backgroundImage = '';
      this._root.classList.remove('has-bg-image');
    }

    if (!this._ro) {
      this._ro = new ResizeObserver(() => this._resize());
      this._ro.observe(this._root);
    }
    this._resize();
  }

  /** Tear down and rebuild — used by the editor after layout changes. */
  rebuild(newLayout) {
    this._layout = newLayout;
    this._root.innerHTML = '';
    this._gauges.clear();
    this._wrappers.clear();
    this.build();
  }

  /** Returns a Map<gaugeId, wrapperEl> — consumed by DragGrid. */
  getWrappers() {
    return this._wrappers;
  }

  /**
   * Called by WSClient.onStale / onFresh to dim a gauge and show a STALE badge.
   * Works for both single-signal and multi-signal gauges.
   */
  markStale(signal, isStale) {
    // Find every gauge def that cares about this signal
    for (const def of this._layout.gauges) {
      // Signal is at def.signal (top-level) for all types.
      // Lights gauges also watch individual light signals from def.config.lights.
      const signals = def.type === 'lights'
        ? (def.config?.lights ?? []).map(l => l.signal).concat([def.signal])
        : [def.signal];

      if (!signals.includes(signal)) continue;

      const wrapper = this._wrappers.get(def.id);
      if (!wrapper) continue;

      // Dim the canvas
      wrapper.querySelector('canvas').style.opacity = isStale ? '0.35' : '';

      // Add/remove STALE badge
      let badge = wrapper.querySelector('.stale-badge');
      if (isStale) {
        if (!badge) {
          badge = document.createElement('div');
          badge.className = 'stale-badge';
          badge.textContent = '⚠ NO SIGNAL';
          wrapper.appendChild(badge);
        }
      } else {
        badge?.remove();
      }
    }
  }

  _resize() {
    this._root.querySelectorAll('canvas').forEach(c => {
      c.width  = c.offsetWidth;
      c.height = c.offsetHeight;
    });
    this._gauges.forEach(list => list.forEach(g => g.draw(g._lastValue)));
  }

  update(signals) {
    Object.assign(this._signals, signals);

    // Rebuild flat snapshot lazily — shared across all multi-signal gauge draws this tick
    let flatCache = null;
    const flat = () => flatCache ?? (flatCache = this._flatSnapshot());

    for (const [signal, entry] of Object.entries(signals)) {
      const list = this._gauges.get(signal);
      if (!list) continue;
      const value = typeof entry === 'object' ? entry.value : entry;
      list.forEach(g => {
        g._isMultiSignal ? g.draw(flat()) : g.draw(value);
      });
    }
  }

  _flatSnapshot() {
    return Object.fromEntries(
      Object.entries(this._signals).map(([k, v]) => [k, typeof v === 'object' ? v.value : v])
    );
  }

}
