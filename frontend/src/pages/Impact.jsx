import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { CATEGORY_LABEL, fmt, inr, tonnes } from '../format';
import { Kpis } from './CommandCenter';

function HBarChart({ title, rows, format, unit }) {
  const [tip, setTip] = useState(null);
  const [asTable, setAsTable] = useState(false);
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <section className="panel" aria-label={title}>
      <div className="panel-head">
        <span className="panel-title">{title}</span>
        <button type="button" className="btn btn-sm" onClick={() => setAsTable((t) => !t)} aria-pressed={asTable}>{asTable ? 'Chart' : 'Table'}</button>
      </div>
      {asTable ? (
        <table className="table">
          <thead><tr><th>Material</th><th className="r">{unit}</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.label} style={{ cursor: 'default' }}><td>{r.label}</td><td className="r num">{format(r.value)}</td></tr>)}</tbody>
        </table>
      ) : (
        <div className="panel-body hbar-chart" onMouseLeave={() => setTip(null)}>
          {rows.map((r) => (
            <div className="hbar" key={r.label}
              onMouseMove={(e) => setTip({ x: e.clientX + 12, y: e.clientY + 12, text: `${r.label}: ${format(r.value)} ${unit}` })}>
              <span className="name" title={r.label}>{r.label}</span>
              <span className="track"><span className="fill" style={{ width: `${Math.max(0, (r.value / max) * 100)}%` }} /></span>
              <span className="val">{format(r.value)}</span>
            </div>
          ))}
        </div>
      )}
      {tip && <div className="chart-tip" style={{ left: tip.x, top: tip.y }}>{tip.text}</div>}
    </section>
  );
}

export default function Impact({ refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api.network({}, 300).then(setData).catch((e) => setError(e.message)); }, [refreshKey]);

  const agg = useMemo(() => {
    if (!data) return null;
    const catOf = Object.fromEntries(data.opportunities.map((o) => [o.id, o.category]));
    const byMat = {};
    const byCat = { direct: { t: 0, c: 0, i: 0 }, multi_step: { t: 0, c: 0, i: 0 }, hidden: { t: 0, c: 0, i: 0 } };
    data.streams.forEach((s) => {
      const m = (byMat[s.material_name] ||= { supply: 0, t: 0, c: 0, i: 0 });
      m.supply += s.supply_tpm * 12;
      s.allocation.forEach((a) => {
        m.t += a.tonnes; m.c += a.tco2e; m.i += a.inr;
        const k = byCat[catOf[a.id]];
        if (k) { k.t += a.tonnes; k.c += a.tco2e; k.i += a.inr; }
      });
    });
    const rows = (key) => Object.entries(byMat).map(([label, v]) => ({ label, value: v[key] })).sort((a, b) => b.value - a.value);
    return { byMat, byCat, rows };
  }, [data]);

  if (error) return <div className="page"><p className="notice">{error}</p></div>;
  if (!data) return <div className="page"><div className="skeleton" style={{ height: 80 }} /></div>;

  return (
    <div className="page">
      <Kpis t={data.totals} />
      <div className="grid-cc" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <HBarChart title="Waste diverted · t/yr" unit="t/yr" rows={agg.rows('t')} format={(v) => tonnes(v)} />
        <HBarChart title="Net CO₂e avoided · t/yr" unit="tCO₂e/yr" rows={agg.rows('c')} format={(v) => tonnes(v)} />
        <HBarChart title="Economic opportunity · ₹/yr" unit="per yr" rows={agg.rows('i')} format={inr} />
      </div>
      <div className="grid-cc" style={{ gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)' }}>
        <section className="panel">
          <div className="panel-head"><span className="panel-title">By pathway type</span></div>
          <table className="table">
            <thead><tr><th>Pathway</th><th className="r">Diverted</th><th className="r">tCO₂e/yr</th><th className="r">₹/yr</th></tr></thead>
            <tbody>
              {Object.entries(agg.byCat).map(([k, v]) => (
                <tr key={k} style={{ cursor: 'default' }}>
                  <td><span className={`tag cat-${k}`}>{CATEGORY_LABEL[k]}</span></td>
                  <td className="r num">{tonnes(v.t)}</td><td className="r num">{fmt(v.c)}</td><td className="r num">{inr(v.i)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel">
          <div className="panel-head"><span className="panel-title">Utilisation by material</span><span className="panel-meta">diverted ÷ available</span></div>
          <table className="table">
            <thead><tr><th>Material</th><th className="r">Available</th><th className="r">Diverted</th><th className="r">Share</th></tr></thead>
            <tbody>
              {Object.entries(agg.byMat).sort((a, b) => b[1].supply - a[1].supply).map(([k, v]) => (
                <tr key={k} style={{ cursor: 'default' }}>
                  <td>{k}</td><td className="r num">{tonnes(v.supply)}</td><td className="r num">{tonnes(v.t)}</td>
                  <td className="r num">{Math.round((100 * v.t) / Math.max(1, v.supply))}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <p className="caveat" style={{ padding: 0 }}>
        Each stream's supply is allocated greedily across its best opportunities, so tonnes are never counted twice.
        Net CO₂e = virgin emissions avoided − processing − transport. These are estimated reductions, not credited reductions:
        carbon-credit eligibility needs an approved methodology, monitoring and verification.
      </p>
    </div>
  );
}
