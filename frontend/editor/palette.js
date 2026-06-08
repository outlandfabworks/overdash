/**
 * GaugePalette — left-side panel for adding new gauges.
 * Clicking a type finds the first unoccupied grid position and
 * inserts a new gauge with sensible defaults, then calls onAdd.
 */
export class GaugePalette {
  /**
   * @param {function} onAdd  (type, gaugeDef) → called after new gauge is created
   */
  constructor(onAdd) {
    this._onAdd  = onAdd;
    this._panel  = this._buildPanel();
    document.body.appendChild(this._panel);
  }

  show() { this._panel.style.display = 'flex'; }
  hide() { this._panel.style.display = 'none'; }

  setLayout(layout) { this._layout = layout; }

  // ── private ──────────────────────────────────────────────────

  _buildPanel() {
    const el = document.createElement('div');
    el.id = 'edit-palette';
    el.style.display = 'none';

    const title = document.createElement('div');
    title.style.cssText = 'font-family:var(--font-mono);font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:#555;text-align:center;';
    title.textContent = 'ADD';
    el.appendChild(title);

    const sep = document.createElement('div');
    sep.className = 'palette-sep';
    el.appendChild(sep);

    const gaugeTypes = [
      { type: 'circular',  icon: '◎', label: 'Dial'      },
      { type: 'bar',       icon: '▮', label: 'Bar'       },
      { type: 'numeric',   icon: '#', label: 'Num'       },
      { type: 'indicator', icon: '⚠', label: 'Indicator' },
    ];

    for (const { type, icon, label } of gaugeTypes) {
      const card = document.createElement('div');
      card.className = 'palette-item';
      card.innerHTML = `<span class="palette-icon">${icon}</span><span>${label}</span>`;
      card.title = `Add ${label} gauge`;
      card.addEventListener('click', () => this._addGauge(type));
      el.appendChild(card);
    }

    return el;
  }

  _addGauge(type) {
    if (!this._layout) return;
    const { col, row } = type === 'indicator' ? { col: 0, row: 0 } : (this._findFreeCell(2, 2) ?? { col: 0, row: 0 });
    const id = `gauge_${Date.now()}`;

    const defaults = {
      circular: {
        label: 'RPM', unit: '', min: 0, max: 100,
        start_angle: 135, sweep_angle: 270,
        major_ticks: 5, minor_ticks: 5,
        zones: [
          { min: 0, max: 70,  color: '#00e676' },
          { min: 70,max: 90,  color: '#ffa726' },
          { min: 90,max: 100, color: '#ef5350' },
        ],
      },
      bar: {
        label: 'Value', unit: '', min: 0, max: 100,
        orientation: 'vertical',
        zones: [
          { min: 0,  max: 70,  color: '#00e676' },
          { min: 70, max: 90,  color: '#ffa726' },
          { min: 90, max: 100, color: '#ef5350' },
        ],
      },
      numeric: {
        label: 'Value', unit: '', decimals: 0,
        font_size_ratio: 0.4, color: '#e0e0e0',
      },
      indicator: {
        id: 'left_turn', label: 'Left Turn', signal: 'left_turn', color: '#ffa726',
      },
    };

    const isIndicator = type === 'indicator';
    const def = {
      id,
      type,
      signal: isIndicator ? undefined : 'engine_rpm',
      ...(isIndicator
        ? { pos: { x: 42, y: 4, w: 8, h: 10 } }
        : { grid: { col, row, colspan: 2, rowspan: 2 } }),
      config: defaults[type] ?? {},
    };

    this._layout.gauges.push(def);
    this._onAdd(def);
  }

  _findFreeCell(colspan, rowspan) {
    const { columns, rows } = this._layout.grid;
    for (let r = 0; r <= rows - rowspan; r++) {
      for (let c = 0; c <= columns - colspan; c++) {
        const blocked = this._layout.gauges.some(g => {
          const gc = g.grid;
          return c < gc.col + (gc.colspan || 1) &&
                 c + colspan > gc.col &&
                 r < gc.row + (gc.rowspan || 1) &&
                 r + rowspan > gc.row;
        });
        if (!blocked) return { col: c, row: r };
      }
    }
    return null;
  }
}
