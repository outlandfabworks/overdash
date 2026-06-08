/**
 * DTCPanel — bottom-sheet overlay that shows active DTC codes.
 *
 * Opens when:
 *   - User taps an active warning light (LightsGauge fires 'pidash:show-dtcs')
 *   - Programmatically via panel.show()
 *
 * Data comes from the 'dtc_list' signal published by the backend's DTC
 * monitor. The value is a JSON array of { code, desc, type, source } objects.
 */

// Small lookup of common codes. Falls back to "Unknown — refer to scan tool."
const DTC_DESCRIPTIONS = {
  // ── Powertrain ──────────────────────────────────────────────
  P0001: 'Fuel Volume Regulator Control Circuit Open',
  P0016: 'Crankshaft/Camshaft Position Correlation',
  P0087: 'Fuel Rail/System Pressure Too Low',
  P0088: 'Fuel Rail/System Pressure Too High',
  P0100: 'Mass Air Flow Circuit Malfunction',
  P0101: 'MAF Circuit Range/Performance',
  P0102: 'MAF Circuit Low Input',
  P0103: 'MAF Circuit High Input',
  P0105: 'Manifold Absolute Pressure Circuit Malfunction',
  P0107: 'MAP Circuit Low Input',
  P0108: 'MAP Circuit High Input',
  P0110: 'Intake Air Temperature Circuit Malfunction',
  P0115: 'Engine Coolant Temperature Circuit Malfunction',
  P0116: 'Coolant Temp Circuit Range/Performance',
  P0117: 'Coolant Temp Circuit Low Input',
  P0118: 'Coolant Temp Circuit High Input',
  P0180: 'Fuel Temperature Sensor Circuit Malfunction',
  P0190: 'Fuel Rail Pressure Sensor Circuit Malfunction',
  P0191: 'Fuel Rail Pressure Sensor Range/Performance',
  P0192: 'Fuel Rail Pressure Sensor Low Input',
  P0193: 'Fuel Rail Pressure Sensor High Input',
  P0200: 'Injector Circuit Malfunction',
  P0201: 'Injector Circuit — Cylinder 1',
  P0202: 'Injector Circuit — Cylinder 2',
  P0203: 'Injector Circuit — Cylinder 3',
  P0204: 'Injector Circuit — Cylinder 4',
  P0217: 'Engine Coolant Over Temperature',
  P0234: 'Turbocharger Overboost',
  P0235: 'Turbocharger Boost Sensor Circuit Malfunction',
  P0236: 'Turbocharger Boost Sensor Range/Performance',
  P0237: 'Turbocharger Boost Sensor Low Input',
  P0238: 'Turbocharger Boost Sensor High Input',
  P0299: 'Turbocharger Underboost',
  P0300: 'Random/Multiple Cylinder Misfire Detected',
  P0380: 'Glow Plug Circuit A Malfunction',
  P0381: 'Glow Plug Indicator Circuit Malfunction',
  P0401: 'EGR Flow Insufficient Detected',
  P0402: 'EGR Excessive Flow Detected',
  P0403: 'EGR Circuit Malfunction',
  P0404: 'EGR Circuit Range/Performance',
  P0405: 'EGR Sensor A Circuit Low',
  P0470: 'Exhaust Pressure Sensor Malfunction',
  P0471: 'Exhaust Pressure Sensor Range/Performance',
  P0478: 'Exhaust Pressure Control Valve High',
  P0500: 'Vehicle Speed Sensor Malfunction',
  P0530: 'A/C Refrigerant Pressure Sensor Circuit Malfunction',
  P0560: 'System Voltage Malfunction',
  P0562: 'System Voltage Low',
  P0563: 'System Voltage High',
  P0600: 'Serial Communication Link Malfunction',
  P0602: 'Control Module Programming Error',
  P0606: 'PCM/ECM/TCM Processor Fault',
  P0700: 'Transmission Control System Malfunction',
  P0705: 'Transmission Range Sensor Circuit Malfunction',
  P0710: 'Transmission Fluid Temperature Sensor Malfunction',
  P0711: 'Trans Fluid Temp Sensor Range/Performance',
  P0712: 'Trans Fluid Temp Sensor Low Input',
  P0713: 'Trans Fluid Temp Sensor High Input',
  P0720: 'Output Shaft Speed Sensor Malfunction',
  P0730: 'Incorrect Gear Ratio',
  P0740: 'Torque Converter Clutch Circuit Malfunction',
  P0741: 'TCC Stuck Off',
  P0742: 'TCC Stuck On',
  P0743: 'TCC Electrical',
  P0750: 'Shift Solenoid A Malfunction',
  P0755: 'Shift Solenoid B Malfunction',
  P0760: 'Shift Solenoid C Malfunction',
  P2002: 'Diesel Particulate Filter Efficiency Below Threshold',
  P2003: 'DPF Efficiency Below Threshold Bank 2',
  P2047: 'Reductant Injector Circuit Open Bank 1 Sensor 1',
  P2200: 'NOx Sensor Circuit Bank 1',
  P2202: 'NOx Sensor Circuit Low Bank 1',
  // ── Chassis ────────────────────────────────────────────────
  C0031: 'Left Front Wheel Speed Sensor',
  C0034: 'Right Front Wheel Speed Sensor',
  C0037: 'Left Rear Wheel Speed Sensor',
  C0040: 'Right Rear Wheel Speed Sensor',
  C0044: 'ABS Solenoid Valve Circuit Malfunction',
  C0110: 'ABS Motor Circuit Malfunction',
  C0121: 'ABS Valve Relay Circuit Malfunction',
  C0265: 'ABS/EBCM Relay Circuit Active',
  C0268: 'Pump Motor Circuit Open/Shorted',
  C1145: 'Wheel Speed Sensor RF Input Circuit Failure',
  C1155: 'Wheel Speed Sensor LF Input Circuit Failure',
  C1165: 'Wheel Speed Sensor RR Input Circuit Failure',
  C1175: 'Wheel Speed Sensor LR Input Circuit Failure',
  // ── Body ───────────────────────────────────────────────────
  B0001: 'Driver Frontal Stage 1 Deployment Control',
  B0002: 'Driver Frontal Stage 2 Deployment Control',
  B0010: 'Driver Frontal Stage 1 Squib Resistance Low',
  B0051: 'Passenger Frontal Stage 1 Deployment Control',
  B1000: 'ECU Malfunction',
  B1004: 'Battery Voltage High',
  B1008: 'Battery Voltage Low',
  B1049: 'Vehicle Identification Number (VIN) Mismatch',
  B1050: 'Vehicle Configuration Data Mismatch',
  B2141: 'NVM Configuration Failure',
  // ── Network ────────────────────────────────────────────────
  U0001: 'High Speed CAN Communication Bus',
  U0100: 'Lost Communication with ECM/PCM A',
  U0101: 'Lost Communication with TCM',
  U0121: 'Lost Communication with ABS Control Module',
  U0140: 'Lost Communication with Body Control Module',
};

