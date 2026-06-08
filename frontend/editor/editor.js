/**
 * Editor — top-level controller for the no-code visual editor.
 * Activated by the floating pencil button; coordinates the toolbar,
 * gauge palette, drag-grid, and properties panel.
 */
import { DragGrid }       from './drag_grid.js';
import { PropertiesPanel } from './properties.js';
import { GaugePalette }    from './palette.js';
import { authFetch }       from '../js/auth.js';

export class Editor {
  /**
   * @param {object}        layout        — layout config object (mutated in-place)
   * @param {LayoutManager} manager       — dash layout manager
   * @param {string}        layoutName    — e.g. "tdi_discovery" (used for save URL)
   * @param {string}        apiBase       — e.g. "http://127.0.0.1:8080"
   */
  constructor(layout, manager, layoutName, apiBase) {
    this._layout     = layout;
    this._manager    = manager;
    this._layoutName = layoutName;
    this._apiBase    = apiBase;
    this._active     = false;
    this._selected   = null;

    this._props   = new PropertiesPanel(
      (def) => this._onGaugeChange(def),
      (id)  => this._onGaugeDelete(id),
    );

    this._palette = new GaugePalette((def) => this._onGaugeAdd(def));
    this._palette.setLayout(layout);

    this._dragGrid = new DragGrid(
      document.getElementById('dash-root'),
      layout,
      (l, silent) => this._onLayoutUpdate(l, silent),
      (id) => this._onGaugeSelect(id),
      (id) => this._onGaugeDelete(id),
    );

    this._toggleBtn = this._buildToggleButton();
    document.body.appendChild(this._toggleBtn);
  }

  toggle() {
    this._active ? this.deactivate() : this.activate();
  }

  activate() {
    this._active = true;
    this._toggleBtn.title = 'Exit edit mode';
    this._toggleBtn.style.background = 'rgba(0,230,118,0.15)';
    this._toggleBtn.style.borderColor = '#00e676';

    // Snapshot the layout at the moment edit mode opens so Reset can restore it
    this._snapshot = JSON.stringify(this._layout);
    // Undo/redo stacks
    this._undoStack = [];
    this._redoStack = [];
    this._pushUndo();

    this._toolbar = this._buildToolbar();
    document.body.appendChild(this._toolbar);
    document.body.classList.add('edit-mode');

    this._palette.show();
    this._dragGrid.attach(this._manager.getWrappers());
    this._fetchSignals();
  }

  undo() {
    if (this._undoStack.length < 2) return;
    this._redoStack.push(this._undoStack.pop());
    const state = JSON.parse(this._undoStack[this._undoStack.length - 1]);
    Object.keys(this._layout).forEach(k => delete this._layout[k]);
    Object.assign(this._layout, state);
    this._props.hide(); this._selected = null;
    this._onLayoutUpdate(this._layout);
    this._updateUndoButtons();
  }

  redo() {
    if (!this._redoStack.length) return;
    const state = JSON.parse(this._redoStack.pop());
    Object.keys(this._layout).forEach(k => delete this._layout[k]);
    Object.assign(this._layout, state);
    this._undoStack.push(JSON.stringify(this._layout));
    this._props.hide(); this._selected = null;
    this._onLayoutUpdate(this._layout);
    this._updateUndoButtons();
  }

  _pushUndo() {
    const snap = JSON.stringify(this._layout);
    // Don't push duplicate states
    if (this._undoStack.length && this._undoStack[this._undoStack.length - 1] === snap) return;
    this._undoStack.push(snap);
    if (this._undoStack.length > 20) this._undoStack.shift();
    this._redoStack = [];
    this._updateUndoButtons();
  }

  _updateUndoButtons() {
    if (!this._undoBtn) return;
    this._undoBtn.disabled = this._undoStack.length < 2;
    this._redoBtn.disabled = !this._redoStack.length;
  }

