import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api';
import { EMPTY_INTAKE } from './components/IntakePanel';
import { SplitWords } from './components/Motion';
import Analyse from './pages/Analyse';
import CommandCenter from './pages/CommandCenter';
import Impact from './pages/Impact';
import Landing from './pages/Landing';
import Materials from './pages/Materials';
import Network from './pages/Network';
import Opportunities from './pages/Opportunities';
import Outreach from './pages/Outreach';
import Schemes from './pages/Schemes';

const PAGES = [
  { id: 'command', label: 'Command Center', group: 'Monitor', title: 'Command', accent: 'center.', sub: 'The industrial resource network at a glance: where by-products are, where they could go, and what is already moving.' },
  { id: 'analyse', label: 'Analyse & What-if', group: 'Discover', title: 'Analyse a', accent: 'by-product.', sub: 'Turn an industrial email into ranked direct, multi-step and hidden opportunities, then stress-test the assumptions.' },
  { id: 'opportunities', label: 'Opportunities', group: 'Discover', title: 'Every', accent: 'opportunity.', sub: 'Every exchange the engine found across known plants, with pathway type and outreach status.' },
  { id: 'materials', label: 'Materials', group: 'Discover', title: 'Material', accent: 'atlas.', sub: 'Suppliers, consumers, properties, possible uses and processing hubs for each by-product.' },
  { id: 'network', label: 'Network', group: 'Discover', title: 'The ecosystem,', accent: 'mapped.', sub: 'Sources → processing hubs → consumers. Trace how resources could flow through the ecosystem.' },
  { id: 'impact', label: 'Impact', group: 'Evaluate', title: 'Measured', accent: 'impact.', sub: 'Waste diverted, net CO₂e and economic value, allocated without double counting.' },
  { id: 'schemes', label: 'Schemes', group: 'Evaluate', title: 'Policy', accent: 'pathways.', sub: 'Indian policy instruments linked to the opportunities, with the verification each one needs.' },
  { id: 'outreach', label: 'Outreach', group: 'Engage', title: 'Outreach &', accent: 'responses.', sub: 'Contact potential buyers and track their responses. Every response feeds back into future scores.' },
];

function parseHash() {
  const [, page = 'home', arg] = window.location.hash.split('/');
  return { page: PAGES.some((p) => p.id === page) ? page : 'home', arg };
}

export default function App() {
  const [route, setRoute] = useState(parseHash);
  const [meta, setMeta] = useState(null);
  const [smtp, setSmtp] = useState(false);
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [busyOutreach, setBusyOutreach] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [session, setSession] = useState({ intake: EMPTY_INTAKE, scenario: {}, result: null, baseline: null, selectedId: null });

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const statusSig = useRef(null);
  const loadOutreach = useCallback(() => api.outreach().then((r) => {
    const sig = JSON.stringify(r.map((x) => [x.id, x.status]));
    if (statusSig.current !== null && sig !== statusSig.current) setRefreshKey((k) => k + 1);
    statusSig.current = sig;
    setRecords(r);
  }).catch(() => {}), []);

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(e.message));
    fetch('/api/health').then((r) => r.json()).then((h) => setSmtp(!!h.smtp)).catch(() => {});
    loadOutreach();
    const onFocus = () => loadOutreach();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [loadOutreach]);

  const outreachByOpp = useMemo(() => Object.fromEntries([...records].reverse().map((r) => [r.opportunity_id, r])), [records]);
  const statusByOpp = useMemo(() => Object.fromEntries(Object.entries(outreachByOpp).map(([k, r]) => [k, r.status])), [outreachByOpp]);

  const startOutreach = useCallback(async (o, supplier, materialName, analysisId) => {
    const existing = outreachByOpp[o.id];
    if (existing) {
      window.location.hash = `#/outreach/${existing.id}`;
      return;
    }
    setBusyOutreach(true);
    try {
      const rec = await api.createOutreach({ opportunity: o, supplier, material_name: materialName, analysis_id: analysisId ?? null });
      await loadOutreach();
      window.location.hash = `#/outreach/${rec.id}`;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyOutreach(false);
    }
  }, [outreachByOpp, loadOutreach]);

  const onOutreachSaved = () => { loadOutreach(); };

  if (route.page === 'home') return <Landing />;

  const page = PAGES.find((p) => p.id === route.page);
  const common = { meta, statusByOpp, outreachByOpp, onStartOutreach: startOutreach, busy: busyOutreach, refreshKey };
  const responded = records.filter((r) => ['interested', 'more_info', 'not_feasible'].includes(r.status)).length;

  let groupSeen = '';
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#/home" aria-label="Byloop home">
          <span className="brand-mark" aria-hidden="true" />
          <span><span className="brand-name">Byloop</span><br /><span className="brand-sub">Industrial resource intelligence · India</span></span>
        </a>
        <nav className="nav" aria-label="Sections">
          {PAGES.map((p) => {
            const head = p.group !== groupSeen ? <div className="nav-group">{p.group}</div> : null;
            groupSeen = p.group;
            return (
              <div key={p.id} style={{ display: 'contents' }}>
                {head}
                <a href={`#/${p.id}`} aria-current={route.page === p.id ? 'page' : undefined}>
                  {p.label}
                  {p.id === 'outreach' && records.length > 0 && <span className="count">{responded}/{records.length}</span>}
                </a>
              </div>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          Screening estimates only. Plant locations are real (approx.); volumes are illustrative.
        </div>
      </aside>

      <div className="main">
        <header className="page-head" key={`head-${route.page}`}>
          <div>
            <p className="page-eyebrow word" style={{ animationDelay: '0ms' }}>{page.group} · Byloop</p>
            <h1 className="page-title">
              <SplitWords text={page.title} start={80} />
              <em><SplitWords text={page.accent} start={80 + page.title.split(' ').length * 80} /></em>
            </h1>
            <p className="page-sub word" style={{ animationDelay: '380ms' }}>{page.sub}</p>
          </div>
        </header>
        {error && <div className="page" style={{ paddingBottom: 0 }}><p className="notice" role="alert">{error}</p></div>}
        {!meta ? (
          <div className="page"><div className="skeleton" style={{ height: 60 }} /></div>
        ) : (
          <div className="page-anim" key={`page-${route.page}`}>
            {route.page === 'command' && <CommandCenter {...common} />}
            {route.page === 'analyse' && <Analyse {...common} session={session} setSession={setSession} busyOutreach={busyOutreach} />}
            {route.page === 'opportunities' && <Opportunities {...common} />}
            {route.page === 'materials' && <Materials meta={meta} initial={route.arg} />}
            {route.page === 'network' && <Network {...common} />}
            {route.page === 'impact' && <Impact refreshKey={refreshKey} />}
            {route.page === 'schemes' && <Schemes refreshKey={refreshKey} />}
            {route.page === 'outreach' && (
              <Outreach records={records} selectedId={route.arg ? Number(route.arg) : null} smtp={smtp}
                onSelect={(id) => { window.location.hash = `#/outreach/${id}`; }} onSaved={onOutreachSaved} onReload={loadOutreach} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
