import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { PATHWAY_LABEL, STATUS_LABEL, inr } from '../format';
import { StatusTag } from '../components/OpportunityList';
import { Counter } from '../components/Motion';

function Editor({ rec, smtp, onSaved }) {
  const [form, setForm] = useState({ recipient_email: '', subject: '', body: '', response_note: '' });
  const [msg, setMsg] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setForm({ recipient_email: rec.recipient_email || '', subject: rec.subject, body: rec.body, response_note: rec.response_note || '' });
    setMsg(null);
  }, [rec.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = form.recipient_email !== (rec.recipient_email || '') || form.subject !== rec.subject || form.body !== rec.body ||
    form.response_note !== (rec.response_note || '');

  const save = async (extra = {}) => {
    try {
      const r = await api.updateOutreach(rec.id, { ...form, ...extra });
      onSaved(r);
      setMsg(null);
      return r;
    } catch (e) {
      setMsg({ kind: 'bad', text: e.message });
      return null;
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(`Subject: ${form.subject}\n\n${form.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const send = async () => {
    if (dirty && !(await save())) return;
    try {
      onSaved(await api.sendOutreach(rec.id));
      setMsg({ kind: 'good', text: `Sent to ${form.recipient_email}` });
    } catch (e) {
      setMsg({ kind: 'info', text: e.message });
    }
  };

  const mailto = `mailto:${encodeURIComponent(form.recipient_email)}?subject=${encodeURIComponent(form.subject)}&body=${encodeURIComponent(form.body)}`;

  return (
    <section className="panel" aria-label="Outreach email">
      <div className="panel-head">
        <span className="panel-title">{rec.consumer_name}</span>
        <span className="btn-row"><span className="tag">{PATHWAY_LABEL[rec.pathway_type] || rec.pathway_type}</span><StatusTag status={rec.status} /></span>
      </div>
      <div className="panel-body" style={{ display: 'grid', gap: 10 }}>
        <div className="stat-row" style={{ marginTop: 0 }}>
          <div className="stat"><b>{rec.score}</b><span>score</span></div>
          <div className="stat"><b>{Math.round(rec.net_tco2e_per_year).toLocaleString('en-IN')}</b><span>tCO₂e/yr</span></div>
          <div className="stat"><b>{inr(rec.net_inr_per_year)}</b><span>per year</span></div>
          <div className="stat"><b>{rec.material_name}</b><span>from {rec.supplier_name || rec.supplier_location}</span></div>
        </div>
        <div className="field"><label htmlFor="o-to">Recipient email</label>
          <input id="o-to" type="email" className="input" value={form.recipient_email} placeholder="procurement@buyer.com"
            onChange={(e) => setForm({ ...form, recipient_email: e.target.value })} /></div>
        <div className="field"><label htmlFor="o-subj">Subject</label>
          <input id="o-subj" className="input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></div>
        <div className="field"><label htmlFor="o-body">Message</label>
          <textarea id="o-body" className="email" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></div>
        <div className="btn-row">
          <button type="button" className="btn btn-sm" disabled={!dirty} onClick={() => save()}>Save</button>
          <button type="button" className="btn btn-sm" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
          <a className="btn btn-sm" href={mailto} onClick={() => rec.status === 'draft' && save({ status: 'sent' })}>Open in mail app</a>
          <button type="button" className="btn btn-sm btn-primary" onClick={send} disabled={!form.recipient_email}
            title={smtp ? 'Send via configured SMTP' : 'SMTP not configured on the server'}>Send{smtp ? '' : ' (SMTP)'}</button>
          {rec.status === 'draft' && <button type="button" className="btn btn-sm" onClick={() => save({ status: 'sent' })}>Mark as sent</button>}
        </div>
        {msg && <p className={`notice ${msg.kind}`}>{msg.text}</p>}
      </div>

      <div className="panel-body" style={{ borderTop: '1px solid var(--line)', display: 'grid', gap: 10 }}>
        <span className="eyebrow">Industry response</span>
        <p className="muted" style={{ fontSize: 12 }}>
          The recipient clicks one of these links in the email, and the answer lands here and re-weights future recommendations.
          You can also log a reply received by phone.
        </p>
        <div className="btn-row">
          {Object.entries(rec.response_links).map(([k, url]) => (
            <a key={k} className={`tag st-${k}`} href={url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', padding: '3px 10px' }}>
              {STATUS_LABEL[k]} link ↗
            </a>
          ))}
        </div>
        <div className="field"><label htmlFor="o-note">Note</label>
          <input id="o-note" className="input" value={form.response_note} onChange={(e) => setForm({ ...form, response_note: e.target.value })} placeholder="e.g. wants a 5 t trial lot in March" /></div>
        <div className="btn-row">
          <span className="panel-meta">Log response:</span>
          {['interested', 'more_info', 'not_feasible'].map((s) => (
            <button type="button" key={s} className="btn btn-sm" aria-pressed={rec.status === s} onClick={() => save({ status: s })}>{STATUS_LABEL[s]}</button>
          ))}
          {rec.status !== 'draft' && <button type="button" className="btn btn-sm" onClick={() => save({ status: 'draft' })}>Reset</button>}
        </div>
        {rec.responded_at && <p className="panel-meta">Responded {new Date(rec.responded_at).toLocaleString()}</p>}
      </div>
    </section>
  );
}

const RESPONSES = ['interested', 'more_info', 'not_feasible'];
const OUTCOME = {
  interested: { label: 'Interested', icon: '✓', color: 'var(--ok)' },
  more_info: { label: 'Needs info', icon: '?', color: 'var(--warn)' },
  not_feasible: { label: 'Not feasible', icon: '×', color: 'var(--bad)' },
  sent: { label: 'Awaiting reply', icon: '…', color: 'color-mix(in srgb, var(--moonstone) 45%, var(--line))' },
};

function daysAgo(iso) {
  const d = (Date.now() - new Date(iso).getTime()) / 86400000;
  if (d < 1 / 24) return 'just now';
  if (d < 1) return `${Math.round(d * 24)}h ago`;
  return `${Math.round(d)}d ago`;
}

function stats(records) {
  const sent = records.filter((r) => r.status !== 'draft');
  const replied = records.filter((r) => RESPONSES.includes(r.status));
  const by = (s) => records.filter((r) => r.status === s).length;
  const waits = replied.filter((r) => r.sent_at && r.responded_at)
    .map((r) => (new Date(r.responded_at) - new Date(r.sent_at)) / 86400000);
  const interested = records.filter((r) => r.status === 'interested');
  return {
    total: records.length,
    drafts: by('draft'),
    sent: sent.length,
    awaiting: by('sent'),
    replied: replied.length,
    interested: by('interested'),
    moreInfo: by('more_info'),
    notFeasible: by('not_feasible'),
    replyRate: sent.length ? replied.length / sent.length : 0,
    avgReplyDays: waits.length ? waits.reduce((a, b) => a + b, 0) / waits.length : null,
    pipelineInr: interested.reduce((a, r) => a + (r.net_inr_per_year || 0), 0),
    pipelineCo2: interested.reduce((a, r) => a + Math.max(0, r.net_tco2e_per_year || 0), 0),
  };
}

function Funnel({ s }) {
  const stages = [
    { label: 'Emails sent', value: s.sent, sub: `${s.drafts} still in draft`, pct: s.total ? s.sent / s.total : 0 },
    { label: 'Replies', value: s.replied, sub: `${Math.round(s.replyRate * 100)}% reply rate`, pct: s.sent ? s.replied / s.sent : 0 },
    { label: 'Interested', value: s.interested, sub: s.replied ? `${Math.round((s.interested / s.replied) * 100)}% of replies` : '—', pct: s.replied ? s.interested / s.replied : 0 },
  ];
  return (
    <div className="or-funnel" role="list" aria-label="Outreach funnel">
      {stages.map((st, i) => (
        <div key={st.label} className="or-stage" role="listitem" style={{ '--i': i }}>
          <span className="or-stage-label">{st.label}</span>
          <span className="or-stage-num"><Counter value={st.value} /></span>
          <span className="or-stage-bar" aria-hidden="true"><span style={{ '--w': `${Math.max(4, st.pct * 100)}%` }} /></span>
          <span className="or-stage-sub">{st.sub}</span>
          {i < stages.length - 1 && <span className="or-arrow" aria-hidden="true">→</span>}
        </div>
      ))}
    </div>
  );
}

function CompletionRing({ s }) {
  const R = 70;
  const C = 2 * Math.PI * R;
  const segs = [
    ['interested', s.interested], ['more_info', s.moreInfo], ['not_feasible', s.notFeasible], ['sent', s.awaiting],
  ];
  const total = Math.max(1, s.sent);
  let offset = 0;
  return (
    <div className="or-ring-wrap">
      <svg viewBox="0 0 180 180" className="or-ring" role="img"
        aria-label={`${Math.round(s.replyRate * 100)}% of sent emails have a reply: ${s.interested} interested, ${s.moreInfo} need info, ${s.notFeasible} not feasible, ${s.awaiting} awaiting`}>
        <circle cx="90" cy="90" r={R} className="or-ring-track" />
        {segs.map(([k, n], i) => {
          const len = (n / total) * C;
          const el = (
            <circle key={k} cx="90" cy="90" r={R} className="or-ring-seg"
              style={{ stroke: OUTCOME[k].color, strokeDasharray: `${Math.max(0, len - 3)} ${C}`, strokeDashoffset: -offset, animationDelay: `${300 + i * 180}ms` }} />
          );
          offset += len;
          return el;
        })}
      </svg>
      <div className="or-ring-center">
        <span className="or-ring-pct"><Counter value={Math.round(s.replyRate * 100)} format={(v) => `${Math.round(v)}%`} /></span>
        <span className="or-ring-cap">completion</span>
      </div>
    </div>
  );
}

function Outcomes({ s }) {
  const rows = [['interested', s.interested], ['more_info', s.moreInfo], ['not_feasible', s.notFeasible], ['sent', s.awaiting]];
  const total = Math.max(1, s.sent);
  return (
    <div className="or-outcomes">
      <div className="or-stack" aria-hidden="true">
        {rows.map(([k, n], i) => n > 0 && (
          <span key={k} style={{ '--w': `${(n / total) * 100}%`, background: OUTCOME[k].color, animationDelay: `${200 + i * 120}ms` }} />
        ))}
      </div>
      <ul className="or-legend">
        {rows.map(([k, n]) => (
          <li key={k}>
            <span className="or-dot" style={{ background: OUTCOME[k].color }}>{OUTCOME[k].icon}</span>
            <span>{OUTCOME[k].label}</span>
            <b className="num">{n}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Activity({ records }) {
  const [tip, setTip] = useState(null);
  const days = [...Array(14)].map((_, i) => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - (13 - i));
    return d;
  });
  const key = (iso) => { const d = new Date(iso); d.setHours(0, 0, 0, 0); return d.getTime(); };
  const data = days.map((d) => ({
    d,
    sent: records.filter((r) => r.sent_at && key(r.sent_at) === d.getTime()).length,
    replies: records.filter((r) => r.responded_at && key(r.responded_at) === d.getTime()).length,
  }));
  const max = Math.max(1, ...data.map((x) => Math.max(x.sent, x.replies)));
  return (
    <div className="or-activity" onMouseLeave={() => setTip(null)}>
      <div className="or-bars" role="table" aria-label="Emails sent and replies received per day, last 14 days">
        {data.map((x, i) => {
          const label = x.d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
          return (
            <div key={i} className="or-day" role="row" style={{ '--i': i }}
              onMouseMove={(e) => setTip({ x: e.clientX + 12, y: e.clientY + 12, text: `${label}: ${x.sent} sent · ${x.replies} replies` })}>
              <span className="or-col sent" role="cell" aria-label={`${label} sent ${x.sent}`} style={{ '--h': `${(x.sent / max) * 100}%` }} />
              <span className="or-col replies" role="cell" aria-label={`${label} replies ${x.replies}`} style={{ '--h': `${(x.replies / max) * 100}%` }} />
              <span className="or-day-lbl">{i % 2 === 1 ? label : ''}</span>
            </div>
          );
        })}
      </div>
      {tip && <div className="chart-tip" style={{ left: tip.x, top: tip.y }}>{tip.text}</div>}
    </div>
  );
}

function ReplyFeed({ records, onSelect }) {
  const replies = records.filter((r) => RESPONSES.includes(r.status))
    .sort((a, b) => new Date(b.responded_at) - new Date(a.responded_at)).slice(0, 4);
  if (!replies.length) return <p className="empty">No replies yet.</p>;
  return (
    <ul className="or-feed">
      {replies.map((r, i) => (
        <li key={r.id} style={{ '--i': i }}>
          <button type="button" onClick={() => onSelect(r.id)}>
            <span className="or-dot" style={{ background: OUTCOME[r.status].color }}>{OUTCOME[r.status].icon}</span>
            <span className="or-feed-main">
              <b>{r.consumer_name}</b>
              <span>{r.response_note || OUTCOME[r.status].label} · {r.material_name}</span>
            </span>
            <span className="or-feed-time">{daysAgo(r.responded_at)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function Outreach({ records, selectedId, onSelect, onSaved, onReload, smtp }) {
  const [busy, setBusy] = useState(false);
  const s = useMemo(() => stats(records), [records]);
  const current = records.find((r) => r.id === selectedId) || records[0];
  const demoCount = records.filter((r) => r.demo).length;

  const demo = async (action) => {
    setBusy(true);
    try {
      await (action === 'seed' ? api.seedDemoOutreach() : api.clearDemoOutreach());
      await onReload();
    } finally {
      setBusy(false);
    }
  };

  if (records.length === 0) {
    return (
      <div className="page">
        <section className="panel or-empty">
          <h2 className="page-title" style={{ fontSize: 48 }}>No outreach <em>yet.</em></h2>
          <p className="muted">Open any opportunity and choose “Start outreach”, or load demo activity to see the full pipeline.</p>
          <div className="btn-row" style={{ justifyContent: 'center' }}>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => demo('seed')}>{busy ? 'Loading…' : 'Load demo activity'}</button>
            <a className="btn" href="#/opportunities">Browse opportunities</a>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      {demoCount > 0 && (
        <p className="or-demo">
          <span className="tag st-more_info">Demo data</span>
          {demoCount} of {records.length} contacts are simulated activity for presentation, built from real engine opportunities.
          <span className="btn-row" style={{ marginLeft: 'auto' }}>
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => demo('seed')}>Reload demo</button>
            <button type="button" className="btn btn-sm" disabled={busy} onClick={() => demo('clear')}>Clear demo</button>
          </span>
        </p>
      )}

      <section className="panel or-hero">
        <Funnel s={s} />
        <CompletionRing s={s} />
      </section>

      <div className="or-strip">
        <div><span className="kpi-label">Avg. time to reply</span><b><Counter value={s.avgReplyDays ?? 0} format={(v) => `${v.toFixed(1)} days`} /></b></div>
        <div><span className="kpi-label">Awaiting reply</span><b><Counter value={s.awaiting} /></b></div>
        <div><span className="kpi-label">Value in interested deals</span><b><Counter value={s.pipelineInr} format={inr} /></b></div>
        <div><span className="kpi-label">CO₂e in interested deals</span><b><Counter value={s.pipelineCo2} format={(v) => `${Math.round(v).toLocaleString('en-IN')} t/yr`} /></b></div>
      </div>

      <div className="grid-cc" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.2fr) minmax(0, 1fr)', alignItems: 'stretch' }}>
        <section className="panel">
          <div className="panel-head"><span className="panel-title">Where replies landed</span><span className="panel-meta">of {s.sent} sent</span></div>
          <div className="panel-body"><Outcomes s={s} /></div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <span className="panel-title">Activity · last 14 days</span>
            <span className="legend">
              <span><i className="dot" style={{ background: 'var(--consumer)' }} />Sent</span>
              <span><i className="dot" style={{ background: 'var(--producer)' }} />Replies</span>
            </span>
          </div>
          <div className="panel-body"><Activity records={records} /></div>
        </section>
        <section className="panel">
          <div className="panel-head"><span className="panel-title">Latest replies</span><span className="panel-meta">live</span></div>
          <ReplyFeed records={records} onSelect={onSelect} />
        </section>
      </div>

      <div className="grid-cc" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.1fr)' }}>
        <section className="panel">
          <div className="panel-head"><span className="panel-title">Tracker</span><span className="panel-meta">{records.length} contacts</span></div>
          <div className="table-scroll" style={{ maxHeight: 620 }}>
            <table className="table">
              <thead><tr><th>Company</th><th>Opportunity</th><th className="r">Score</th><th>Status</th></tr></thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} aria-selected={current?.id === r.id} onClick={() => onSelect(r.id)}>
                    <td className="clip"><div style={{ fontWeight: 500 }}>{r.consumer_name}</div><div className="muted" style={{ fontSize: 12 }}>{daysAgo(r.updated_at)}</div></td>
                    <td className="clip">{r.material_name}<div className="muted" style={{ fontSize: 12 }}>from {r.supplier_name || r.supplier_location}</div></td>
                    <td className="r num">{r.score}</td>
                    <td><StatusTag status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        {current && <Editor rec={current} smtp={smtp} onSaved={onSaved} />}
      </div>
    </div>
  );
}
