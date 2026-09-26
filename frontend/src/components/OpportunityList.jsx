import { useState } from 'react';
import { CATEGORY_LABEL, PATHWAY_LABEL, STATUS_LABEL, fmt } from '../format';

export function CategoryTag({ category }) {
  return <span className={`tag cat-${category}`}>{CATEGORY_LABEL[category]}</span>;
}

export function StatusTag({ status }) {
  if (!status) return null;
  return <span className={`tag st-${status}`}>{STATUS_LABEL[status]}</span>;
}

export default function OpportunityList({ opportunities, selectedId, onSelect, statusByOpp = {}, title = 'Opportunities', meta, showProducer = false, maxHeight }) {
  const [filter, setFilter] = useState('all');
  const counts = opportunities.reduce((acc, o) => ({ ...acc, [o.category]: (acc[o.category] || 0) + 1 }), {});
  const shown = filter === 'all' ? opportunities : opportunities.filter((o) => o.category === filter);

  return (
    <section className="panel" aria-label={title}>
      <div className="panel-head">
        <span className="panel-title">{title}</span>
        {meta && <span className="panel-meta">{meta}</span>}
      </div>
      <div className="panel-body" style={{ paddingBottom: 10 }}>
        <div className="chips" role="group" aria-label="Filter by pathway">
          <button type="button" className="chip" aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>All {opportunities.length}</button>
          {['direct', 'multi_step', 'hidden'].map((c) => (
            <button type="button" key={c} className="chip" aria-pressed={filter === c} onClick={() => setFilter(c)}>
              {CATEGORY_LABEL[c]} {counts[c] || 0}
            </button>
          ))}
        </div>
      </div>
      {shown.length === 0 ? (
        <p className="empty">No opportunities in this category.</p>
      ) : (
        <ul className="opp-list" key={filter} role="listbox" aria-label={title} style={maxHeight ? { maxHeight, overflow: 'auto' } : undefined}>
          {shown.map((o, i) => (
            <li key={o.id} style={{ '--i': Math.min(i, 14) }}>
              <button type="button" className="opp" role="option" aria-selected={o.id === selectedId} onClick={() => onSelect(o.id)}>
                <span className="score-ring" style={{ '--p': o.score }} aria-label={`Score ${o.score}`}><b>{o.score}</b></span>
                <span style={{ minWidth: 0 }}>
                  <span className="opp-name">{o.title}</span>
                  <span className="opp-sub">
                    {showProducer && o.origin ? `${o.origin.name} · ` : ''}{o.material_name} → {o.consumer_sector} · {PATHWAY_LABEL[o.pathway_type]}
                  </span>
                </span>
                <span className="opp-right">
                  <span className="num">{fmt(o.road_km)} km</span>
                  <span style={{ display: 'flex', gap: 4 }}>
                    {statusByOpp[o.id] ? <StatusTag status={statusByOpp[o.id]} /> : <CategoryTag category={o.category} />}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
