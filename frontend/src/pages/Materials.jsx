import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { fmt, inr } from '../format';
import { SitesMap } from '../components/NetworkMap';

export default function Materials({ meta, initial }) {
  const [query, setQuery] = useState('');
  const [id, setId] = useState(initial || meta.materials[0]?.id);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setData(null);
    api.material(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  const matches = meta.materials.filter((m) => m.name.toLowerCase().includes(query.toLowerCase()) || m.id.includes(query.toLowerCase()));
  const groups = useMemo(() => (data ? [
    { role: 'src', sites: data.suppliers },
    { role: 'hub', sites: data.hubs },
    { role: 'dst', sites: data.consumers },
  ] : []), [data]);

  const balance = data ? data.totals.supply_tpm / Math.max(1, data.totals.demand_tpm) : 0;

  return (
    <div className="page">
      <section className="panel">
        <div className="panel-body" style={{ display: 'grid', gap: 10 }}>
          <input className="input" type="search" placeholder="Search a material, e.g. fly ash" value={query}
            onChange={(e) => { setQuery(e.target.value); const m = meta.materials.find((x) => x.name.toLowerCase().includes(e.target.value.toLowerCase())); if (m && e.target.value) setId(m.id); }}
            aria-label="Search materials" style={{ maxWidth: 420 }} />
          <div className="chips">
            {matches.map((m) => <button type="button" key={m.id} className="chip" aria-pressed={m.id === id} onClick={() => setId(m.id)}>{m.name}</button>)}
          </div>
        </div>
      </section>
      {error && <p className="notice">{error}</p>}
      {data && (
        <>
          <div className="kpis" style={{ gridTemplateColumns: 'repeat(5, minmax(0,1fr))' }}>
            <div className="kpi"><div className="kpi-label">Available supply</div><div className="kpi-value">{fmt(data.totals.supply_tpm)}</div><div className="kpi-sub">t/month · {data.suppliers.length} suppliers</div></div>
            <div className="kpi"><div className="kpi-label">Current demand</div><div className="kpi-value">{fmt(data.totals.demand_tpm)}</div><div className="kpi-sub">t/month · {data.consumers.length} consumers</div></div>
            <div className="kpi"><div className="kpi-label">Supply : demand</div><div className="kpi-value">{balance.toFixed(1)}×</div><div className="kpi-sub">{balance > 1 ? 'surplus: needs new uses' : 'demand exceeds supply'}</div></div>
            <div className="kpi"><div className="kpi-label">Economic radius</div><div className="kpi-value">{data.material.max_radius_km} km</div><div className="kpi-sub">indicative, by road</div></div>
            <div className="kpi"><div className="kpi-label">Disposal cost</div><div className="kpi-value">{inr(data.material.disposal_cost_inr_per_t)}/t</div><div className="kpi-sub">avoided when reused</div></div>
          </div>
          <div className="grid-2">
            <div className="stack">
              <section className="panel">
                <div className="panel-head"><span className="panel-title">{data.material.name}</span><span className="panel-meta">from {data.material.source_sectors.join(', ')}</span></div>
                <div className="panel-body">
                  <span className="eyebrow">Properties</span>
                  <div className="standards">{data.material.properties.map((p) => <span className="tag" key={p}>{p}</span>)}</div>
                </div>
                <div className="table-scroll">
                  <table className="table">
                    <thead><tr><th>Possible use</th><th>Replaces</th><th>Processing</th><th className="r">Fit</th></tr></thead>
                    <tbody>
                      {data.uses.map((u) => (
                        <tr key={u.use} style={{ cursor: 'default' }}>
                          <td><div style={{ fontWeight: 500 }}>{u.consumer_sector}</div><div className="muted" style={{ fontSize: 12 }}>{u.use}{u.novel ? ' · non-obvious' : ''}</div></td>
                          <td style={{ fontSize: 13 }}>{u.virgin_input}</td>
                          <td style={{ fontSize: 12 }} className="muted">{u.processing_label ? `${u.processing_label}${u.in_house_sectors.length ? ' (in-house possible)' : ''}` : 'None'}</td>
                          <td className="r num">{Math.round(u.compatibility * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel">
                <div className="panel-head"><span className="panel-title">Processing hubs</span><span className="panel-meta">{data.hubs.length}</span></div>
                {data.hubs.length === 0 ? <p className="empty">No processing hub in the dataset. Look in Opportunities for proposed “missing link” hubs.</p> : (
                  <ul className="history">{data.hubs.map((h) => (
                    <li key={h.id}><button type="button" style={{ cursor: 'default' }}><span><span className="h-main">{h.name}</span><span className="h-sub">{h.capabilities.map((c) => `${c.step.replace(/_/g, ' ')} · ${fmt(c.capacity_tpm)} t/mo`).join(', ')}</span></span></button></li>
                  ))}</ul>
                )}
              </section>
            </div>
            <div className="stack">
              <section className="panel">
                <div className="panel-head">
                  <span className="panel-title">Where it is and where it's needed</span>
                  <span className="legend">
                    <span><i className="dot" style={{ background: 'var(--producer)' }} />Supplier</span>
                    <span><i className="dot" style={{ background: 'var(--hub)' }} />Hub</span>
                    <span><i className="dot" style={{ background: 'var(--consumer)' }} />Consumer</span>
                  </span>
                </div>
                <SitesMap groups={groups} />
              </section>
              <div className="grid-2" style={{ gridTemplateColumns: '1fr 1fr' }}>
                {[['Suppliers', data.suppliers], ['Consumers', data.consumers]].map(([title, rows]) => (
                  <section className="panel" key={title}>
                    <div className="panel-head"><span className="panel-title">{title}</span><span className="panel-meta">t/month</span></div>
                    <div className="table-scroll" style={{ maxHeight: 320 }}>
                      <table className="table"><tbody>
                        {rows.map((r) => (
                          <tr key={r.id} style={{ cursor: 'default' }}>
                            <td className="clip"><div style={{ fontWeight: 500 }}>{r.name}</div><div className="muted" style={{ fontSize: 12 }}>{r.city}</div></td>
                            <td className="r num">{fmt(r.quantity_tpm)}</td>
                          </tr>
                        ))}
                      </tbody></table>
                    </div>
                  </section>
                ))}
              </div>
            </div>
          </div>
          <p className="caveat" style={{ padding: 0 }}>Supply and demand volumes are illustrative order-of-magnitude estimates. Plant locations are approximate (town-level).</p>
        </>
      )}
    </div>
  );
}
