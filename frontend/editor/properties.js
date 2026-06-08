/**
 * PropertiesPanel — slide-in right panel for editing all gauge config
 * properties without writing code. Renders a dynamic form based on gauge
 * type and calls back immediately on every change so the live canvas updates.
 */
export class PropertiesPanel {
  /**
   * @param {function} onChange  (gaugeDef) → called on every field change
   * @param {function} onDelete  (gaugeId)  → called when delete is pressed
   */
  constructor(onChange, onDelete) {
    this._onChange = onChange;
    this._onDelete = onDelete;
    this._panel = this._buildShell();
    this._currentDef = null;
    document.body.appendChild(this._panel);
  }

  show(gaugeDef, signals = []) {
    this._currentDef = gaugeDef;
    this._signals    = signals;
    this._render();
    this._panel.classList.add('visible');
  }

  hide() {
    this._panel.classList.remove('visible');
    this._currentDef = null;
  }

  // ── private ──────────────────────────────────────────────────

  _buildShell() {
    const el = document.createElement('div');
    el.id = 'edit-properties';
    return el;
  }

  _render() {
    const def = this._currentDef;
    if (!def) return;

    this._panel.innerHTML = '';

    // Header
    const hdr = document.createElement('div');
    hdr.className = 'prop-header';
    hdr.innerHTML = `<span>Gauge: ${def.id}</span>`;
    const closeBtn = document.createElement('button');
    closeBtn.className = 'prop-close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', () => this.hide());
    hdr.appendChild(closeBtn);
    this._panel.appendChild(hdr);

    // Basic section
    this._panel.appendChild(this._sectionBasic(def));

    // Grid position / size
    this._panel.appendChild(this._sectionGrid(def));

    // Type-specific
    if (['circular', 'bar'].includes(def.type)) {
      this._panel.appendChild(this._sectionRange(def));
      this._panel.appendChild(this._sectionZones(def));
    }
    if (def.type === 'bar') {
      this._panel.appendChild(this._sectionBarOptions(def));
    }
    if (def.type === 'circular') {
      this._panel.appendChild(this._sectionCircularOptions(def));
    }
    if (def.type === 'numeric') {
      this._panel.appendChild(this._sectionNumericOptions(def));
    }
    if (def.type === 'indicator') {
      this._panel.appendChild(this._sectionIndicatorOptions(def));
    }

