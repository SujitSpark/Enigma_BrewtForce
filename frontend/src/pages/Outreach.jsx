import { useEffect, useState } from 'react';
import { api } from '../api';
import { PATHWAY_LABEL, STATUS_LABEL, inr } from '../format';
import { StatusTag } from '../components/OpportunityList';

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

export default function Outreach({ records, selectedId, onSelect, onSaved, smtp }) {
  const counts = records.reduce((a, r) => ({ ...a, [r.status]: (a[r.status] || 0) + 1 }), {});
  const current = records.find((r) => r.id === selectedId) || records[0];

  return (
    <div className="page">
      <div className="kpis" style={{ gridTemplateColumns: 'repeat(5, minmax(0,1fr))' }}>
        {Object.entries(STATUS_LABEL).map(([k, v]) => (
          <div className="kpi" key={k}><div className="kpi-label">{v}</div><div className="kpi-value">{counts[k] || 0}</div></div>
        ))}
      </div>
      {records.length === 0 ? (
        <section className="panel"><p className="empty">No outreach yet. Open any opportunity and choose “Start outreach”.</p></section>
      ) : (
        <div className="grid-cc" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.1fr)' }}>
          <section className="panel">
            <div className="panel-head"><span className="panel-title">Tracker</span><span className="panel-meta">{records.length} contacts</span></div>
            <div className="table-scroll">
              <table className="table">
                <thead><tr><th>Company</th><th>Opportunity</th><th className="r">Score</th><th>Status</th></tr></thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id} aria-selected={current?.id === r.id} onClick={() => onSelect(r.id)}>
                      <td className="clip"><div style={{ fontWeight: 500 }}>{r.consumer_name}</div><div className="muted" style={{ fontSize: 12 }}>{new Date(r.updated_at).toLocaleDateString()}</div></td>
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
      )}
    </div>
  );
}
