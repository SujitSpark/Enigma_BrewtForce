import { CATEGORY_LABEL, DIM_LABEL, MONTHS, PATHWAY_LABEL, fmt, inr } from '../format';
import { CategoryTag, StatusTag } from './OpportunityList';

const ICON = { ok: '✓', warn: '!', bad: '×' };

function PathDiagram({ o }) {
  const [l1, l2] = o.legs;
  const src = (
    <div className="path-node src"><b>{o.origin.name}</b><span>{o.origin.city} · {o.material_name}</span></div>
  );
  const dst = (
    <div className="path-node dst" style={{ textAlign: 'right' }}>
      <b>{o.pathway_type === 'missing_hub' ? `${o.consumers.length} potential buyer${o.consumers.length > 1 ? 's' : ''}` : o.consumer.name}</b>
      <span>{o.consumer_sector}{o.pathway_type !== 'missing_hub' ? ` · ${o.consumer.city}` : ''}</span>
    </div>
  );
  if (o.pathway_type === 'via_hub') {
    return (
      <div className="path">
        {src}
        <div className="path-edge"><span>{fmt(l1.km)} km</span></div>
        <div className="path-node hub" style={{ textAlign: 'center' }}><b>{o.hub.name}</b><span>{o.processing.label}</span></div>
        <div className="path-edge"><span>{fmt(l2.km)} km</span></div>
        {dst}
      </div>
    );
  }
  if (o.pathway_type === 'missing_hub') {
    return (
      <div className="path">
        {src}
        <div className="path-edge dashed"><span>{fmt(l1.km)} km</span></div>
        <div className="path-node missing" style={{ textAlign: 'center' }}><b>Proposed hub · {o.proposed_hub.label.split(',')[0]}</b><span>{o.proposed_hub.step_label}</span></div>
        <div className="path-edge dashed"><span>~{fmt(l2.km)} km avg</span></div>
        {dst}
      </div>
    );
  }
  return (
    <div className="path">
      {src}
      <div className="path-edge"><span>{fmt(o.road_km)} km</span></div>
      {dst}
    </div>
  );
}

function Waterfall({ rows, total, format, label }) {
  const max = Math.max(1, ...rows.filter((r) => r.value > 0).map((r) => r.value));
  let running = 0;
  return (
    <div className="waterfall" role="table" aria-label={label}>
      {rows.map((r) => {
        const start = Math.max(0, r.value >= 0 ? running : running + r.value);
        const width = Math.min(Math.abs(r.value), Math.max(0, max - start));
        running += r.value;
        return (
          <div className="wf-row" role="row" key={r.label}>
            <span role="cell">{r.label}</span>
            <span className="wf-track" role="cell" aria-hidden="true">
              <span className={`wf-bar ${r.value >= 0 ? 'plus' : 'minus'}`} style={{ left: `${(start / max) * 100}%`, width: `max(2px, ${(width / max) * 100}%)` }} />
            </span>
            <span className="num" role="cell">{r.value >= 0 ? '+' : '−'}{format(Math.abs(r.value))}</span>
          </div>
        );
      })}
      <div className="wf-row total" role="row">
        <span role="cell">Net</span>
        <span className="wf-track" role="cell" aria-hidden="true">
          <span className="wf-bar net" style={{ left: 0, width: `${Math.max(0, (total / max) * 100)}%` }} />
        </span>
        <span className="num" role="cell">{total < 0 ? '−' : ''}{format(Math.abs(total))}</span>
      </div>
    </div>
  );
}

function Timing({ volume }) {
  const sMax = Math.max(...volume.supply_months, 0.01);
  const dMax = Math.max(...volume.demand_months, 0.01);
  const row = (label, arr, max, color) => (
    <>
      <span className="lbl">{label}</span>
      {arr.map((v, i) => (
        <span key={i} className="cell" title={`${label} ${MONTHS[i]}: ${Math.round((v / max) * 100)}%`}
          style={{ background: `color-mix(in srgb, ${color} ${Math.round(15 + 85 * (v / max))}%, var(--line))` }} />
      ))}
    </>
  );
  return (
    <div className="timeline" aria-label="Monthly supply and demand">
      {row('Supply', volume.supply_months, sMax, 'var(--producer)')}
      {row('Demand', volume.demand_months, dMax, 'var(--consumer)')}
      <span />
      {MONTHS.map((m, i) => <span key={i} className="m">{m}</span>)}
    </div>
  );
}

