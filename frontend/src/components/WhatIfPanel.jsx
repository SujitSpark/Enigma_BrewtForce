import { useEffect, useState } from 'react';
import { api } from '../api';
import { DIM_LABEL, fmt } from '../format';

function Slider({ label, value, min, max, step, onChange, display, id }) {
  return (
    <div className="slider-row">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      <span className="num">{display ?? value}</span>
    </div>
  );
}

const NEW_INDUSTRY = { name: '', role: 'consumer', sector: '', material_id: '', location: '', quantity_tpm: '', processing_step: '' };

function AddIndustry({ meta, onChanged }) {
  const [form, setForm] = useState(NEW_INDUSTRY);
  const [list, setList] = useState([]);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const load = () => api.customIndustries().then(setList).catch(() => {});
  useEffect(() => { load(); }, []);

  const material = meta.materials.find((m) => m.id === form.material_id);
  const sectors = form.role === 'consumer' ? (material?.uses ?? []) : (material?.source_sectors ?? []);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v, ...(k === 'material_id' || k === 'role' ? { sector: '' } : {}) }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.addCustomIndustry({
        ...form,
        sector: form.role === 'processor' ? 'Processing' : form.sector,
        material_id: form.role === 'processor' ? null : form.material_id,
        quantity_tpm: form.quantity_tpm ? Number(form.quantity_tpm) : null,
        processing_step: form.role === 'processor' ? form.processing_step : null,
      });
      setForm(NEW_INDUSTRY);
      await load();
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async (id) => {
    await api.deleteCustomIndustry(id);
    await load();
    onChanged();
  };

  const valid = form.name.trim().length > 1 && form.location.trim() &&
    (form.role === 'processor' ? form.processing_step : form.material_id && form.sector);

  return (
    <div style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
      <div className="panel-head" style={{ padding: 0, border: 0 }}>
        <span className="eyebrow">Add an industry to the ecosystem</span>
        <button type="button" className="btn btn-sm" onClick={() => setOpen((o) => !o)} aria-expanded={open}>{open ? 'Close' : 'Add'}</button>
      </div>
      {list.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, marginTop: 8, display: 'grid', gap: 6 }}>
          {list.map((c) => (
            <li key={c.site.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 13 }}>
              <span>{c.site.name} <span className="muted">· {c.site.sector} · {c.site.city}</span></span>
              <button type="button" className="btn btn-sm" onClick={() => remove(c.site.id)}>Remove</button>
            </li>
          ))}
        </ul>
      )}
      {open && (
        <form onSubmit={submit} className="fields" style={{ marginTop: 10 }}>
          <div className="field wide"><label htmlFor="ni-name">Name</label><input id="ni-name" className="input" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Pune Cement Grinding Co" /></div>
          <div className="field">
            <label htmlFor="ni-role">Role</label>
            <select id="ni-role" className="select" value={form.role} onChange={(e) => set('role', e.target.value)}>
              <option value="consumer">Consumer (needs material)</option>
              <option value="supplier">Supplier (has by-product)</option>
              <option value="processor">Processing hub</option>
            </select>
          </div>
          <div className="field"><label htmlFor="ni-loc">Location</label><input id="ni-loc" className="input" value={form.location} onChange={(e) => set('location', e.target.value)} placeholder="City" /></div>
          {form.role === 'processor' ? (
            <div className="field wide">
              <label htmlFor="ni-step">Capability</label>
              <select id="ni-step" className="select" value={form.processing_step} onChange={(e) => set('processing_step', e.target.value)}>
                <option value="">Select…</option>
                {meta.processing_steps.map((s) => <option key={s.id} value={s.id}>{s.short} — {s.label}</option>)}
              </select>
            </div>
          ) : (
            <>
              <div className="field">
                <label htmlFor="ni-mat">Material</label>
                <select id="ni-mat" className="select" value={form.material_id} onChange={(e) => set('material_id', e.target.value)}>
                  <option value="">Select…</option>
                  {meta.materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="ni-sector">Sector</label>
                <select id="ni-sector" className="select" value={form.sector} onChange={(e) => set('sector', e.target.value)} disabled={!material}>
                  <option value="">Select…</option>
                  {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </>
          )}
          <div className="field wide">
            <label htmlFor="ni-qty">{form.role === 'processor' ? 'Capacity' : form.role === 'supplier' ? 'Supply' : 'Demand'} t/month <span className="hint">optional</span></label>
            <input id="ni-qty" type="number" min="1" className="input num" value={form.quantity_tpm} onChange={(e) => set('quantity_tpm', e.target.value)} />
          </div>
          {error && <p className="notice field wide">{error}</p>}
          <button type="submit" className="btn btn-primary field wide" disabled={!valid} style={{ justifyContent: 'center' }}>Add to ecosystem & recalculate</button>
        </form>
      )}
    </div>
  );
}

export default function WhatIfPanel({ meta, scenario, onChange, onIndustriesChanged }) {
  const w = scenario.weights ?? meta.default_weights;
  const setW = (k, v) => onChange({ ...scenario, weights: { ...w, [k]: v } });
  const auto = scenario.max_road_km == null;

  return (
    <section className="panel" aria-label="What-if simulator">
      <div className="panel-head">
        <span className="panel-title">2 · What-if simulator</span>
        <button type="button" className="btn btn-sm" onClick={() => onChange({})}>Reset</button>
      </div>
      <div className="panel-body" style={{ display: 'grid', gap: 10 }}>
        <label className="toggle">
          <input type="checkbox" checked={auto} onChange={(e) => onChange({ ...scenario, max_road_km: e.target.checked ? null : 100 })} />
          Use each material's economic radius
        </label>
        {!auto && (
          <Slider id="wi-radius" label="Transport radius" min={10} max={800} step={5} value={scenario.max_road_km}
            display={`${scenario.max_road_km} km`} onChange={(v) => onChange({ ...scenario, max_road_km: v })} />
        )}
        <Slider id="wi-freight" label="Freight ₹/t·km" min={1} max={10} step={0.5} value={scenario.transport_inr_per_tkm ?? meta.defaults.transport_inr_per_tkm}
          onChange={(v) => onChange({ ...scenario, transport_inr_per_tkm: v })} />
        <Slider id="wi-carbon" label="Carbon ₹/tCO₂e" min={0} max={5000} step={100} value={scenario.carbon_price_inr_per_t ?? 0}
          display={fmt(scenario.carbon_price_inr_per_t ?? 0)} onChange={(v) => onChange({ ...scenario, carbon_price_inr_per_t: v })} />
        <label className="toggle">
          <input type="checkbox" checked={scenario.use_hubs ?? true} onChange={(e) => onChange({ ...scenario, use_hubs: e.target.checked })} />
          Existing processing hubs available
        </label>

        <div style={{ borderTop: '1px solid var(--line)', paddingTop: 10, display: 'grid', gap: 6 }}>
          <span className="eyebrow">Priority weights</span>
          {Object.keys(DIM_LABEL).map((k) => (
            <Slider key={k} id={`wi-w-${k}`} label={DIM_LABEL[k]} min={0} max={40} step={1} value={w[k]} onChange={(v) => setW(k, v)} display={`${w[k]}`} />
          ))}
          <p className="hint">Weights are a prototype design choice, normalised to 100%, not an official formula.</p>
        </div>
        <AddIndustry meta={meta} onChanged={onIndustriesChanged} />
      </div>
    </section>
  );
}