function describeCode(code) {
  return DTC_DESCRIPTIONS[code] ?? 'Unknown — refer to scan tool';
}

export class DTCPanel {
  constructor() {
    this._dtcs    = [];
    this._lastScan = null;
    this._panel   = this._build();
    document.body.appendChild(this._panel);

    // Listen for clicks on active lights
    document.addEventListener('pidash:show-dtcs', () => this.show());
  }

  /** Called by LayoutManager.update() when dtc_list signal arrives. */
  ingestSignals(signals) {
    if ('dtc_list' in signals) {
      const raw = signals['dtc_list'];
      const val = (raw && typeof raw === 'object') ? raw.value : raw;
      try {
        this._dtcs = typeof val === 'string' ? JSON.parse(val) : (val ?? []);
      } catch {
        this._dtcs = [];
      }
    }
    if ('dtc_last_scan' in signals) {
      const raw = signals['dtc_last_scan'];
      this._lastScan = (raw && typeof raw === 'object') ? raw.value : raw;
    }
  }

  show() {
    this._renderList();
    this._panel.classList.add('visible');
  }

  hide() {
    this._panel.classList.remove('visible');
  }

  // ── private ──────────────────────────────────────────────────

  _build() {
    const panel = document.createElement('div');
    panel.id = 'dtc-panel';
    panel.addEventListener('click', (e) => {
      if (e.target === panel) this.hide();
    });

    const sheet = document.createElement('div');
    sheet.id = 'dtc-sheet';

    const hdr = document.createElement('div');
    hdr.className = 'dtc-header';
    hdr.innerHTML = '<span class="dtc-title">Diagnostic Trouble Codes</span>';
    const closeBtn = document.createElement('button');
    closeBtn.className = 'dtc-close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', () => this.hide());
    hdr.appendChild(closeBtn);

    this._metaEl = document.createElement('div');
    this._metaEl.className = 'dtc-meta';

    this._listEl = document.createElement('div');
    this._listEl.className = 'dtc-list';

    sheet.append(hdr, this._metaEl, this._listEl);
    panel.appendChild(sheet);
    return panel;
  }

  _renderList() {
    const ts = this._lastScan
      ? new Date(this._lastScan * 1000).toLocaleTimeString('en-US', { hour12: false })
      : 'never';
    this._metaEl.textContent = `Last scan: ${ts}  ·  ${this._dtcs.length} code${this._dtcs.length !== 1 ? 's' : ''}`;

    this._listEl.innerHTML = '';

    if (!this._dtcs.length) {
      const empty = document.createElement('div');
      empty.className = 'dtc-empty';
      empty.textContent = 'No active diagnostic codes';
      this._listEl.appendChild(empty);
      return;
    }

    for (const dtc of this._dtcs) {
      const code    = dtc.code ?? '?????';
      const category = code[0] ?? 'P';
      const desc    = dtc.desc ?? describeCode(code);
      const type    = dtc.type ?? 'stored';
      const source  = dtc.source ?? '';

      const item = document.createElement('div');
      item.className = 'dtc-item';

      const codeEl = document.createElement('div');
      codeEl.className = `dtc-code ${category}`;
      codeEl.textContent = code;

      const infoEl = document.createElement('div');
      infoEl.className = 'dtc-info';
      infoEl.innerHTML = `
        <div class="dtc-desc">${desc}</div>
        ${source ? `<div class="dtc-source">${source}</div>` : ''}
      `;

      const badge = document.createElement('div');
      badge.className = `dtc-type-badge ${type}`;
      badge.textContent = type;

      item.append(codeEl, infoEl, badge);
      this._listEl.appendChild(item);
    }
  }
}
