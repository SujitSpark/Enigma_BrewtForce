import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { fmt } from '../format';

export default function Schemes({ refreshKey }) {
  const [schemes, setSchemes] = useState(null);
  const [net, setNet] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.schemes(), api.network({}, 300)])
      .then(([s, n]) => { setSchemes(s); setNet(n); })
      .catch((e) => setError(e.message));
  }, [refreshKey]);

  const usage = useMemo(() => {
    const u = {};
    (net?.opportunities ?? []).forEach((o) => o.pathways.forEach((p) => {
      const x = (u[p.id] ||= { n: 0, co2: 0, materials: new Set() });
      x.n += 1;
      x.co2 += Math.max(0, o.impact.net_tco2e_per_year);
      x.materials.add(o.material_name);
    }));
    return u;
  }, [net]);

  if (error) return <div className="page"><p className="notice">{error}</p></div>;
  if (!schemes) return <div className="page"><div className="skeleton" style={{ height: 80 }} /></div>;

  return (
    <div className="page">
      <p className="notice info">
        These are <b>potential policy pathways</b>, not guaranteed subsidies. Every match needs an eligibility check, and carbon-credit
        pathways need an approved methodology, monitoring and verification before any reduction is credited.
      </p>
      <div className="grid-cc" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        {schemes.map((s) => {
          const u = usage[s.id];
          return (
            <section className="panel" key={s.id}>
              <div className="panel-head">
                <span className="panel-title">{s.name}</span>
                <span className="tag">{s.type}</span>
              </div>
              <div className="panel-body" style={{ display: 'grid', gap: 10 }}>
                <div className="pathway-auth">{s.authority} · {s.year}</div>
                <p style={{ fontSize: 13, color: 'var(--ink-2)' }}>{s.relevance}</p>
                <div className="stat-row" style={{ marginTop: 0 }}>
                  <div className="stat"><b>{fmt(u?.n ?? 0)}</b><span>opportunities linked</span></div>
                  <div className="stat"><b>{fmt(u?.co2 ?? 0)}</b><span>tCO₂e/yr in those</span></div>
                </div>
                {u && <div className="standards">{[...u.materials].map((m) => <span className="tag" key={m}>{m}</span>)}</div>}
                <div>
                  <span className="eyebrow">Requirements / verification</span>
                  <ul style={{ margin: '6px 0 0 18px', padding: 0, fontSize: 13, color: 'var(--ink-2)' }}>
                    {s.verify.map((v) => <li key={v}>{v}</li>)}
                  </ul>
                </div>
                <a href={s.portal} target="_blank" rel="noreferrer" style={{ color: 'var(--focus)', fontSize: 13 }}>Official portal ↗</a>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
