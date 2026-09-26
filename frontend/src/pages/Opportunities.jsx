import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { CATEGORY_LABEL, PATHWAY_LABEL, STATUS_LABEL, fmt, inr, withOrigin } from '../format';
import OpportunityDetail from '../components/OpportunityDetail';
import { CategoryTag, StatusTag } from '../components/OpportunityList';

export default function Opportunities({ meta, statusByOpp, outreachByOpp, onStartOutreach, busy, refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [cat, setCat] = useState('all');
  const [mat, setMat] = useState('all');
  const [status, setStatus] = useState('all');
  const [selected, setSelected] = useState(null);

  useEffect(() => { api.network({}, 300).then(setData).catch((e) => setError(e.message)); }, [refreshKey]);

  const opps = useMemo(() => (data?.opportunities ?? []).map((o) => withOrigin(o)), [data]);
  const shown = opps.filter((o) =>
    (cat === 'all' || o.category === cat) &&
    (mat === 'all' || o.material_id === mat) &&
    (status === 'all' || (status === 'untracked' ? !statusByOpp[o.id] : statusByOpp[o.id] === status)));
  const current = opps.find((o) => o.id === selected);

  return (
    <div className="page">
      <section className="panel">
        <div className="panel-head">
          <span className="panel-title">All opportunities across the network</span>
          <span className="panel-meta">{shown.length} of {opps.length} shown</span>
        </div>
        <div className="panel-body btn-row">
          <select className="select" style={{ width: 'auto' }} value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Pathway">
            <option value="all">All pathways</option>
            {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={mat} onChange={(e) => setMat(e.target.value)} aria-label="Material">
            <option value="all">All materials</option>
            {meta.materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="all">Any status</option>
            <option value="untracked">Not contacted</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        {error && <p className="notice" style={{ margin: '0 16px 16px' }}>{error}</p>}
        {!data && !error && <div className="panel-body" style={{ display: 'grid', gap: 8 }}>{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" />)}</div>}
        {data && (
          <div className="table-scroll" style={{ maxHeight: 460 }}>
            <table className="table">
              <thead>
                <tr><th>Score</th><th>Source → consumer</th><th>Material</th><th>Pathway</th><th className="r">km</th><th className="r">tCO₂e/yr</th><th className="r">₹/yr</th><th>Status</th></tr>
              </thead>
              <tbody>
                {shown.map((o) => (
                  <tr key={o.id} aria-selected={o.id === selected} onClick={() => setSelected(o.id)}>
                    <td className="num">{o.score}</td>
                    <td className="clip"><b style={{ fontWeight: 500 }}>{o.origin.name}</b> → {o.title}</td>
                    <td className="clip">{o.material_name}</td>
                    <td><CategoryTag category={o.category} /> <span className="muted" style={{ fontSize: 12 }}>{PATHWAY_LABEL[o.pathway_type]}</span></td>
                    <td className="r num">{fmt(o.road_km)}</td>
                    <td className="r num">{fmt(o.impact.net_tco2e_per_year)}</td>
                    <td className="r num">{inr(o.economics.net_inr_per_year)}</td>
                    <td>{statusByOpp[o.id] ? <StatusTag status={statusByOpp[o.id]} /> : <span className="muted" style={{ fontSize: 12 }}>—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="caveat">Supply volumes are illustrative estimates for the named plants. Hidden pathways include non-obvious uses and missing processing hubs.</p>
      </section>
      {current && (
        <OpportunityDetail o={current} outreachRec={outreachByOpp[current.id]} busy={busy}
          onStartOutreach={(o) => onStartOutreach(o, { company: o.origin.name, location_label: o.origin.city }, o.material_name)} />
      )}
    </div>
  );
}