    // Delete
    const actions = document.createElement('div');
    actions.className = 'prop-actions';
    const delBtn = document.createElement('button');
    delBtn.className = 'tb-btn danger';
    delBtn.textContent = 'Delete Gauge';
    delBtn.addEventListener('click', () => this._onDelete(def.id));
    actions.appendChild(delBtn);
    this._panel.appendChild(actions);
  }

  _section(title) {
    const sec = document.createElement('div');
    sec.className = 'prop-section';
    const t = document.createElement('div');
    t.className = 'prop-section-title';
    t.textContent = title;
    sec.appendChild(t);
    return sec;
  }

  _row(labelText, inputEl, hint) {
    const row = document.createElement('div');
    row.className = 'prop-row';
    const lbl = document.createElement('label');
    lbl.textContent = labelText;
    if (hint) {
      const icon = document.createElement('span');
      icon.className = 'prop-hint';
      icon.textContent = 'ⓘ';
      icon.addEventListener('mouseenter', (e) => PropertiesPanel._tipShow(hint, e));
      icon.addEventListener('mousemove',  (e) => PropertiesPanel._tipMove(e));
      icon.addEventListener('mouseleave', ()  => PropertiesPanel._tipHide());
      // Touch: tap to toggle tooltip
      icon.addEventListener('touchstart', (e) => {
        e.preventDefault();
        const el = PropertiesPanel._tipEl;
        if (el && el.style.display !== 'none' && el._hint === hint) {
          PropertiesPanel._tipHide();
        } else {
          PropertiesPanel._tipShow(hint, { clientX: e.touches[0].clientX, clientY: e.touches[0].clientY });
          if (PropertiesPanel._tipEl) PropertiesPanel._tipEl._hint = hint;
          // Auto-hide after 4s on touch
          clearTimeout(PropertiesPanel._tipTimer);
          PropertiesPanel._tipTimer = setTimeout(() => PropertiesPanel._tipHide(), 4000);
        }
      }, { passive: false });
      lbl.appendChild(icon);
    }
    row.appendChild(lbl);
    row.appendChild(inputEl);
    return row;
  }

  // ── Shared fixed-position tooltip (never clipped by panel overflow) ──────
  static _tipEl = null;

  static _ensureTip() {
    if (PropertiesPanel._tipEl) return;
    const el = document.createElement('div');
    el.id = 'prop-tooltip';
    el.style.cssText = `
      position: fixed;
      z-index: 99999;
      max-width: 240px;
      background: #1e2030;
      color: #ccc;
      font-size: 11px;
      font-family: sans-serif;
      line-height: 1.5;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.12);
      box-shadow: 0 4px 16px rgba(0,0,0,0.6);
      pointer-events: none;
      display: none;
      white-space: normal;
    `;
    document.body.appendChild(el);
    PropertiesPanel._tipEl = el;
  }

  static _tipShow(text, e) {
    PropertiesPanel._ensureTip();
    const el = PropertiesPanel._tipEl;
    el.textContent = text;
    el.style.display = 'block';
    PropertiesPanel._tipMove(e);
  }

  static _tipMove(e) {
    const el = PropertiesPanel._tipEl;
    if (!el || el.style.display === 'none') return;
    const pad = 12;
    const vw = window.innerWidth, vh = window.innerHeight;
    const w = el.offsetWidth, h = el.offsetHeight;
    // Try left of cursor, fall back to right
    let x = e.clientX - w - pad;
    if (x < 4) x = e.clientX + pad;
    let y = e.clientY - h / 2;
    y = Math.max(4, Math.min(vh - h - 4, y));
    el.style.left = `${x}px`;
    el.style.top  = `${y}px`;
  }

  static _tipHide() {
    if (PropertiesPanel._tipEl) PropertiesPanel._tipEl.style.display = 'none';
  }

  _textInput(value, onchange) {
    const el = document.createElement('input');
    el.type = 'text';
    el.value = value ?? '';
    el.addEventListener('input', () => { onchange(el.value); this._emit(); });
    return el;
  }

  _numberInput(value, onchange, opts = {}) {
    const el = document.createElement('input');
    el.type = 'number';
    el.value = value ?? '';
    if (opts.step !== undefined) el.step = opts.step;
    if (opts.min  !== undefined) el.min  = opts.min;
    el.addEventListener('input', () => { onchange(parseFloat(el.value)); this._emit(); });
    return el;
  }

  _selectInput(options, value, onchange) {
    const el = document.createElement('select');
    for (const [v, label] of options) {
      const opt = document.createElement('option');
      opt.value   = v;
      opt.textContent = label;
      opt.selected    = v === value;
      el.appendChild(opt);
    }
    el.addEventListener('change', () => { onchange(el.value); this._emit(); });
    return el;
  }

  _colorInput(value, onchange) {
    const el = document.createElement('input');
    el.type  = 'color';
    el.value = value ?? '#ffffff';
    el.addEventListener('input', () => { onchange(el.value); this._emit(); });
    return el;
  }

  _signalInput(value, onchange) {
    // Searchable combobox: text input + datalist for autocomplete
    // Works on both mouse and touch; user can type to filter
    const wrap = document.createElement('div');
    wrap.style.cssText = 'flex:1; position:relative;';

    const listId = `sig-dl-${Math.random().toString(36).slice(2)}`;
    const dl = document.createElement('datalist');
    dl.id = listId;
    for (const s of (this._signals ?? [])) {
      const opt = document.createElement('option');
      opt.value = s;
      dl.appendChild(opt);
    }

    const input = document.createElement('input');
    input.type        = 'text';
    input.value       = value ?? '';
    input.placeholder = this._signals?.length ? 'Type to search…' : 'Enter signal name';
    input.setAttribute('list', listId);
    input.style.cssText = 'width:100%;';
    input.addEventListener('input',  () => { onchange(input.value); this._emit(); });
    input.addEventListener('change', () => { onchange(input.value); this._emit(); });

    wrap.appendChild(input);
    wrap.appendChild(dl);
    return wrap;
  }

  _emit() {
    this._onChange(this._currentDef);
  }

  // ── sections ─────────────────────────────────────────────────

  _sectionBasic(def) {
    const sec = this._section('Identity');
    const cfg = def.config;

    if (def.type !== 'indicator') {
      sec.appendChild(this._row('Signal',
        this._signalInput(def.signal, v => { def.signal = v; }),
        'The data bus signal this gauge reads. Pick from the list — these are the values your vehicle is currently sending.'));
    }

    sec.appendChild(this._row('Type',
      this._selectInput(
        [['circular','Circular'],['bar','Bar'],['numeric','Numeric'],['indicator','Indicator']],
        def.type,
        v => { def.type = v; this._render(); }),
      'The visual style of this gauge. Changing type resets some settings.'));

    sec.appendChild(this._row('Label',
      this._textInput(cfg.label, v => { cfg.label = v; }),
      'Text shown on the gauge face (e.g. "RPM", "COOLANT"). Leave blank to hide it.'));

    return sec;
  }

  _sectionGrid(def) {
    const sec = this._section('Position & Size');

    if (def.pos) {
      // Free-float gauge — show % position/size controls
      const p = def.pos;
      const prow = (lbl, key, min, max, hint) => this._row(lbl,
        this._numberInput(p[key], v => { p[key] = Math.max(min, Math.min(max, Math.round(v * 10) / 10)); },
          { min, max, step: 0.5 }), hint);
      sec.appendChild(prow('Left %',   'x', 0,  95, 'Horizontal position — 0% is the left edge, 100% is the right edge of the dashboard.'));
      sec.appendChild(prow('Top %',    'y', 0,  95, 'Vertical position — 0% is the top edge, 100% is the bottom edge of the dashboard.'));
      sec.appendChild(prow('Width %',  'w', 1, 100, 'Width of the indicator as a percentage of the total dashboard width.'));
      sec.appendChild(prow('Height %', 'h', 1, 100, 'Height of the indicator as a percentage of the total dashboard height.'));
      return sec;
    }

    const g   = def.grid;
    const row = (lbl, key, min, hint) => this._row(lbl,
      this._numberInput(g[key], v => { g[key] = Math.max(min, Math.round(v)); }, { min, step: 1 }), hint);
    sec.appendChild(row('Column',  'col',     0, 'Which grid column this gauge starts in (0 = leftmost).'));
    sec.appendChild(row('Row',     'row',     0, 'Which grid row this gauge starts in (0 = topmost).'));
    sec.appendChild(row('Width',   'colspan', 1, 'How many columns wide this gauge spans.'));
    sec.appendChild(row('Height',  'rowspan', 1, 'How many rows tall this gauge spans.'));
    return sec;
  }

  _sectionRange(def) {
    const sec = this._section('Range');
    const cfg = def.config;
    sec.appendChild(this._row('Min', this._numberInput(cfg.min, v => { cfg.min = v; }, { step: 'any' }),
      'The lowest value on the scale. Anything at or below this sits at the start of the gauge.'));
    sec.appendChild(this._row('Max', this._numberInput(cfg.max, v => { cfg.max = v; }, { step: 'any' }),
      'The highest value on the scale. Anything at or above this pegs at the end of the gauge.'));
    return sec;
  }

  _sectionZones(def) {
    const sec = this._section('Color Zones');
    const cfg = def.config;
    if (!cfg.zones) cfg.zones = [];

    const renderZones = () => {
      // Clear existing zone rows (keep title)
      while (sec.children.length > 1) sec.removeChild(sec.lastChild);

      cfg.zones.forEach((z, i) => {
        const row = document.createElement('div');
        row.className = 'zone-row';

        const col = this._colorInput(z.color, v => { z.color = v; this._emit(); });
        const mn  = document.createElement('input');
        mn.type = 'number'; mn.className = ''; mn.value = z.min;
        mn.addEventListener('input', () => { z.min = parseFloat(mn.value); this._emit(); });

        const dash = document.createElement('span');
        dash.textContent = '–';
        dash.style.color = '#555';

        const mx = document.createElement('input');
        mx.type = 'number'; mx.value = z.max;
        mx.addEventListener('input', () => { z.max = parseFloat(mx.value); this._emit(); });

        const del = document.createElement('button');
        del.className = 'zone-del';
        del.textContent = '×';
        del.addEventListener('click', () => {
          cfg.zones.splice(i, 1);
          this._emit();
          renderZones();
        });

        mn.style.cssText = mx.style.cssText = 'width:56px;background:#12141e;color:#e0e0e0;border:1px solid rgba(255,255,255,0.15);border-radius:4px;padding:2px 5px;font-family:var(--font-mono);font-size:11px;';
        row.append(col, mn, dash, mx, del);
        sec.appendChild(row);
      });

      const addBtn = document.createElement('button');
      addBtn.className = 'btn-add-zone';
      addBtn.textContent = '+ Add Zone';
      addBtn.addEventListener('click', () => {
        const last = cfg.zones[cfg.zones.length - 1];
        cfg.zones.push({ min: last?.max ?? 0, max: (last?.max ?? 0) + 10, color: '#00e676' });
        this._emit();
        renderZones();
      });
      sec.appendChild(addBtn);
    };

    renderZones();
    return sec;
  }

  _rowUnit(def) {
    const cfg    = def.config;
    const signal = (def.signal ?? '').toLowerCase();

    // Infer signal domain from name, show only relevant units
    // Each entry: [display_label, conversion_factor_from_SI_base_unit]
    let units;
    if (/speed|velocity/.test(signal)) {
      units = [['km/h', 1], ['mph', 0.62137]];
    } else if (/temp|coolant|iat|egt|oil_t/.test(signal)) {
      units = [['°C', 1], ['°F', 1.8]];
    } else if (/rpm|revs|engine_speed/.test(signal)) {
      units = [['RPM', 1]];
    } else if (/boost|pressure|map\b|baro|vacuum/.test(signal)) {
      units = [['kPa', 1], ['psi', 0.14504], ['bar', 0.01]];
    } else if (/volt|battery|batt/.test(signal)) {
      units = [['V', 1]];
    } else if (/fuel_rate|consumption|flow/.test(signal)) {
      units = [['L/h', 1], ['gal/h', 0.26417]];
    } else if (/current|amps/.test(signal)) {
      units = [['A', 1]];
    } else if (/fuel|level|load|throttle|percent/.test(signal)) {
      units = [['%', 1]];
    } else if (/odo|odometer|trip|dist/.test(signal)) {
      units = [['km', 1], ['mi', 0.62137]];
    } else {
      units = [['kPa',1],['psi',0.14504],['bar',0.01],
               ['km/h',1],['mph',0.62137],['°C',1],['°F',1.8],
               ['RPM',1],['V',1],['%',1],['A',1],['L/h',1]];
    }

    const current = (cfg.unit && cfg.unit !== '') ? cfg.unit : units[0][0];
    return this._row('Unit', this._selectInput(
      units.map(([u]) => [u, u]),
      current,
      v => {
        const oldConv = cfg.unit_conversion ?? 1;
        const entry   = units.find(([u]) => u === v);
        const newConv = entry ? entry[1] : 1;
        cfg.unit            = v;
        cfg.unit_conversion = newConv;
        // Auto-scale range and zones to match the new unit
        if (Math.abs(oldConv - newConv) > 0.0001) {
          const scale = newConv / oldConv;
          if (cfg.min !== undefined) cfg.min = Math.round(cfg.min * scale * 10) / 10;
          if (cfg.max !== undefined) cfg.max = Math.round(cfg.max * scale * 10) / 10;
          if (cfg.zones) cfg.zones = cfg.zones.map(z => ({
            ...z,
            min: Math.round(z.min * scale * 10) / 10,
            max: Math.round(z.max * scale * 10) / 10,
          }));
        }
        this._render(); // refresh panel so range fields show updated values
      }
    ));
  }

  _sectionBarOptions(def) {
    const sec = this._section('Bar Options');
    const cfg = def.config;
    sec.appendChild(this._row('Orientation',
      this._selectInput([['vertical','Vertical'],['horizontal','Horizontal']],
        cfg.orientation ?? 'vertical',
        v => { cfg.orientation = v; })));
    sec.appendChild(this._rowUnit(def));
    sec.appendChild(this._row('Font',
      this._selectInput(
        [['rajdhani','Rajdhani'],['arial','Arial'],['impact','Impact'],['mono','Monospace']],
        cfg.font_family ?? 'rajdhani',
        v => { cfg.font_family = v; })));
    return sec;
  }

  _sectionCircularOptions(def) {
    const sec = this._section('Dial Shape');
    const cfg = def.config;
    sec.appendChild(this._row('Style',
      this._selectInput(
        [['oem','OEM (navy/chrome)'],['minimal','Minimal (flat arc)'],['retro','Retro (classic)']],
        cfg.style ?? 'oem',
        v => { cfg.style = v; })));
    sec.appendChild(this._rowUnit(def));
    sec.appendChild(this._row('Start°',
      this._numberInput(cfg.start_angle ?? 225, v => { cfg.start_angle = Math.max(0, Math.min(360, v)); }, { step: 1, min: 0, max: 360 }),
      'Where the scale begins, in degrees. 0° = 3 o\'clock, 90° = 6 o\'clock, 180° = 9 o\'clock. Default 225° starts at bottom-left like a car speedo.'));
    sec.appendChild(this._row('Sweep°',
      this._numberInput(cfg.sweep_angle ?? 270, v => { cfg.sweep_angle = Math.max(10, Math.min(360, v)); }, { step: 1, min: 10, max: 360 }),
      'How far the arc spans from start to end, in degrees. 270° is a ¾ circle (typical gauge). 360° makes a full circle.'));
    return sec;
  }

  _sectionNumericOptions(def) {
    const sec  = this._section('Numeric Options');
    const cfg  = def.config;
    sec.appendChild(this._rowUnit(def));
    sec.appendChild(this._row('Font',
      this._selectInput(
        [['rajdhani','Rajdhani'],['arial','Arial'],['impact','Impact'],['mono','Monospace']],
        cfg.font_family ?? 'rajdhani',
        v => { cfg.font_family = v; })));
    sec.appendChild(this._row('Decimals',
      this._numberInput(cfg.decimals ?? 0, v => { cfg.decimals = Math.max(0, Math.round(v)); }, { min: 0, step: 1 }),
      'How many decimal places to show. 0 = whole numbers, 1 = one decimal place (e.g. 14.4V).'));
    sec.appendChild(this._row('Size',
      this._numberInput(cfg.font_size_ratio ?? 0.4, v => { cfg.font_size_ratio = v; }, { step: 0.05 }),
      'Font size relative to the gauge height. 0.4 = 40% of the box height. Increase to fill more of the space.'));
    sec.appendChild(this._row('Color',
      this._colorInput(cfg.color ?? '#e0e0e0', v => { cfg.color = v; }),
      'The colour of the displayed number.'));
    sec.appendChild(this._row('BG Box',
      this._selectInput(
        [['on','Show'],['off','Hide']],
        (cfg.panel_bg === false) ? 'off' : 'on',
        v => { cfg.panel_bg = (v === 'on'); }),
      'Show or hide the dark background rectangle behind the number. Helps readability on busy backgrounds.'));

    // Thresholds
    if (!cfg.thresholds) cfg.thresholds = [];
    const thSec = document.createElement('div');
    thSec.style.marginTop = '6px';
    const thTitle = document.createElement('div');
    thTitle.className = 'prop-section-title';
    thTitle.textContent = 'Thresholds (≤ max → color)';
    thSec.appendChild(thTitle);

    const renderTh = () => {
      while (thSec.children.length > 1) thSec.removeChild(thSec.lastChild);
      cfg.thresholds.forEach((t, i) => {
        const row = document.createElement('div');
        row.className = 'zone-row';
        const col = this._colorInput(t.color, v => { t.color = v; this._emit(); });
        const mx  = document.createElement('input');
        mx.type = 'number'; mx.value = t.max;
        mx.style.cssText = 'width:66px;background:#12141e;color:#e0e0e0;border:1px solid rgba(255,255,255,0.15);border-radius:4px;padding:2px 5px;font-family:var(--font-mono);font-size:11px;';
        mx.addEventListener('input', () => { t.max = parseFloat(mx.value); this._emit(); });
        const del = document.createElement('button');
        del.className = 'zone-del'; del.textContent = '×';
        del.addEventListener('click', () => { cfg.thresholds.splice(i, 1); this._emit(); renderTh(); });
        row.append(col, mx, del);
        thSec.appendChild(row);
      });
      const addBtn = document.createElement('button');
      addBtn.className = 'btn-add-zone'; addBtn.textContent = '+ Add Threshold';
      addBtn.addEventListener('click', () => {
        cfg.thresholds.push({ max: 100, color: '#00e676' });
        this._emit(); renderTh();
      });
      thSec.appendChild(addBtn);
    };
    renderTh();
    sec.appendChild(thSec);
    return sec;
  }

  _sectionIndicatorOptions(def) {
    const sec = this._section('Indicator');
    const cfg = def.config;

    const ICONS = [
      ['left_turn',  'Left Turn'],   ['right_turn',  'Right Turn'],
      ['high_beam',  'High Beam'],   ['low_beam',    'Low Beam'],
      ['mil',        'Check Engine'],['oil',         'Oil Pressure'],
      ['coolant',    'Coolant Temp'],['abs',         'ABS'],
      ['battery',    'Battery'],     ['glow',        'Glow Plug'],
      ['reverse',    'Reverse'],     ['boost_warn',  'Boost Warning'],
      ['body',       'Body DTC'],    ['network',     'Network DTC'],
      ['trans',      'Transmission'],
    ];

    sec.appendChild(this._row('Icon',
      this._selectInput(ICONS, cfg.id ?? 'mil',
        v => { cfg.id = v; }),
      'The warning symbol to display. Pick one that matches what this indicator monitors.'));

    // Signal — always a select so it's clearly interactive.
    const sigs  = this._signals ?? [];
    const cur   = cfg.signal ?? '';
    const opts  = [];
    if (!sigs.includes(cur)) opts.push([cur, cur || '— pick signal —']);
    sigs.forEach(s => opts.push([s, s]));
    if (opts.length === 0) opts.push(['', '— no signals available —']);

    sec.appendChild(this._row('Signal',
      this._selectInput(opts, cur,
        v => { cfg.signal = v; def.signal = v; this._updateTriggerSummary(summary, cfg); }),
      'The data bus signal to watch. The indicator activates when this signal meets the trigger condition.'));

    sec.appendChild(this._row('Color',
      this._colorInput(cfg.color ?? '#ffa726', v => { cfg.color = v; }),
      'The colour the icon glows when active. Red for critical warnings, amber for cautions, green for status lights.'));

    sec.appendChild(this._row('Trigger',
      this._selectInput(
        [['truthy','Non-zero'],['above','Above threshold'],['below','Below threshold']],
        cfg.trigger ?? 'truthy',
        v => { cfg.trigger = v === 'truthy' ? undefined : v; this._render(); this._updateTriggerSummary(summary, cfg); }),
      'When to light up. "Non-zero" activates on any true/active signal. "Above/Below threshold" activates when the value crosses a number you set.'));

    if (cfg.trigger === 'above' || cfg.trigger === 'below') {
      sec.appendChild(this._row('Threshold',
        this._numberInput(cfg.threshold ?? 0, v => { cfg.threshold = v; this._updateTriggerSummary(summary, cfg); }, { step: 1 }),
        'The value the signal must cross to activate the indicator (e.g. 10 for "below 10V").'));
    }

    // Live plain-English summary of what will trigger this indicator
    const summary = document.createElement('div');
    summary.className = 'indicator-summary';
    this._updateTriggerSummary(summary, cfg);
    sec.appendChild(summary);

    return sec;
  }

  _updateTriggerSummary(el, cfg) {
    const sig = cfg.signal || '?';
    const thr = cfg.threshold ?? 0;
    let msg;
    if (cfg.trigger === 'above') {
      msg = `Lights up when <b>${sig}</b> &gt; <b>${thr}</b>`;
    } else if (cfg.trigger === 'below') {
      msg = `Lights up when <b>${sig}</b> &lt; <b>${thr}</b>`;
    } else {
      msg = `Lights up when <b>${sig}</b> is active (non-zero)`;
    }
    el.innerHTML = msg;
  }
}
