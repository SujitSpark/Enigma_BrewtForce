import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { CATEGORY_LABEL, fmt, tonnes, withOrigin } from '../format';
import OpportunityDetail from '../components/OpportunityDetail';

const W = 1200;
const X = { src: 250, hub: 610, dst: 910 };
const ROW = 26;
const TOP = 44;
const trunc = (s, n = 36) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
const CAT_VAR = { direct: 'var(--consumer)', multi_step: 'var(--hub)', hidden: 'var(--hidden)' };

function curve(x1, y1, x2, y2) {
  const mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

export default function Network({ meta, outreachByOpp, onStartOutreach, busy, refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [mat, setMat] = useState('all');
  const [hover, setHover] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => { api.network({}, 300).then(setData).catch((e) => setError(e.message)); }, [refreshKey]);

  const opps = useMemo(() => (data?.opportunities ?? []).map((o) => withOrigin(o))
    .filter((o) => mat === 'all' || o.material_id === mat), [data, mat]);

  const graph = useMemo(() => {
    const cols = { src: new Map(), hub: new Map(), dst: new Map() };
    const add = (col, key, node) => {
      const n = cols[col].get(key) || { ...node, key, col, volume: 0 };
      n.volume += node.volume;
      cols[col].set(key, n);
    };
    const links = [];
    opps.forEach((o) => {
      const v = o.volume.exchanged_tpy;
      const s = `src:${o.producer.id}`;
      add('src', s, { label: o.producer.name, sub: o.producer.sector, volume: v });
      const dsts = o.pathway_type === 'missing_hub' ? o.consumers : [o.consumer];
      dsts.forEach((c) => add('dst', `dst:${c.id}`, { label: c.name, sub: c.sector, volume: v / dsts.length }));
      if (o.pathway_type === 'via_hub' || o.pathway_type === 'missing_hub') {
        const h = o.hub ? `hub:${o.hub.id}` : `ph:${o.id}`;
        add('hub', h, { label: o.hub ? o.hub.name : `Proposed · near ${o.proposed_hub.label.split(',')[0]}`, sub: o.processing.label, volume: v, proposed: !o.hub });
        links.push({ id: o.id, from: s, to: h, v, cat: o.category, dashed: !o.hub });
        dsts.forEach((c) => links.push({ id: o.id, from: h, to: `dst:${c.id}`, v: v / dsts.length, cat: o.category, dashed: !o.hub }));
      } else {
        links.push({ id: o.id, from: s, to: `dst:${o.consumer.id}`, v, cat: o.category });
      }
    });
    const pos = {};
    const counts = {};
    Object.entries(cols).forEach(([col, m]) => {
      const nodes = [...m.values()].sort((a, b) => (col === 'dst' ? a.sub.localeCompare(b.sub) || b.volume - a.volume : b.volume - a.volume));
      counts[col] = nodes.length;
      nodes.forEach((n, i) => { pos[n.key] = { ...n, x: X[col], i }; });
    });
    const maxN = Math.max(1, ...Object.values(counts));
    const H = TOP + maxN * ROW + 20;
    Object.values(pos).forEach((p) => {
      const n = counts[p.col];
      p.y = TOP + ((p.i + 0.5) * (H - TOP - 20)) / n;
    });
    const vmax = Math.max(1, ...links.map((l) => l.v));
    return { pos, links, H, vmax, counts };
  }, [opps]);

  const touches = (l) => hover && (l.from === hover || l.to === hover);
  const current = opps.find((o) => o.id === selected);

  return (
    <div className="page">
      <section className="panel">
        <div className="panel-head">
          <span className="panel-title">Industrial ecosystem</span>
          <span className="legend">
            {Object.entries(CATEGORY_LABEL).map(([k, v]) => <span key={k}><i className="dot" style={{ background: CAT_VAR[k] }} />{v}</span>)}
            <span className="muted">link width = tonnes/yr</span>
          </span>
        </div>
        <div className="panel-body btn-row">
          <div className="chips">
            <button type="button" className="chip" aria-pressed={mat === 'all'} onClick={() => setMat('all')}>All materials</button>
            {meta.materials.map((m) => <button type="button" key={m.id} className="chip" aria-pressed={mat === m.id} onClick={() => setMat(m.id)}>{m.name}</button>)}
          </div>
        </div>
        {error && <p className="notice" style={{ margin: '0 16px 16px' }}>{error}</p>}
        {!data && !error && <div className="panel-body"><div className="skeleton" style={{ height: 300 }} /></div>}
        {data && (
          <div style={{ overflowX: 'auto' }}>
            <svg className="graph" viewBox={`0 0 ${W} ${graph.H}`} style={{ minWidth: 900 }} role="img"
              aria-label={`Ecosystem graph: ${graph.counts.src} sources, ${graph.counts.hub} processing hubs, ${graph.counts.dst} consumers`}>
              <text className="col-title" x={X.src} y={20} textAnchor="end">Sources · {graph.counts.src}</text>
              <text className="col-title" x={X.hub} y={20} textAnchor="middle">Processing hubs · {graph.counts.hub}</text>
              <text className="col-title" x={X.dst} y={20}>Consumers · {graph.counts.dst}</text>
              <g>
                {graph.links.map((l, i) => {
                  const a = graph.pos[l.from];
                  const b = graph.pos[l.to];
                  const cls = hover ? (touches(l) ? 'on' : 'off') : selected ? (l.id === selected ? 'on' : 'off') : '';
                  return (
                    <path key={i} className={`link ${cls}`} d={curve(a.x + 5, a.y, b.x - 5, b.y)}
                      strokeWidth={1.5 + 7 * Math.sqrt(l.v / graph.vmax)}
                      strokeDasharray={l.dashed ? '6 5' : undefined} onClick={() => setSelected(l.id)} style={{ cursor: 'pointer', stroke: CAT_VAR[l.cat] }}>
                      <title>{`${a.label} → ${b.label}: ${tonnes(l.v)}/yr (${CATEGORY_LABEL[l.cat]})`}</title>
                    </path>
                  );
                })}
              </g>
              {Object.values(graph.pos).map((p) => {
                const fill = p.col === 'src' ? 'var(--producer)' : p.col === 'dst' ? 'var(--consumer)' : p.proposed ? 'var(--surface)' : 'var(--hub)';
                return (
                  <g key={p.key} className="node" onMouseEnter={() => setHover(p.key)} onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(p.key)} onBlur={() => setHover(null)} tabIndex={0}>
                    <rect x={p.x - 5} y={p.y - 8} width={10} height={16} rx={3}
                      style={{ fill, stroke: p.proposed ? 'var(--hidden)' : 'none' }} strokeDasharray={p.proposed ? '3 2' : undefined} strokeWidth={1.5} />
                    <text x={p.col === 'src' ? p.x - 12 : p.x + 12} y={p.y + 4} textAnchor={p.col === 'src' ? 'end' : 'start'}
                      style={{ fill: hover === p.key ? 'var(--ink)' : undefined, fontWeight: hover === p.key ? 600 : 400 }}>
                      {trunc(p.label, p.col === 'hub' ? 30 : 38)}
                    </text>
                    <title>{`${p.label} · ${p.sub} · ${tonnes(p.volume)}/yr`}</title>
                  </g>
                );
              })}
            </svg>
          </div>
        )}
        <p className="caveat">Hover a node to trace its flows; click a flow to open the opportunity. Showing the top {fmt(opps.length)} opportunities. Volumes are illustrative.</p>
      </section>
      {current && (
        <OpportunityDetail o={current} outreachRec={outreachByOpp[current.id]} busy={busy}
          onStartOutreach={(o) => onStartOutreach(o, { company: o.origin.name, location_label: o.origin.city }, o.material_name)} />
      )}
    </div>
  );
}
