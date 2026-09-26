import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { MONTHS } from '../format';

export const SAMPLES = [
  { label: 'Fly ash · Chandrapur', text: 'Our thermal power station at Chandrapur produces 1.2 lakh tonnes per annum of dry fly ash, available year-round. We would like to connect with cement and brick manufacturers who can lift it regularly.' },
  { label: 'Steel slag · Pune', text: 'We are ABC Steel Pvt Ltd located in Pune. We generate approximately 500 tonnes/month of steel slag from our SMS shop and are looking for a responsible, long-term offtake partner.' },
  { label: 'GBF slag · Ballari', text: 'Deccan Ironworks Ltd, based in Ballari, has 20,000 t/month of granulated blast furnace slag available from our blast furnace.' },
  { label: 'Foundry sand · Kolhapur', text: 'Mahalaxmi Castings Pvt Ltd, based in Kolhapur, disposes around 40 TPD of spent foundry sand. Can this be reused instead of landfilling?' },
  { label: 'C&D waste · Pune', text: 'Skyline Builders Pvt Ltd, based in Pune, will generate about 3,000 tonnes per month of demolition waste and concrete debris from October to March.' },
];

export const EMPTY_INTAKE = {
  text: '',
  fields: { material_id: '', quantity_tpm: '', location: '', company: '' },
  months: Array(12).fill(1),
  touched: {},
  extraction: null,
};

export default function IntakePanel({ materials, value, onChange, busy, onAnalyze }) {
  const { text, fields, months, touched, extraction } = value;
  const [reading, setReading] = useState(false);
  const reqId = useRef(0);
  const latest = useRef(value);
  latest.current = value;

  useEffect(() => {
    if (text.trim().length < 20) return undefined;
    const id = ++reqId.current;
    const t = setTimeout(async () => {
      setReading(true);
      try {
        const ex = await api.extract(text);
        if (id !== reqId.current) return;
        const v = latest.current;
        const detected = {
          material_id: ex.material_id ?? '',
          quantity_tpm: ex.quantity?.tonnes_per_month ?? '',
          location: ex.location?.label ?? '',
          company: ex.company ?? '',
        };
        const next = { ...v.fields };
        Object.keys(detected).forEach((k) => { if (!v.touched[k]) next[k] = detected[k]; });
        onChange({ ...v, extraction: ex, fields: next, months: !v.touched.months && ex.availability ? ex.availability.months : v.months });
      } catch {
        /* extraction is best-effort while typing */
      } finally {
        if (id === reqId.current) setReading(false);
      }
    }, 450);
    return () => clearTimeout(t);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps

  const set = (patch, touchedKey) => onChange({ ...value, ...patch, touched: touchedKey ? { ...touched, [touchedKey]: true } : touched });
  const setField = (k, v) => set({ fields: { ...fields, [k]: v } }, k);
  const toggleMonth = (i) => set({ months: months.map((m, j) => (j === i ? (m ? 0 : 1) : m)) }, 'months');
  const detectedCls = (k) => (!touched[k] && extraction && fields[k] !== '' ? 'detected' : '');
  const canRun = !busy && fields.material_id && fields.location && months.some(Boolean);

  const submit = (e) => {
    e.preventDefault();
    if (canRun) onAnalyze();
  };

  return (
    <form className="panel" onSubmit={submit} aria-label="Supply profile">
      <div className="panel-head">
        <span className="panel-title">1 · Supply profile</span>
        {extraction && (
          <span className="confidence" title="Share of key fields found in the text">
            {reading ? 'Reading…' : `${Math.round(extraction.confidence * 100)}% understood`}
            <span className="meter"><span style={{ width: `${extraction.confidence * 100}%` }} /></span>
          </span>
        )}
      </div>
      <div className="panel-body" style={{ display: 'grid', gap: 12 }}>
        <div className="chips" aria-label="Sample emails">
          {SAMPLES.map((s) => (
            <button type="button" className="chip" key={s.label} onClick={() => onChange({ ...EMPTY_INTAKE, text: s.text })}>{s.label}</button>
          ))}
        </div>
        <div className="field">
          <label htmlFor="email">Industrial email or description</label>
          <textarea id="email" className="textarea" value={text} onChange={(e) => set({ text: e.target.value })}
            placeholder="e.g. We are XYZ Steel in Pune, generating 500 tonnes/month of steel slag…" />
        </div>
        <div className="fields">
          <div className="field wide">
            <label htmlFor="material">Material {extraction?.matched_term && !touched.material_id && <span className="hint">found “{extraction.matched_term}”</span>}</label>
            <select id="material" className={`select ${detectedCls('material_id')}`} value={fields.material_id} onChange={(e) => setField('material_id', e.target.value)}>
              <option value="">Select a by-product…</option>
              {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="qty">Tonnes / month {extraction?.quantity && !touched.quantity_tpm && <span className="hint">{extraction.quantity.raw}</span>}</label>
            <input id="qty" type="number" min="1" className={`input num ${detectedCls('quantity_tpm')}`} value={fields.quantity_tpm} onChange={(e) => setField('quantity_tpm', e.target.value)} placeholder="1000" />
          </div>
          <div className="field">
            <label htmlFor="loc">Plant location</label>
            <input id="loc" className={`input ${detectedCls('location')}`} value={fields.location} onChange={(e) => setField('location', e.target.value)} placeholder="City, state" />
          </div>
          <div className="field wide">
            <label htmlFor="company">Company <span className="hint">optional</span></label>
            <input id="company" className={`input ${detectedCls('company')}`} value={fields.company} onChange={(e) => setField('company', e.target.value)} placeholder="Used in outreach" />
          </div>
          <div className="field wide">
            <span className="field-label">Availability {extraction?.availability && !touched.months && <span className="hint">found “{extraction.availability.raw}”</span>}</span>
            <div className="months" role="group" aria-label="Months when the material is available">
              {MONTHS.map((m, i) => (
                <button type="button" key={i} className="month" aria-pressed={!!months[i]} onClick={() => toggleMonth(i)}
                  aria-label={['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][i]}>{m}</button>
              ))}
            </div>
          </div>
        </div>
        <button type="submit" className="btn btn-primary" disabled={!canRun} style={{ justifyContent: 'center' }}>
          {busy ? 'Analysing…' : 'Discover opportunities'}
        </button>
        {!busy && !canRun && (text.trim().length >= 20 || fields.material_id) && (
          <p className="panel-meta">{!fields.material_id ? 'Choose the material to continue.' : !fields.location ? 'Add the plant location to continue.' : 'Select at least one month.'}</p>
        )}
      </div>
    </form>
  );
}
