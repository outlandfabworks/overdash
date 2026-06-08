export class BaseGauge {
  constructor(canvas, config) {
    this._canvas = canvas;
    this._cfg    = config;
    this._lastValue = null;
  }

  get ctx() { return this._canvas.getContext('2d'); }
  get w()   { return this._canvas.width; }
  get h()   { return this._canvas.height; }

  // Return CSS color for value based on zones array [{min,max,color}]
  _zoneColor(value, zones, fallback = '#e0e0e0') {
    if (!zones) return fallback;
    for (const z of zones) {
      if (value >= z.min && value <= z.max) return z.color;
    }
    return fallback;
  }

  /**
   * Override in multi-signal gauges to declare all watched signals.
   * LayoutManager calls this during build() to register subscriptions.
   * @param {object} def — gauge definition from layout JSON
   * @returns {string[]}
   */
  getSignals(def) {
    return [def.signal].filter(Boolean);
  }

  draw(_value) { throw new Error('Not implemented'); }
}