  deactivate() {
    this._active = false;
    this._toggleBtn.title = 'Edit layout';
    this._toggleBtn.style.background = '';
    this._toggleBtn.style.borderColor = '';

    this._toolbar?.remove();
    this._toolbar = null;
    document.body.classList.remove('edit-mode');
    if (this._keyHandler) { document.removeEventListener('keydown', this._keyHandler); this._keyHandler = null; }
    this._undoBtn = null; this._redoBtn = null; this._saveBtn = null;

    this._palette.hide();
    this._props.hide();
    this._dragGrid.detach();
    this._selected = null;
  }

  // ── private ──────────────────────────────────────────────────

  _buildToggleButton() {
    const btn = document.createElement('button');
    btn.id    = 'edit-toggle-btn';
    btn.title = 'Edit layout';
    btn.textContent = '✏';
    btn.style.cssText = `
      position: fixed; bottom: 48px; right: 16px;
      z-index: 300;
      width: 60px; height: 60px;
      border-radius: 50%;
      background: rgba(20,20,30,0.9);
      border: 1px solid rgba(255,255,255,0.2);
      color: #aaa;
      font-size: 22px;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      backdrop-filter: blur(6px);
      transition: background 0.2s, border-color 0.2s;
      touch-action: manipulation;
      box-shadow: 0 2px 12px rgba(0,0,0,0.4);
    `;
    btn.addEventListener('click', () => this.toggle());
    return btn;
  }

  _buildToolbar() {
    const bar = document.createElement('div');
    bar.id = 'edit-toolbar';

    const label = (text) => {
      const el = document.createElement('label');
      el.textContent = text;
      return el;
    };

    // Theme
    bar.appendChild(label('Theme'));
    const themeSelect = document.createElement('select');
    [['dark','Dark'],['light','Light']].forEach(([v, l]) => {
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = l;
      opt.selected = this._layout.meta?.theme === v;
      themeSelect.appendChild(opt);
    });
    themeSelect.addEventListener('change', () => {
      if (!this._layout.meta) this._layout.meta = {};
      this._layout.meta.theme = themeSelect.value;
      document.getElementById('theme-stylesheet').href =
        `css/themes/${themeSelect.value}.css`;
    });
    bar.appendChild(themeSelect);

    // Background color
    bar.appendChild(label('BG'));
    const bgPicker = document.createElement('input');
    bgPicker.type  = 'color';
    bgPicker.value = this._currentBgColor();
    bgPicker.addEventListener('input', () => {
      document.documentElement.style.setProperty('--bg', bgPicker.value);
      if (!this._layout.meta) this._layout.meta = {};
      this._layout.meta.bg_color = bgPicker.value;
    });
    bar.appendChild(bgPicker);

    // Background image + dim control
    bar.appendChild(label('IMG'));
    const bgImgBtn = document.createElement('button');
    bgImgBtn.className   = 'tb-btn';
    bgImgBtn.textContent = this._layout.meta?.bg_image ? 'Change IMG' : '+ BG IMG';
    const bgImgInput = document.createElement('input');
    bgImgInput.type    = 'file';
    bgImgInput.accept  = 'image/*';
    bgImgInput.style.display = 'none';

    const dimLbl    = label('Dim');
    const dimSlider = document.createElement('input');
    dimSlider.type  = 'range';
    dimSlider.min   = 0; dimSlider.max = 80; dimSlider.step = 5;
    dimSlider.value = Math.round((this._layout.meta?.bg_dim ?? 0.3) * 100);
    dimSlider.style.cssText = 'width:55px; accent-color:#00e676; cursor:pointer; vertical-align:middle;';
    dimSlider.addEventListener('input', () => {
      const v = dimSlider.value / 100;
      if (!this._layout.meta) this._layout.meta = {};
      this._layout.meta.bg_dim = v;
      document.getElementById('dash-root').style.setProperty('--bg-dim', v);
    });
    const setDimVisible = (on) => {
      dimLbl.style.display    = on ? '' : 'none';
      dimSlider.style.display = on ? '' : 'none';
    };
    setDimVisible(!!this._layout.meta?.bg_image);

    bgImgInput.addEventListener('change', () => {
      const file = bgImgInput.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target.result;
        if (!this._layout.meta) this._layout.meta = {};
        this._layout.meta.bg_image = dataUrl;
        this._applyBgImage(dataUrl);
        bgImgBtn.textContent = 'Change IMG';
        setDimVisible(true);
      };
      reader.readAsDataURL(file);
    });
    bgImgBtn.addEventListener('click', () => bgImgInput.click());
    if (this._layout.meta?.bg_image) {
      const clearBtn = document.createElement('button');
      clearBtn.className   = 'tb-btn danger';
      clearBtn.textContent = '✕ IMG';
      clearBtn.addEventListener('click', () => {
        delete this._layout.meta.bg_image;
        this._applyBgImage(null);
        clearBtn.remove();
        bgImgBtn.textContent = '+ BG IMG';
        setDimVisible(false);
      });
      bar.appendChild(clearBtn);
    }
    bar.appendChild(bgImgBtn);
    bar.appendChild(bgImgInput);
    bar.appendChild(dimLbl);
    bar.appendChild(dimSlider);

