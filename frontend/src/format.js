export const fmt = (n, digits = 0) =>
  n == null || Number.isNaN(n) ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: digits });

export function inr(n) {
  if (n == null || Number.isNaN(n)) return '—';
  const sign = n < 0 ? '−' : '';
  const a = Math.abs(n);
  if (a >= 1e7) return `${sign}₹${fmt(a / 1e7, 1)} Cr`;
  if (a >= 1e5) return `${sign}₹${fmt(a / 1e5, 1)} L`;
  return `${sign}₹${fmt(a)}`;
}

export function tonnes(n) {
  if (n == null) return '—';
  const a = Math.abs(n);
  if (a >= 1e6) return `${fmt(n / 1e6, 2)} Mt`;
  if (a >= 1e3) return `${fmt(n / 1e3, 1)} kt`;
  return `${fmt(n)} t`;
}

export const slug = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');

export const CATEGORY_LABEL = { direct: 'Direct', multi_step: 'Multi-step', hidden: 'Hidden' };
export const PATHWAY_LABEL = {
  direct: 'Direct use',
  in_house: 'In-house processing',
  via_hub: 'Via processing hub',
  missing_hub: 'Missing processing hub',
};
export const STATUS_LABEL = {
  draft: 'Draft',
  sent: 'Sent',
  interested: 'Interested',
  more_info: 'Needs info',
  not_feasible: 'Not feasible',
};
export const DIM_LABEL = {
  material: 'Material',
  quantity: 'Quantity',
  geography: 'Geography',
  processing: 'Processing',
  timing: 'Timing',
  environment: 'Environment',
  economics: 'Economics',
};
export const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

/** Normalise an opportunity from /analyze (origin = supplier) or /network (origin = producer). */
export function withOrigin(o, supplier, materialName) {
  const origin = o.producer
    ? { name: o.producer.name, lat: o.producer.lat, lon: o.producer.lon, city: o.producer.city }
    : { name: supplier?.company || 'Your plant', lat: supplier?.lat, lon: supplier?.lon, city: supplier?.location_label };
  return { ...o, origin, material_name: o.material_name || materialName };
}
