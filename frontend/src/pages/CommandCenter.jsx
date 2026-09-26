import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { STATUS_LABEL, fmt, inr, tonnes, withOrigin } from '../format';
import NetworkMap, { MapLegend } from '../components/NetworkMap';
import OpportunityDetail from '../components/OpportunityDetail';
import OpportunityList from '../components/OpportunityList';
import { Counter } from '../components/Motion';

export function Kpis({ t }) {
  const items = [
    { label: 'Waste available', value: t.waste_available_tpy, format: tonnes, sub: `${t.streams} by-product streams / yr` },
    { label: 'Potentially diverted', value: t.potentially_diverted_tpy, format: tonnes, sub: `${Math.round((100 * t.potentially_diverted_tpy) / Math.max(1, t.waste_available_tpy))}% of available` },
    { label: 'Net CO₂ impact', value: t.net_tco2e_per_year, format: (v) => `${tonnes(v)}CO₂e`, sub: 'per year, after transport' },
    { label: 'Economic opportunity', value: t.net_inr_per_year, format: inr, sub: 'per year, estimated' },
    { label: 'Opportunities', value: t.opportunities, format: fmt, sub: `${t.by_category.direct} direct · ${t.by_category.multi_step} multi-step · ${t.by_category.hidden} hidden` },
    { label: 'Active exchanges', value: t.active_exchanges, format: fmt, sub: `${t.awaiting_response} awaiting response` },
  ];
  return (
    <div className="kpis" role="list" aria-label="Network totals">
      {items.map((k) => (
        <div className="kpi" role="listitem" key={k.label}>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value"><Counter value={k.value} format={k.format} /></div>
          <div className="kpi-sub">{k.sub}</div>
        </div>
      ))}
    </div>
  );
}

export default function CommandCenter({ statusByOpp, outreachByOpp, onStartOutreach, busy, refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.overview().then((d) => {
      setData(d);
      setSelected((s) => s ?? d.top[0]?.id ?? null);
    }).catch((e) => setError(e.message));
  }, [refreshKey]);

  const opps = useMemo(() => (data?.top ?? []).map((o) => withOrigin(o)), [data]);
  const current = opps.find((o) => o.id === selected);

  if (error) return <div className="page"><p className="notice">{error}</p></div>;
  if (!data) return <div className="page">{[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}</div>;

  return (
    <div className="page">
      <Kpis t={data.totals} />
      <div className="grid-cc">
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <span className="panel-title">Live resource network · top {opps.length} exchanges</span>
              <MapLegend />
            </div>
            <NetworkMap opportunities={opps} selectedId={selected} onSelect={setSelected} hero />
          </section>
          <OpportunityDetail o={current} outreachRec={current && outreachByOpp[current.id]} busy={busy}
            onStartOutreach={(o) => onStartOutreach(o, { company: o.origin.name, location_label: o.origin.city }, o.material_name)} />
        </div>
        <div className="stack">
          <OpportunityList title="Top opportunities" meta="network-wide" opportunities={opps} selectedId={selected}
            onSelect={setSelected} statusByOpp={statusByOpp} showProducer maxHeight={560} />
          <section className="panel" aria-label="Industry responses">
            <div className="panel-head"><span className="panel-title">Industry responses</span><a className="panel-meta" href="#/outreach">Outreach →</a></div>
            {data.responses.length === 0 ? (
              <p className="empty">No responses yet. Start outreach on an opportunity; replies from the email links appear here.</p>
            ) : (
              <ul className="history">
                {data.responses.map((r) => (
                  <li key={r.id}>
                    <button type="button" onClick={() => { window.location.hash = `#/outreach/${r.id}`; }}>
                      <span><span className="h-main">{r.consumer_name}</span><span className="h-sub">{r.material_name} · score {r.score}</span></span>
                      <span className={`tag st-${r.status}`}>{STATUS_LABEL[r.status]}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