    // Grid columns / rows — stepper buttons for fat-finger friendliness
    bar.appendChild(this._sep());
    bar.appendChild(label('Cols'));
    bar.appendChild(this._stepper(
      this._layout.grid.columns, 1, 24,
      v => { this._layout.grid.columns = v; this._onLayoutUpdate(this._layout); }
    ));
    bar.appendChild(label('Rows'));
    bar.appendChild(this._stepper(
      this._layout.grid.rows, 1, 16,
      v => { this._layout.grid.rows = v; this._onLayoutUpdate(this._layout); }
    ));

    // Undo / Redo
    bar.appendChild(this._sep());

    const undoBtn = document.createElement('button');
    undoBtn.className   = 'tb-btn';
    undoBtn.textContent = '↩ Undo';
    undoBtn.title       = 'Undo last change (Ctrl+Z)';
    undoBtn.disabled    = true;
    undoBtn.addEventListener('click', () => this.undo());
    this._undoBtn = undoBtn;
    bar.appendChild(undoBtn);

    const redoBtn = document.createElement('button');
    redoBtn.className   = 'tb-btn';
    redoBtn.textContent = '↪ Redo';
    redoBtn.title       = 'Redo (Ctrl+Y)';
    redoBtn.disabled    = true;
    redoBtn.addEventListener('click', () => this.redo());
    this._redoBtn = redoBtn;
    bar.appendChild(redoBtn);

