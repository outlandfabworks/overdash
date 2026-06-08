/**
 * SettingsPanel — gear icon in status bar opens an overlay with:
 *   - Set odometer (km input → POST /api/set_odometer)
 *   - Reset trip   (button  → POST /api/reset_trip)
 */
import { authFetch } from './auth.js';

export class SettingsPanel {
  constructor(apiBase) {
    this._api = apiBase;
    this._build();
  }

  // ── Build DOM ─────────────────────────────────────────────────────────────

  _build() {
    // Gear button in status bar
    const btn = document.createElement('button');
    btn.id          = 'settings-btn';
    btn.textContent = '⚙';
    btn.title       = 'Settings';
    btn.addEventListener('click', () => this._open());
    document.getElementById('status-bar').appendChild(btn);

    // Overlay
    const overlay = document.createElement('div');
    overlay.id = 'settings-overlay';
    overlay.innerHTML = `
      <div id="settings-panel">
        <h2>⚙ Settings</h2>

        <div class="settings-section">
          <h3>Odometer</h3>
          <div class="settings-row">
            <input id="odo-input" type="number" min="0" step="1" placeholder="distance">
            <button class="btn-unit-toggle" id="odo-unit-btn">km</button>
            <button class="btn-set" id="odo-set-btn">Set</button>
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.3);margin-top:4px;" id="odo-equiv"></div>
          <div class="settings-feedback" id="odo-feedback"></div>
        </div>

        <div class="settings-section">
          <h3>Trip Counter</h3>
          <div class="settings-row">
            <span class="settings-value" id="trip-display">—</span>
            <button class="btn-reset" id="trip-reset-btn">Reset</button>
          </div>
          <div class="settings-feedback" id="trip-feedback"></div>
        </div>

        <div class="settings-section" id="gpio-section">
          <h3>GPIO Inputs</h3>
          <div id="gpio-inputs-body">
            <div style="color:rgba(255,255,255,0.3);font-size:12px;padding:6px 0">Loading…</div>
          </div>
          <div class="settings-feedback" id="gpio-feedback"></div>
        </div>

        <div class="settings-section" id="sim-section">
          <h3>Simulation</h3>
          <div id="sim-controls">
            <div style="color:rgba(255,255,255,0.3);font-size:12px;padding:6px 0">Loading…</div>
          </div>
        </div>

        <button class="btn-close" id="settings-close-btn">Close</button>
      </div>
    `;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', e => {
      if (e.target === overlay) this._close();
    });
    overlay.querySelector('#settings-close-btn')
           .addEventListener('click', () => this._close());

    overlay.querySelector('#odo-set-btn')
           .addEventListener('click', () => this._setOdometer());
    overlay.querySelector('#trip-reset-btn')
           .addEventListener('click', () => this._resetTrip());

    this._overlay      = overlay;
    this._odoInput     = overlay.querySelector('#odo-input');
    this._odoFeedback  = overlay.querySelector('#odo-feedback');
    this._odoEquiv     = overlay.querySelector('#odo-equiv');
    this._odoUnitBtn   = overlay.querySelector('#odo-unit-btn');
    this._tripDisplay  = overlay.querySelector('#trip-display');
    this._tripFeedback = overlay.querySelector('#trip-feedback');
    this._gpioBody     = overlay.querySelector('#gpio-inputs-body');
    this._gpioFeedback = overlay.querySelector('#gpio-feedback');
    this._gpioInputs   = [];
    this._simControls  = overlay.querySelector('#sim-controls');

    // Unit is km by default; toggle switches between km ↔ mi
    this._odoUnit = 'km';
    this._odoUnitBtn.addEventListener('click', () => {
      const cur = parseFloat(this._odoInput.value);
      if (this._odoUnit === 'km') {
        this._odoUnit = 'mi';
        this._odoUnitBtn.textContent = 'mi';
        if (!isNaN(cur)) this._odoInput.value = Math.round(cur * 0.621371);
      } else {
        this._odoUnit = 'km';
        this._odoUnitBtn.textContent = 'km';
        if (!isNaN(cur)) this._odoInput.value = Math.round(cur / 0.621371);
      }
      this._updateOdoEquiv();
    });
    this._odoInput.addEventListener('input', () => this._updateOdoEquiv());
  }

  _updateOdoEquiv() {
    const val = parseFloat(this._odoInput.value);
    if (isNaN(val) || !this._odoEquiv) return;
    if (this._odoUnit === 'km') {
      this._odoEquiv.textContent = `= ${(val * 0.621371).toLocaleString(undefined, {maximumFractionDigits: 0})} mi`;
    } else {
      this._odoEquiv.textContent = `= ${(val / 0.621371).toLocaleString(undefined, {maximumFractionDigits: 0})} km`;
    }
  }

  // ── Open / close ──────────────────────────────────────────────────────────

  async _open() {
    // Populate odometer / trip from signals
    try {
      const res  = await fetch(`${this._api}/api/signals`);
      const sigs = await res.json();
      const odoKm  = sigs['odometer'];
      const tripKm = sigs['trip'];
      if (odoKm != null) {
        const display = this._odoUnit === 'mi'
          ? Math.round(odoKm * 0.621371)
          : Math.round(odoKm);
        this._odoInput.value = display;
        this._updateOdoEquiv();
      }
      if (tripKm != null) {
        if (this._odoUnit === 'mi') {
          this._tripDisplay.textContent = `${(Number(tripKm) * 0.621371).toFixed(1)} mi`;
        } else {
          this._tripDisplay.textContent = `${Number(tripKm).toFixed(1)} km`;
        }
      }
    } catch { /* offline */ }

    // Populate GPIO inputs
    try {
      const res  = await fetch(`${this._api}/api/gpio_inputs`);
      const data = await res.json();
      this._gpioInputs = data.inputs ?? [];
      this._renderGpio();
    } catch {
      this._gpioBody.innerHTML =
        '<div style="color:rgba(255,255,255,0.3);font-size:12px;padding:6px 0">Unavailable offline</div>';
    }

    // Populate simulation toggles
    await this._loadSimulation();

    this._odoFeedback.textContent  = '';
    this._tripFeedback.textContent = '';
    this._gpioFeedback.textContent = '';
    this._overlay.classList.add('open');
    this._odoInput.focus();
  }

  _close() {
    this._overlay.classList.remove('open');
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async _setOdometer() {
    const val = parseFloat(this._odoInput.value);
    if (isNaN(val) || val < 0) {
      this._flash(this._odoFeedback, 'Enter a valid distance', '#ef5350');
      return;
    }
    // Always send km to the API regardless of displayed unit
    const km = this._odoUnit === 'mi' ? val / 0.621371 : val;
    try {
      await authFetch(`${this._api}/api/set_odometer`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ value_km: km }),
      });
      const label = this._odoUnit === 'mi'
        ? `${val.toLocaleString()} mi (${Math.round(km).toLocaleString()} km)`
        : `${Math.round(km).toLocaleString()} km`;
      this._flash(this._odoFeedback, `Set to ${label}`, '#00e676');
    } catch {
      this._flash(this._odoFeedback, 'Error — server unreachable', '#ef5350');
    }
  }

  async _resetTrip() {
    try {
      await authFetch(`${this._api}/api/reset_trip`, { method: 'POST' });
      this._tripDisplay.textContent = `0.0 ${this._odoUnit ?? 'km'}`;
      this._flash(this._tripFeedback, 'Trip reset', '#00e676');
    } catch {
      this._flash(this._tripFeedback, 'Error — server unreachable', '#ef5350');
    }
  }

  // ── GPIO Inputs ───────────────────────────────────────────────────────────

  _renderGpio() {
    const body = this._gpioBody;
    body.innerHTML = '';

    // Accordion cards — collapsed by default, click header to expand
    this._gpioInputs.forEach((inp, i) => {
      const card = document.createElement('div');
      card.className = 'gpio-card';

      // ── Header (always visible) ─────────────────────────────
      const header = document.createElement('div');
      header.className = 'gpio-card-header';

      const title = document.createElement('span');
      title.className = 'gpio-card-title';
      title.textContent = inp.label || `GPIO ${inp.gpio ?? i}`;

      const sub = document.createElement('span');
      sub.className = 'gpio-card-sub';
      sub.textContent = inp.signal ? `→ ${inp.signal}` : 'no signal';

      const chevron = document.createElement('span');
      chevron.className = 'gpio-card-chevron';
      chevron.textContent = '▼';

      header.append(title, sub, chevron);
      header.addEventListener('click', () => card.classList.toggle('open'));

      // ── Body (hidden until expanded) ────────────────────────
      const body2 = document.createElement('div');
      body2.className = 'gpio-card-body';

      const mkField = (labelText, inputEl) => {
        const r = document.createElement('div');
        r.className = 'gpio-field-row';
        const lbl = document.createElement('label');
        lbl.textContent = labelText;
        r.append(lbl, inputEl);
        return r;
      };

      const pinInput = document.createElement('input');
      pinInput.type = 'number'; pinInput.value = inp.gpio ?? '';
      pinInput.min = 0; pinInput.max = 40; pinInput.step = 1;
      pinInput.placeholder = '0–40';
      pinInput.style.cssText = this._inputCss();
      pinInput.addEventListener('change', () => {
        this._gpioInputs[i].gpio = parseInt(pinInput.value) || 0;
        title.textContent = labelInput.value || `GPIO ${pinInput.value}`;
      });

      const labelInput = document.createElement('input');
      labelInput.type = 'text'; labelInput.value = inp.label ?? '';
      labelInput.placeholder = 'e.g. Glow Plug';
      labelInput.style.cssText = this._inputCss();
      labelInput.addEventListener('input', () => {
        this._gpioInputs[i].label = labelInput.value;
        title.textContent = labelInput.value || `GPIO ${pinInput.value || i}`;
      });

      const sigInput = document.createElement('input');
      sigInput.type = 'text'; sigInput.value = inp.signal ?? '';
      sigInput.placeholder = 'e.g. glow_plug';
      sigInput.style.cssText = this._inputCss();
      sigInput.setAttribute('list', 'gpio-signal-datalist');
      sigInput.addEventListener('input', () => {
        this._gpioInputs[i].signal = sigInput.value.trim();
        sub.textContent = sigInput.value.trim() ? `→ ${sigInput.value.trim()}` : 'no signal';
      });

      const delBtn = document.createElement('button');
      delBtn.textContent = '✕ Remove';
      delBtn.className = 'btn-reset';
      delBtn.style.cssText = 'font-size:12px;padding:6px 12px;margin-top:4px;';
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._gpioInputs.splice(i, 1);
        this._renderGpio();
      });

      body2.appendChild(mkField('GPIO Pin', pinInput));
      body2.appendChild(mkField('Label',    labelInput));
      body2.appendChild(mkField('Signal',   sigInput));
      body2.appendChild(delBtn);

      card.append(header, body2);
      body.appendChild(card);
    });

    // Datalist for signal name autocomplete
    let dl = document.getElementById('gpio-signal-datalist');
    if (!dl) {
      dl = document.createElement('datalist');
      dl.id = 'gpio-signal-datalist';
      document.body.appendChild(dl);
    }

    // Add + row / Save row
    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:8px;margin-top:8px;';

    const addBtn = document.createElement('button');
    addBtn.className   = 'btn-reset';
    addBtn.textContent = '+ Add Input';
    addBtn.addEventListener('click', () => {
      this._gpioInputs.push({ gpio: 0, label: '', signal: '' });
      this._renderGpio();
    });

    const saveBtn = document.createElement('button');
    saveBtn.className   = 'btn-set';
    saveBtn.textContent = 'Save';
    saveBtn.addEventListener('click', () => this._saveGpio());

    actions.append(addBtn, saveBtn);
    body.appendChild(actions);
  }

  _inputCss() {
    return 'flex:1;min-width:0;background:#12141e;color:#e0e0e0;border:1px solid rgba(255,255,255,0.15);border-radius:6px;padding:8px 10px;font-family:var(--font-mono);font-size:13px;min-height:40px;touch-action:manipulation;';
  }

  async _saveGpio() {
    const inputs = this._gpioInputs.filter(i => i.signal?.trim());
    try {
      const res = await authFetch(`${this._api}/api/gpio_inputs`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ inputs }),
      });
      if (res.ok) {
        this._flash(this._gpioFeedback, `Saved — ${inputs.length} inputs active`, '#00e676');
      } else {
        this._flash(this._gpioFeedback, 'Save failed', '#ef5350');
      }
    } catch {
      this._flash(this._gpioFeedback, 'Error — server unreachable', '#ef5350');
    }
  }

  _flash(el, msg, color) {
    el.style.color   = color;
    el.textContent   = msg;
    setTimeout(() => { el.textContent = ''; }, 3000);
  }

  // ── Live update from WebSocket ────────────────────────────────────────────

  // ── Simulation ────────────────────────────────────────────────────────────

  async _loadSimulation() {
    try {
      const res   = await fetch(`${this._api}/api/simulate`);
      const state = await res.json();   // { "GPS": false, "Engine ECU": false, ... }
      this._renderSimulation(state);
    } catch {
      this._simControls.innerHTML =
        '<div style="color:rgba(255,255,255,0.3);font-size:12px;padding:6px 0">Unavailable offline</div>';
    }
  }

  _renderSimulation(state) {
    this._simControls.innerHTML = '';
    const names      = Object.keys(state);
    // "always" sources are permanently simulated (e.g. mock_vehicle) — they
    // can't be turned off and shouldn't count toward the toggleable state.
    const always     = names.filter(n => state[n] === 'always');
    const toggleable = names.filter(n => state[n] !== 'always');
    const anyOn      = toggleable.some(n => state[n]);

    if (!names.length) {
      this._simControls.innerHTML =
        '<div style="color:rgba(255,255,255,0.3);font-size:12px;padding:6px 0">No sources configured</div>';
      return;
    }

    // Always-simulated sources notice (mock_vehicle etc.)
    if (always.length) {
      const alwaysNote = document.createElement('div');
      alwaysNote.style.cssText = 'font-size:12px;color:#ffa726;margin-bottom:8px;line-height:1.5;padding:8px 10px;background:rgba(255,165,0,0.08);border:1px solid rgba(255,165,0,0.2);border-radius:6px;';
      alwaysNote.textContent = '⚠ No hardware input. Simulation only.';
      this._simControls.appendChild(alwaysNote);
    }

    if (!toggleable.length) {
      // Nothing to toggle — all sources are always-simulated
      return;
    }

    // Warning note
    const note = document.createElement('div');
    note.style.cssText = 'font-size:11px;color:rgba(255,255,255,0.35);margin-bottom:10px;line-height:1.4;';
    note.textContent   = 'Simulation is all-or-nothing. All hardware sources switch together — mixing real and simulated data is not permitted.';
    this._simControls.appendChild(note);

    // Single master toggle row
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:4px 0;';

    const lbl = document.createElement('span');
    lbl.textContent   = anyOn ? '⚠ Simulation ON' : 'Simulation Mode';
    lbl.style.cssText = `font-size:14px;font-weight:700;color:${anyOn ? '#ffa726' : '#ccc'};`;

    const toggle = document.createElement('button');
    toggle.style.cssText = `
      width:52px;height:28px;border-radius:14px;border:none;cursor:pointer;
      background:${anyOn ? '#ffa726' : 'rgba(255,255,255,0.12)'};
      transition:background 0.2s;position:relative;touch-action:manipulation;
    `;
    const knob = document.createElement('div');
    knob.style.cssText = `
      position:absolute;top:4px;${anyOn ? 'right:4px' : 'left:4px'};
      width:20px;height:20px;border-radius:50%;background:#fff;
      transition:left 0.15s,right 0.15s;
    `;
    toggle.appendChild(knob);
    toggle.addEventListener('click', async () => {
      if (!anyOn && !confirm(
        'Enable simulation mode?\n\nAll hardware sources will generate fake data. ' +
        'A watermark will appear on the dashboard.\n\n' +
        'Do not use simulation mode while driving.'
      )) return;
      toggle.disabled = true;
      await authFetch(`${this._api}/api/simulate`, {
        method: 'POST',
        body: JSON.stringify({ enabled: !anyOn }),
      });
      await this._loadSimulation();
      toggle.disabled = false;
    });

    row.appendChild(lbl);
    row.appendChild(toggle);
    this._simControls.appendChild(row);

    const srcList = document.createElement('div');
    srcList.style.cssText = 'margin-top:8px;font-size:11px;color:rgba(255,255,255,0.3);';
    srcList.textContent   = 'Affects: ' + toggleable.join(', ');
    this._simControls.appendChild(srcList);
  }

  ingestSignals(signals) {
    if (!this._overlay.classList.contains('open')) return;
    const raw  = signals.trip;
    const trip = (raw != null && typeof raw === 'object') ? raw.value : raw;
    if (trip == null) return;
    const unit = this._odoUnit ?? 'km';
    const val  = unit === 'mi' ? Number(trip) * 0.621371 : Number(trip);
    this._tripDisplay.textContent = `${val.toFixed(1)} ${unit}`;
  }
}
