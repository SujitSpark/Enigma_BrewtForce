import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { fmt, inr, tonnes, withOrigin } from '../format';
import IntakePanel from '../components/IntakePanel';
import NetworkMap, { MapLegend } from '../components/NetworkMap';
import OpportunityDetail from '../components/OpportunityDetail';
import OpportunityList from '../components/OpportunityList';
import WhatIfPanel from '../components/WhatIfPanel';

function Delta({ label, from, to, format }) {
  if (from == null || from === to) return <span className="delta">{label} {format(to)}</span>;
  const up = to > from;
  return (
    <span className="delta" style={{ borderColor: up ? 'var(--ok)' : 'var(--bad)' }}>
      {label} {format(from)} → <b style={{ color: up ? 'var(--ok)' : 'var(--bad)' }}>{format(to)}</b>
    </span>
  );
}

function History({ items, onOpen }) {
  if (!items.length) return null;
  return (
    <section className="panel" aria-label="Recent analyses">
      <div className="panel-head"><span className="panel-title">Recent analyses</span><span className="panel-meta">saved in SQLite</span></div>
      <ul className="history">
        {items.map((h) => (
          <li key={h.id}>
            <button type="button" onClick={() => onOpen(h.id)}>
              <span>
                <span className="h-main">{h.company || h.material_name}</span>
                <span className="h-sub">{h.company ? `${h.material_name} · ` : ''}{fmt(h.tonnes_per_month)} t/mo · {h.location}</span>
              </span>
              <span className="h-sub h-top" title={h.top_name || ''}>{h.top_score != null ? `${h.top_score} · ${h.top_name}` : 'no match'}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Analyse({ meta, session, setSession, statusByOpp, outreachByOpp, onStartOutreach, busyOutreach }) {
  const { intake, scenario, result, baseline, selectedId } = session;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const firstRun = useRef(true);

  const patch = useCallback((p) => setSession((s) => ({ ...s, ...p })), [setSession]);
  const loadHistory = () => api.history().then(setHistory).catch(() => {});
  useEffect(() => { loadHistory(); }, []);

  const run = useCallback(async (sc, { asBaseline = false } = {}) => {
    const { fields, text, months } = session.intake;
    setBusy(true);
    setError('');
    try {
      const r = await api.analyze({
        text: text.trim() || null,
        material_id: fields.material_id || null,
        quantity_tpm: fields.quantity_tpm ? Number(fields.quantity_tpm) : null,
        location: fields.location || null,
        company: fields.company || null,
        months,
        scenario: sc,
      });
      setSession((s) => ({
        ...s,
        result: r,
        baseline: asBaseline ? r : s.baseline,
        selectedId: r.opportunities.some((o) => o.id === s.selectedId) ? s.selectedId : r.opportunities[0]?.id ?? null,
      }));
      loadHistory();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, [session.intake, setSession]);

  useEffect(() => {
    if (firstRun.current) { firstRun.current = false; return undefined; }
    if (!session.result) return undefined;
    const t = setTimeout(() => run(scenario), 500);
    return () => clearTimeout(t);
  }, [scenario]); // eslint-disable-line react-hooks/exhaustive-deps

  const opps = useMemo(
    () => (result?.opportunities ?? []).map((o) => withOrigin(o, result.supplier, result.material.name)),
    [result],
  );
  const current = opps.find((o) => o.id === selectedId);
  const s = result?.summary;
  const b = baseline && baseline !== result ? baseline.summary : null;

  const openHistory = async (id) => {
    try {
      const r = await api.historyItem(id);
      patch({ result: r, baseline: r, selectedId: r.opportunities[0]?.id ?? null });
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <div className="grid-2">
        <div className="stack">
          <IntakePanel materials={meta.materials} value={intake} onChange={(v) => patch({ intake: v })} busy={busy}
            onAnalyze={() => run(scenario, { asBaseline: true })} />
          {error && <p className="notice" role="alert">{error}</p>}
          <WhatIfPanel meta={meta} scenario={scenario} onChange={(sc) => patch({ scenario: sc })}
            onIndustriesChanged={() => session.result && run(scenario)} />
          <History items={history} onOpen={openHistory} />
        </div>

        <div className="stack">
          {!result ? (
            <section className="panel">
              <div className="panel-body" style={{ padding: '24px 20px' }}>
                <p className="eyebrow">The pipeline</p>
                <ol style={{ margin: '10px 0 0 18px', padding: 0, color: 'var(--ink-2)', display: 'grid', gap: 6 }}>
                  <li>Paste an industrial email. Material, quantity, location and availability are structured automatically.</li>
                  <li>The engine searches potential uses and finds consumers with matching demand profiles.</li>
                  <li>It discovers <b>direct</b> matches, <b>multi-step</b> routes through processing hubs, and <b>hidden</b> opportunities (non-obvious uses, or a missing hub that would unlock demand).</li>
                  <li>Each is scored on 7 dimensions (material, quantity, geography, processing, timing, environment, economics) with the reasons shown.</li>
                  <li>Change assumptions in the what-if simulator and watch opportunities appear or disappear. Start outreach and track responses.</li>
                </ol>
              </div>
            </section>
          ) : (
            <>
              <section className="panel">
                <div className="panel-head">
                  <span className="panel-title">
                    {result.supplier.company || 'Supply'} · {fmt(result.supply.quantity_tpm)} t/mo {result.material.name.toLowerCase()} · {result.supplier.location_label}
                  </span>
                  <MapLegend />
                </div>
                <div className="panel-body btn-row" style={{ gap: 6 }}>
                  <Delta label="Opportunities" from={b?.count} to={s.count} format={fmt} />
                  <Delta label="Diverted" from={b?.allocated_tpy} to={s.allocated_tpy} format={tonnes} />
                  <Delta label="CO₂e" from={b?.allocated_tco2e} to={s.allocated_tco2e} format={(v) => `${fmt(v)} t`} />
                  <Delta label="Value" from={b?.allocated_inr} to={s.allocated_inr} format={inr} />
                  {busy && <span className="panel-meta">Recalculating…</span>}
                  {result.assumptions.map((a) => <span key={a} className="tag st-more_info">{a}</span>)}
                </div>
                <NetworkMap opportunities={opps} selectedId={selectedId} onSelect={(id) => patch({ selectedId: id })} />
              </section>
              <OpportunityList title="Ranked opportunities" meta="all 7 dimensions" opportunities={opps} selectedId={selectedId}
                onSelect={(id) => patch({ selectedId: id })} statusByOpp={statusByOpp} />
              {opps.length === 0 && (
                <p className="notice info">
                  No opportunities under these assumptions. Widen the transport radius, allow processing hubs, or add a consumer in the simulator.
                </p>
              )}
              <OpportunityDetail o={current} outreachRec={current && outreachByOpp[current.id]} busy={busyOutreach}
                onStartOutreach={(o) => onStartOutreach(o, result.supplier, result.material.name, result.analysis_id)} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