export default function OpportunityDetail({ o, outreachRec, onStartOutreach, busy }) {
  if (!o) {
    return <section className="panel"><p className="empty">Select an opportunity to see its full assessment.</p></section>;
  }
  const { impact, economics: e, volume, dimensions, weights } = o;

  return (
    <article className="panel" aria-label={`Opportunity: ${o.title}`}>
      <div className="panel-head">
        <span style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="panel-title">{o.title}</span>
          <CategoryTag category={o.category} />
          <span className="tag">{PATHWAY_LABEL[o.pathway_type]}</span>
          {o.novel_use && <span className="tag cat-hidden">Non-obvious use</span>}
          {o.carbon_negative && <span className="tag co2neg">Carbon-negative</span>}
        </span>
        <span className="btn-row">
          {outreachRec && <StatusTag status={outreachRec.status} />}
          {o.pathway_type !== 'missing_hub' && (
            <button type="button" className="btn btn-sm btn-primary" disabled={busy} onClick={() => onStartOutreach?.(o)}>
              {outreachRec ? 'Open outreach' : 'Start outreach'}
            </button>
          )}
        </span>
      </div>

      <div className="detail-grid">
        <section className="full">
          <PathDiagram o={o} />
          {o.pathway_type === 'missing_hub' && (
            <p className="notice info" style={{ marginTop: 12 }}>
              Hidden opportunity: {fmt(o.proposed_hub.catchment_demand_tpm)} t/month of demand exists nearby, but nothing can do
              “{o.proposed_hub.step_label.toLowerCase()}” within range. A hub near {o.proposed_hub.label} would unlock it:
              {' '}{o.consumers.map((c) => c.name).join(', ')}.
            </p>
          )}
        </section>

        <section>
          <span className="eyebrow">Opportunity score</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 2 }}>
            <span className="big">{o.score}<span className="big-unit">/ 100</span></span>
            <span className="tag">{o.feasibility}</span>
            {o.feedback_multiplier !== 1 && <span className="tag" title="Adjusted by past industry responses">×{o.feedback_multiplier} feedback</span>}
          </div>
          <div className="dims" role="table" aria-label="Score by dimension">
            <div className="dim-row" role="row" style={{ color: 'var(--muted)', fontSize: 11 }}>
              <span role="columnheader">Dimension</span><span /><span role="columnheader" className="num" style={{ color: 'var(--muted)' }}>Score</span><span role="columnheader" className="w">Wt</span>
            </div>
            {Object.keys(DIM_LABEL).map((k) => (
              <div className="dim-row" role="row" key={k}>
                <span role="cell">{DIM_LABEL[k]}</span>
                <span className="dim-bar" aria-hidden="true"><span style={{ width: `${dimensions[k]}%` }} /></span>
                <span className="num" role="cell">{dimensions[k]}</span>
                <span className="w num" role="cell">{Math.round(weights[k])}%</span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <span className="eyebrow">Why — feasibility checks</span>
          <ul className="checks">
            {o.reasons.map((r) => (
              <li key={r.dimension + r.text}>
                <span className={`ic-${r.status}`} aria-label={r.status}>{ICON[r.status]}</span>
                <span className="d">{r.dimension}</span>
                <span>{r.text}</span>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <span className="eyebrow">Environmental impact · tCO₂e / year</span>
          <div style={{ marginTop: 2 }}>
            <span className="big">{fmt(impact.net_tco2e_per_year)}</span><span className="big-unit">net</span>
          </div>
          <Waterfall
            label="Carbon balance"
            rows={[
              { label: 'Virgin avoided', value: impact.e_virgin_avoided },
              { label: 'Processing', value: -impact.e_processing },
              { label: 'Transport', value: -impact.e_transport },
            ]}
            total={impact.net_tco2e_per_year}
            format={(v) => fmt(v)}
          />
          <div className="stat-row">
            <div className="stat"><b>{fmt(impact.waste_diverted_t)} t</b><span>waste diverted / yr</span></div>
            <div className="stat"><b>{fmt(impact.virgin_replaced_t)} t</b><span>{impact.virgin_input.toLowerCase()} replaced</span></div>
            <div className="stat"><b>{fmt(impact.carbon_breakeven_km)} km</b><span>carbon break-even</span></div>
          </div>
        </section>

        <section>
          <span className="eyebrow">Economic opportunity · per year</span>
          <div style={{ marginTop: 2 }}>
            <span className="big">{inr(e.net_inr_per_year)}</span><span className="big-unit">net · {inr(e.net_inr_per_t)}/t</span>
          </div>
          <Waterfall
            label="Business case"
            rows={[
              { label: 'Virgin savings', value: e.virgin_savings_inr },
              { label: 'Disposal saved', value: e.disposal_savings_inr },
              ...(e.carbon_value_inr ? [{ label: 'Carbon value', value: e.carbon_value_inr }] : []),
              { label: 'Transport', value: -e.transport_cost_inr },
              { label: 'Processing', value: -e.processing_cost_inr },
            ]}
            total={e.net_inr_per_year}
            format={(v) => inr(v).replace('₹', '')}
          />
          <p className="caveat" style={{ padding: '8px 0 0' }}>
            Supplier revenue at an indicative ₹{fmt(e.byproduct_price_inr_per_t)}/t: {inr(e.byproduct_revenue_inr)}/yr. This is a transfer between the parties, so it's not added to the net.
          </p>
        </section>

        <section>
          <span className="eyebrow">Quantity & timing</span>
          <div className="stat-row" style={{ marginTop: 6 }}>
            <div className="stat"><b>{fmt(volume.supply_tpm)} t/mo</b><span>supply</span></div>
            <div className="stat"><b>{fmt(volume.demand_tpm)} t/mo</b><span>demand</span></div>
            <div className="stat"><b>{fmt(volume.exchanged_tpy / 12)} t/mo</b><span>exchanged (avg)</span></div>
          </div>
          <Timing volume={volume} />
        </section>

        <section>
          <span className="eyebrow">Processing & specifications</span>
          <p style={{ marginTop: 6, fontSize: 13 }}>{o.use}</p>
          <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            {o.processing.label ? `${o.processing.label} · ${PATHWAY_LABEL[o.pathway_type].toLowerCase()}` : 'No treatment needed'}
          </p>
          <div className="standards">{o.standards.map((s) => <span className="tag" key={s}>{s}</span>)}</div>
        </section>

        <section className="full">
          <span className="eyebrow">Policy / scheme pathways</span>
          {o.pathways.length === 0 ? (
            <p className="muted" style={{ marginTop: 6 }}>No specific policy instrument mapped for this pair.</p>
          ) : (
            o.pathways.map((p) => (
              <div className="pathway" key={p.id}>
                <div className="pathway-head">
                  <span className="pathway-name">{p.name}</span>
                  <span className="btn-row"><span className="tag">{p.type}</span><span className="tag st-more_info">Verify eligibility</span></span>
                </div>
                <div className="pathway-auth">{p.authority} · {p.year} · matched on {p.matched_on.join(', ')}</div>
                <p>{p.relevance}</p>
                <ul>{p.verify.map((v) => <li key={v}>{v}</li>)}</ul>
                <a href={p.portal} target="_blank" rel="noreferrer">Official portal ↗</a>
              </div>
            ))
          )}
        </section>
      </div>
      <p className="caveat">
        {CATEGORY_LABEL[o.category]} pathway · {o.distance_source === 'live-osrm' ? 'live road distance (OSRM)' : 'estimated road distance'}.
        This is a screening estimate from indicative factors and illustrative volumes. Validate with lab tests, LCA data and logistics quotes.
      </p>
    </article>
  );
}
