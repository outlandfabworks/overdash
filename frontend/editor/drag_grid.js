/**
 * DragGrid — attaches drag-to-move and resize-handle interaction to all
 * gauge wrappers in edit mode. Works directly on the CSS grid wrappers so
 * no ghost elements are needed; CSS grid position is updated live during
 * the drag and committed to the layout object on pointerup.
 */
export class DragGrid {
  /**
   * @param {HTMLElement}   root
   * @param {object}        layout       — layout config (mutated in-place on drop)
   * @param {function}      onUpdate     — called after every committed layout change
   * @param {function}      onSelect     — called with gaugeId when user clicks a gauge
   */
  constructor(root, layout, onUpdate, onSelect, onDelete) {
    this._root     = root;
    this._layout   = layout;
    this._onUpdate = onUpdate;
    this._onSelect = onSelect;
    this._onDelete = onDelete;
    this._overlays = new Map(); // gaugeId -> overlay div
    this._boundResize = () => this._repositionAll();
  }

  attach(wrapperMap) {
    this._wrapperMap = wrapperMap;
    this._overlays.clear();

    for (const [id, wrapper] of wrapperMap) {
      const def = this._defById(id);
      if (!def) continue;
      const overlay = this._createOverlay(wrapper, def);
      this._overlays.set(id, overlay);
    }

    this._drawGridOverlay();
    window.addEventListener('resize', this._boundResize);
  }

  detach() {
    for (const overlay of this._overlays.values()) overlay.remove();
    this._overlays.clear();
    if (this._gridCanvas) { this._gridCanvas.remove(); this._gridCanvas = null; }
    window.removeEventListener('resize', this._boundResize);
  }

  updateSelected(id) {
    for (const [oid, ov] of this._overlays) {
      ov.classList.toggle('selected', oid === id);
    }
  }

  // ── internal ────────────────────────────────────────────────

  _defById(id) {
    return this._layout.gauges.find(g => g.id === id);
  }

  _cellMetrics() {
    const rect = this._root.getBoundingClientRect();
    const { columns: cols, rows, gap_px: gap = 8 } = this._layout.grid;
    const cellW = (rect.width  - (cols + 1) * gap) / cols;
    const cellH = (rect.height - (rows + 1) * gap) / rows;
    return { rect, cols, rows, gap, cellW, cellH };
  }

