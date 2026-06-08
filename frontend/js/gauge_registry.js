const _registry = new Map();

export const GaugeRegistry = {
  register(type, cls) {
    _registry.set(type, cls);
  },
  create(type, canvas, config) {
    const cls = _registry.get(type);
    if (!cls) throw new Error(`Unknown gauge type: ${type}`);
    return new cls(canvas, config);
  },
};