    // Keyboard shortcuts
    this._keyHandler = (e) => {
      if (!this._active) return;
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); this.undo(); }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) { e.preventDefault(); this.redo(); }
    };
    document.addEventListener('keydown', this._keyHandler);

    // Reset / Save / Done
    bar.appendChild(this._sep());

    const resetBtn = document.createElement('button');
    resetBtn.className = 'tb-btn danger';
    resetBtn.textContent = 'Reset';
    resetBtn.title = 'Discard all changes and restore layout to when you opened the editor';
    resetBtn.addEventListener('click', () => {
      if (!confirm('Reset layout to the state it was in when you opened the editor?')) return;
      const restored = JSON.parse(this._snapshot);
      Object.keys(this._layout).forEach(k => delete this._layout[k]);
      Object.assign(this._layout, restored);
      this._props.hide();
      this._selected = null;
      this._onLayoutUpdate(this._layout);
    });
    bar.appendChild(resetBtn);

    // ── Export / Import / Load ──────────────────────────────────────────────
    bar.appendChild(this._sep());

    // Export — download current layout as a JSON file
    const exportBtn = document.createElement('button');
    exportBtn.className   = 'tb-btn';
    exportBtn.textContent = '↓ Export';
    exportBtn.title       = 'Download current layout as a JSON file';
    exportBtn.addEventListener('click', () => this._exportLayout());
    bar.appendChild(exportBtn);

    // Import — load a layout from a local JSON file
    const importBtn   = document.createElement('button');
    importBtn.className   = 'tb-btn';
    importBtn.textContent = '↑ Import';
    importBtn.title       = 'Load a layout from a JSON file on your device';
    const importInput = document.createElement('input');
    importInput.type   = 'file';
    importInput.accept = '.json,application/json';
    importInput.style.display = 'none';
    importInput.addEventListener('change', () => this._importLayout(importInput));
    importBtn.addEventListener('click', () => importInput.click());
    bar.appendChild(importBtn);
    bar.appendChild(importInput);

    // Load from server — pick from saved layouts
    const loadBtn = document.createElement('button');
    loadBtn.className   = 'tb-btn';
    loadBtn.textContent = '⊞ Layouts';
    loadBtn.title       = 'Browse and load layouts saved on the Pi';
    loadBtn.addEventListener('click', () => this._showLayoutPicker(loadBtn));
    bar.appendChild(loadBtn);

    // ── Save / Done ─────────────────────────────────────────────────────────
    bar.appendChild(this._sep());

    const saveBtn = document.createElement('button');
    saveBtn.className = 'tb-btn primary';
    saveBtn.textContent = 'Save';
    saveBtn.addEventListener('click', () => this._save(saveBtn));
    this._saveBtn = saveBtn;
    bar.appendChild(saveBtn);

    const doneBtn = document.createElement('button');
    doneBtn.className = 'tb-btn';
    doneBtn.textContent = 'Done';
    doneBtn.addEventListener('click', () => this.deactivate());
    bar.appendChild(doneBtn);

    return bar;
  }

  _sep() {
    const s = document.createElement('div');
    s.className = 'tb-sep';
    return s;
  }

  _stepper(value, min, max, onchange) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;gap:2px;';
    let current = value;
    const display = document.createElement('span');
    display.style.cssText = 'min-width:24px;text-align:center;font-family:var(--font-mono);font-size:13px;color:#e0e0e0;';
    display.textContent = current;
    const btn = (label, delta) => {
      const b = document.createElement('button');
      b.textContent = label;
      b.style.cssText = 'width:32px;height:32px;background:#1a1a2a;color:#ccc;border:1px solid rgba(255,255,255,0.18);border-radius:5px;cursor:pointer;font-size:16px;touch-action:manipulation;line-height:1;';
      b.addEventListener('click', () => {
        current = Math.max(min, Math.min(max, current + delta));
        display.textContent = current;
        onchange(current);
      });
      return b;
    };
    wrap.append(btn('−', -1), display, btn('+', 1));
    return wrap;
  }

  _smallNumber(value, min, max, onchange) {
    const el = document.createElement('input');
    el.type  = 'number';
    el.value = value;
    el.min   = min; el.max = max; el.step = 1;
    el.style.cssText = 'width:42px;background:#1a1a2a;color:#e0e0e0;border:1px solid rgba(255,255,255,0.18);border-radius:4px;padding:2px 5px;font-family:var(--font-mono);font-size:11px;';
    el.addEventListener('change', () => onchange(Math.round(parseFloat(el.value))));
    return el;
  }

  _applyBgImage(dataUrl) {
    const root = document.getElementById('dash-root');
    if (dataUrl) {
      root.style.backgroundImage    = `url(${dataUrl})`;
      root.style.backgroundSize     = 'cover';
      root.style.backgroundPosition = 'center';
      root.classList.add('has-bg-image');
    } else {
      root.style.backgroundImage = '';
      root.classList.remove('has-bg-image');
    }
  }

  _currentBgColor() {
    return this._layout.meta?.bg_color ??
           getComputedStyle(document.documentElement).getPropertyValue('--bg').trim() ??
           '#0d0d0d';
  }

  _onLayoutUpdate(layout, silent = false) {
    this._manager.rebuild(layout);
    if (!silent) {
      this._dragGrid.detach();
      this._dragGrid.attach(this._manager.getWrappers());
      if (this._selected) this._dragGrid.updateSelected(this._selected);
    }
    this._palette.setLayout(layout);
    this._markUnsaved();
  }

  _markUnsaved() {
    if (!this._saveBtn) return;
    if (!this._saveBtn.textContent.startsWith('●')) {
      this._saveBtn.textContent = '● Save';
    }
    this._pushUndo();
  }

  _onGaugeSelect(id) {
    this._selected = id;
    this._dragGrid.updateSelected(id);
    const def = this._layout.gauges.find(g => g.id === id);
    if (!def) return;
    // Re-fetch signals if cache is empty, then show panel
    if (!this._cachedSignals?.length) {
      this._fetchSignals().then(() =>
        this._props.show(def, this._cachedSignals ?? []));
    } else {
      this._props.show(def, this._cachedSignals);
    }
  }

  _onGaugeChange(def) {
    // Gauge config changed via properties panel — rebuild to reflect
    this._manager.rebuild(this._layout);
    this._dragGrid.detach();
    this._dragGrid.attach(this._manager.getWrappers());
    this._dragGrid.updateSelected(def.id);
  }

  _onGaugeDelete(id) {
    this._layout.gauges = this._layout.gauges.filter(g => g.id !== id);
    this._props.hide();
    this._selected = null;
    this._onLayoutUpdate(this._layout);
  }

  _onGaugeAdd(def) {
    this._onLayoutUpdate(this._layout);
    // Select the new gauge so its properties open immediately
    this._onGaugeSelect(def.id);
  }

  async _fetchSignals() {
    const CACHE_KEY = 'pidash_signals';
    try {
      const res = await fetch(`${this._apiBase}/api/signals`);
      if (!res.ok) throw new Error('bad response');
      const data = await res.json();
      this._cachedSignals = Object.keys(data);
      // Persist to localStorage so the editor still works when offline
      try { localStorage.setItem(CACHE_KEY, JSON.stringify(this._cachedSignals)); } catch {}
    } catch {
      // Fall back to cached list from last online session
      if (!this._cachedSignals?.length) {
        try {
          const stored = localStorage.getItem(CACHE_KEY);
          if (stored) this._cachedSignals = JSON.parse(stored);
        } catch {}
      }
      this._cachedSignals = this._cachedSignals ?? [];
      // Show a non-blocking banner so the user knows they're working offline
      if (!this._offlineBanner) this._showOfflineBanner();
    }
  }

  _showOfflineBanner() {
    if (this._offlineBanner) return;
    const b = document.createElement('div');
    b.style.cssText = `
      position: fixed; bottom: 48px; left: 50%; transform: translateX(-50%);
      z-index: 9998; background: #1a1a2e;
      color: #ffa726; border: 1px solid #ffa72644;
      padding: 8px 16px; border-radius: 8px;
      font-family: var(--font-mono); font-size: 12px;
      pointer-events: none;
    `;
    b.textContent = '⚠ Server offline — using cached signal list';
    document.body.appendChild(b);
    this._offlineBanner = b;
    setTimeout(() => { b.remove(); this._offlineBanner = null; }, 5000);
  }

  async _save(btn) {
    const json = JSON.stringify(this._layout, null, 2);
    const url  = `${this._apiBase}/api/layout/${this._layoutName}`;
    btn.textContent = '…';
    btn.disabled    = true;

    let toastMsg, toastOk;
    try {
      const res = await authFetch(url, {
        method: 'PUT',
        body: json,
      });
      if (res.ok) {
        toastMsg = '✓ Layout saved to server';
        toastOk  = true;
        btn.textContent = 'Save';
      } else {
        toastMsg = '✗ Save failed — server returned an error';
        toastOk  = false;
        btn.textContent = '● Save';
      }
    } catch {
      const blob = new Blob([json], { type: 'application/json' });
      const a    = document.createElement('a');
      a.href     = URL.createObjectURL(blob);
      a.download = `${this._layoutName}.json`;
      a.click();
      toastMsg = '↓ Server offline — layout downloaded as file';
      toastOk  = true;
      btn.textContent = 'Save';
    }

    btn.disabled = false;
    this._toast(toastMsg, toastOk);
  }

  _toast(msg, ok = true) {
    const t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = `
      position: fixed; top: 52px; left: 50%; transform: translateX(-50%);
      z-index: 9999;
      background: ${ok ? '#1a2e1a' : '#2e1a1a'};
      color: ${ok ? '#00e676' : '#ef5350'};
      border: 1px solid ${ok ? '#00e676' : '#ef5350'}44;
      padding: 10px 20px;
      border-radius: 8px;
      font-family: var(--font-mono);
      font-size: 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      pointer-events: none;
      transition: opacity 0.4s;
    `;
    document.body.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; }, 2200);
    setTimeout(() => t.remove(), 2600);
  }

  // ── Export / Import / Load ─────────────────────────────────────────────────

  _exportLayout() {
    const name = this._layoutName ?? 'layout';
    const json = JSON.stringify(this._layout, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `${name}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    this._toast(`↓ Exported as ${name}.json`, true);
  }

  _importLayout(input) {
    const file = input.files[0];
    if (!file) return;
    input.value = '';   // reset so the same file can be re-imported
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        // Basic sanity check
        if (!imported.gauges || !imported.grid) {
          throw new Error('Missing required fields (gauges, grid)');
        }
        if (!confirm(`Load layout "${imported.meta?.name ?? file.name}"? This will replace the current layout.`)) return;
        Object.keys(this._layout).forEach(k => delete this._layout[k]);
        Object.assign(this._layout, imported);
        this._props.hide();
        this._selected = null;
        this._snapshot = JSON.stringify(this._layout);
        this._onLayoutUpdate(this._layout);
        this._toast(`✓ Loaded "${file.name}"`, true);
      } catch (err) {
        this._toast(`✗ Invalid layout file: ${err.message}`, false);
      }
    };
    reader.readAsText(file);
  }

  async _showLayoutPicker(anchorBtn) {
    // Remove any existing picker
    document.getElementById('layout-picker-popup')?.remove();

    let layouts = [];
    try {
      const res = await fetch(`${this._apiBase}/api/layouts`);
      layouts   = await res.json();
    } catch {
      this._toast('✗ Could not reach server', false);
      return;
    }

    if (!layouts.length) {
      this._toast('No saved layouts found on server', true);
      return;
    }

    // Build a small popup positioned below the button
    const popup = document.createElement('div');
    popup.id = 'layout-picker-popup';
    popup.style.cssText = `
      position: fixed;
      z-index: 9999;
      background: #1a1a2e;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 8px;
      padding: 6px 0;
      min-width: 180px;
      box-shadow: 0 6px 24px rgba(0,0,0,0.6);
      font-family: var(--font-mono);
      font-size: 13px;
    `;

    const rect = anchorBtn.getBoundingClientRect();
    popup.style.top  = `${rect.bottom + 6}px`;
    popup.style.left = `${rect.left}px`;

    const heading = document.createElement('div');
    heading.textContent = 'SAVED LAYOUTS';
    heading.style.cssText = 'padding:6px 14px 8px;font-size:10px;letter-spacing:.1em;color:#555;border-bottom:1px solid rgba(255,255,255,0.08);';
    popup.appendChild(heading);

    for (const name of layouts) {
      const item = document.createElement('div');
      item.textContent = name;
      item.style.cssText = `
        padding: 10px 16px;
        cursor: pointer;
        color: ${name === this._layoutName ? '#00e676' : '#ccc'};
        background: ${name === this._layoutName ? 'rgba(0,230,118,0.06)' : 'transparent'};
      `;
      item.addEventListener('mouseenter', () => { item.style.background = 'rgba(255,255,255,0.06)'; });
      item.addEventListener('mouseleave', () => { item.style.background = name === this._layoutName ? 'rgba(0,230,118,0.06)' : 'transparent'; });
      item.addEventListener('click', async () => {
        popup.remove();
        if (name === this._layoutName &&
            !confirm(`Reload "${name}" from the server? Unsaved changes will be lost.`)) return;
        try {
          const res     = await fetch(`${this._apiBase}/api/layout/${name}`);
          const fetched = await res.json();
          Object.keys(this._layout).forEach(k => delete this._layout[k]);
          Object.assign(this._layout, fetched);
          this._props.hide();
          this._selected   = null;
          this._layoutName = name;
          this._snapshot   = JSON.stringify(this._layout);
          this._onLayoutUpdate(this._layout);
          this._toast(`✓ Loaded "${name}"`, true);
        } catch {
          this._toast(`✗ Failed to load "${name}"`, false);
        }
      });
      popup.appendChild(item);
    }

    // Close when clicking outside
    const close = (e) => {
      if (!popup.contains(e.target) && e.target !== anchorBtn) {
        popup.remove();
        document.removeEventListener('pointerdown', close);
      }
    };
    document.addEventListener('pointerdown', close);
    document.body.appendChild(popup);
  }
}