  _pixelToCell(clientX, clientY) {
    const { rect, cols, rows, gap, cellW, cellH } = this._cellMetrics();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
      col: Math.max(0, Math.min(cols - 1, Math.floor((x - gap) / (cellW + gap)))),
      row: Math.max(0, Math.min(rows - 1, Math.floor((y - gap) / (cellH + gap)))),
    };
  }

  _hasOverlap(skipId, col, row, colspan, rowspan) {
    return this._layout.gauges.some(g => {
      if (g.id === skipId || g.pos) return false;  // pos gauges float freely
      const gc = g.grid;
      return col < gc.col + (gc.colspan || 1) &&
             col + colspan > gc.col &&
             row < gc.row + (gc.rowspan || 1) &&
             row + rowspan > gc.row;
    });
  }

  _inBounds(col, row, colspan, rowspan) {
    const { cols, rows } = this._layout.grid;
    return col >= 0 && row >= 0 &&
           col + colspan <= cols &&
           row + rowspan <= rows;
  }

  _applyGridPos(wrapper, col, row, colspan, rowspan) {
    wrapper.style.gridColumn = `${col + 1} / span ${colspan}`;
    wrapper.style.gridRow    = `${row + 1} / span ${rowspan}`;
  }

  _targetCell(topLeftX, topLeftY, cs, rs, cols, rows) {
    const { col: rawCol, row: rawRow } = this._pixelToCell(topLeftX, topLeftY);
    return {
      col: Math.max(0, Math.min(cols - cs, rawCol)),
      row: Math.max(0, Math.min(rows - rs, rawRow)),
    };
  }

  _repositionAll() {
    this._onUpdate(this._layout, /* silent= */ true);
    this._drawGridOverlay();
  }

  _drawGridOverlay() {
    if (!this._gridCanvas) {
      this._gridCanvas = document.createElement('canvas');
      this._gridCanvas.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:5;';
      this._root.appendChild(this._gridCanvas);
    }
    const rect = this._root.getBoundingClientRect();
    const cv   = this._gridCanvas;
    cv.width   = rect.width;
    cv.height  = rect.height;
    const ctx  = cv.getContext('2d');
    ctx.clearRect(0, 0, cv.width, cv.height);

    const { columns: cols, rows, gap_px: gap = 8 } = this._layout.grid;
    const cellW = (rect.width  - (cols + 1) * gap) / cols;
    const cellH = (rect.height - (rows + 1) * gap) / rows;

    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth   = 1;

    // Vertical lines
    for (let c = 0; c <= cols; c++) {
      const x = gap + c * (cellW + gap) - gap / 2;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, rect.height); ctx.stroke();
    }
    // Horizontal lines
    for (let r = 0; r <= rows; r++) {
      const y = gap + r * (cellH + gap) - gap / 2;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(rect.width, y); ctx.stroke();
    }
  }

  _createOverlay(wrapper, def) {
    const overlay = document.createElement('div');
    overlay.className = 'gauge-edit-overlay';
    if (def.pos) overlay.classList.add('float-overlay');

    const chip = document.createElement('div');
    chip.className = 'gauge-label-chip';
    chip.textContent = def.pos ? (def.config?.id ?? 'indicator') : (def.signal ?? def.type);
    overlay.appendChild(chip);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'gauge-delete-btn';
    deleteBtn.textContent = '🗑';
    deleteBtn.title = 'Delete gauge';
    deleteBtn.addEventListener('pointerdown', (e) => { e.stopPropagation(); e.preventDefault(); });
    deleteBtn.addEventListener('pointerup',   (e) => e.stopPropagation());
    deleteBtn.addEventListener('click',       (e) => { e.stopPropagation(); if (this._onDelete) this._onDelete(def.id); });
    overlay.appendChild(deleteBtn);

    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'gauge-resize-handle';
    overlay.appendChild(resizeHandle);

    wrapper.style.position = wrapper.style.position || 'relative';
    wrapper.appendChild(overlay);

    let dragging  = false;
    let hasMoved  = false;
    let startPtrX = 0;
    let startPtrY = 0;

    if (def.pos) {
      // ── Free-float drag (pos gauges) ─────────────────────────
      let startX = 0, startY = 0;   // pos.x/y at drag start

      overlay.addEventListener('pointerdown', (e) => {
        if (e.target === resizeHandle || e.target === deleteBtn) return;
        e.preventDefault();
        overlay.setPointerCapture(e.pointerId);
        dragging  = true; hasMoved = false;
        startPtrX = e.clientX; startPtrY = e.clientY;
        startX = def.pos.x; startY = def.pos.y;
        this.updateSelected(def.id);
      });

      overlay.addEventListener('pointermove', (e) => {
        if (!dragging) return;
        if (!hasMoved && Math.abs(e.clientX - startPtrX) < 4 && Math.abs(e.clientY - startPtrY) < 4) return;
        hasMoved = true;
        const rect = this._root.getBoundingClientRect();
        const dx = (e.clientX - startPtrX) / rect.width  * 100;
        const dy = (e.clientY - startPtrY) / rect.height * 100;
        const x = Math.max(0, Math.min(100 - def.pos.w, startX + dx));
        const y = Math.max(0, Math.min(100 - def.pos.h, startY + dy));
        wrapper.style.left = `${x}%`;
        wrapper.style.top  = `${y}%`;
      });

      overlay.addEventListener('pointerup', (e) => {
        if (!dragging) return;
        dragging = false;
        if (!hasMoved) { this._onSelect(def.id); this._onUpdate(this._layout); return; }
        const rect = this._root.getBoundingClientRect();
        const dx = (e.clientX - startPtrX) / rect.width  * 100;
        const dy = (e.clientY - startPtrY) / rect.height * 100;
        def.pos.x = Math.max(0, Math.min(100 - def.pos.w, Math.round((startX + dx) * 10) / 10));
        def.pos.y = Math.max(0, Math.min(100 - def.pos.h, Math.round((startY + dy) * 10) / 10));
        this._onUpdate(this._layout);
      });

      // ── Resize (pos gauges) ──────────────────────────────────
      let resizing = false;

      resizeHandle.addEventListener('pointerdown', (e) => {
        e.preventDefault(); e.stopPropagation();
        resizeHandle.setPointerCapture(e.pointerId);
        resizing = true;
      });

      resizeHandle.addEventListener('pointermove', (e) => {
        if (!resizing) return;
        const rect = this._root.getBoundingClientRect();
        const rx = (e.clientX - rect.left) / rect.width  * 100;
        const ry = (e.clientY - rect.top)  / rect.height * 100;
        def.pos.w = Math.max(2, Math.round((rx - def.pos.x) * 10) / 10);
        def.pos.h = Math.max(2, Math.round((ry - def.pos.y) * 10) / 10);
        wrapper.style.width  = `${def.pos.w}%`;
        wrapper.style.height = `${def.pos.h}%`;
      });

      resizeHandle.addEventListener('pointerup', () => {
        if (!resizing) return;
        resizing = false;
        this._onUpdate(this._layout);
      });

    } else {
      // ── Grid-snap drag ────────────────────────────────────────
      let dragColOffset = 0;
      let dragRowOffset = 0;

      overlay.addEventListener('pointerdown', (e) => {
        if (e.target === resizeHandle || e.target === deleteBtn) return;
        e.preventDefault();
        overlay.setPointerCapture(e.pointerId);
        dragging  = true; hasMoved = false;
        startPtrX = e.clientX; startPtrY = e.clientY;
        const ptrCell = this._pixelToCell(e.clientX, e.clientY);
        dragColOffset = ptrCell.col - (def.grid.col ?? 0);
        dragRowOffset = ptrCell.row - (def.grid.row ?? 0);
        this.updateSelected(def.id);
      });

      overlay.addEventListener('pointermove', (e) => {
        if (!dragging) return;
        if (!hasMoved) {
          if (Math.abs(e.clientX - startPtrX) < 5 && Math.abs(e.clientY - startPtrY) < 5) return;
          hasMoved = true;
        }
        const cs = def.grid.colspan || 1;
        const rs = def.grid.rowspan || 1;
        const { columns: cols, rows } = this._layout.grid;
        const { col: ptrCol, row: ptrRow } = this._pixelToCell(e.clientX, e.clientY);
        const col = Math.max(0, Math.min(cols - cs, ptrCol - dragColOffset));
        const row = Math.max(0, Math.min(rows - rs, ptrRow - dragRowOffset));
        const valid = !this._hasOverlap(def.id, col, row, cs, rs);
        overlay.classList.toggle('drag-valid',   valid);
        overlay.classList.toggle('drag-invalid', !valid);
        this._applyGridPos(wrapper, col, row, cs, rs);
      });

      overlay.addEventListener('pointerup', (e) => {
        if (!dragging) return;
        dragging = false;
        overlay.classList.remove('drag-valid', 'drag-invalid');
        if (!hasMoved) { this._onSelect(def.id); this._onUpdate(this._layout); return; }
        const cs = def.grid.colspan || 1;
        const rs = def.grid.rowspan || 1;
        const { columns: cols, rows } = this._layout.grid;
        const { col: ptrCol, row: ptrRow } = this._pixelToCell(e.clientX, e.clientY);
        const col = Math.max(0, Math.min(cols - cs, ptrCol - dragColOffset));
        const row = Math.max(0, Math.min(rows - rs, ptrRow - dragRowOffset));
        if (!this._hasOverlap(def.id, col, row, cs, rs)) {
          def.grid.col = col; def.grid.row = row;
        }
        this._onUpdate(this._layout);
      });

      // ── Grid resize ───────────────────────────────────────────
      let resizing = false;

      resizeHandle.addEventListener('pointerdown', (e) => {
        e.preventDefault(); e.stopPropagation();
        resizeHandle.setPointerCapture(e.pointerId);
        resizing = true;
      });

      resizeHandle.addEventListener('pointermove', (e) => {
        if (!resizing) return;
        const { col: targetCol, row: targetRow } = this._pixelToCell(e.clientX, e.clientY);
        const newCs = Math.max(1, targetCol - def.grid.col + 1);
        const newRs = Math.max(1, targetRow - def.grid.row + 1);
        const { columns: cols, rows } = this._layout.grid;
        def.grid.colspan = Math.min(newCs, cols - def.grid.col);
        def.grid.rowspan = Math.min(newRs, rows - def.grid.row);
        this._applyGridPos(wrapper, def.grid.col, def.grid.row, def.grid.colspan, def.grid.rowspan);
        chip.textContent = `${def.signal}  ${def.grid.colspan}×${def.grid.rowspan}`;
      });

      resizeHandle.addEventListener('pointerup', () => {
        if (!resizing) return;
        resizing = false;
        chip.textContent = def.signal ?? def.type;
        this._onUpdate(this._layout);
      });
    }

    return overlay;
  }
}
