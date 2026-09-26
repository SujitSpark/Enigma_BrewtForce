import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { Counter, SplitWords, reduceMotion, useInView } from '../components/Motion';
import '../landing.css';

const PAIRS = [
  ['fly ash', 'cement'],
  ['steel slag', 'road base'],
  ['foundry sand', 'new moulds'],
  ['phosphogypsum', 'plaster'],
  ['mill scale', 'sinter feed'],
  ['C&D rubble', 'aggregate'],
];

const MARQUEE = ['Fly ash → Portland pozzolana cement', 'Steel slag → Road base', 'GBF slag → Slag cement', 'Foundry sand → Reclaimed moulds',
  'Phosphogypsum → Plaster', 'Red mud → Iron corrective', 'Mill scale → Sinter feed', 'C&D waste → Recycled aggregate'];

const DIMS = [['Material', 95], ['Quantity', 65], ['Geography', 98], ['Processing', 100], ['Timing', 100], ['Environment', 100], ['Economics', 99]];

function Reveal({ as: Tag = 'div', className = '', delay = 0, children, ...rest }) {
  const ref = useRef(null);
  const seen = useInView(ref, 0.15);
  return (
    <Tag ref={ref} className={`rv ${seen ? 'in' : ''} ${className}`} style={{ transitionDelay: `${delay}ms` }} {...rest}>
      {children}
    </Tag>
  );
}

function Rotator() {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (reduceMotion()) return undefined;
    const t = setInterval(() => setI((x) => (x + 1) % PAIRS.length), 2400);
    return () => clearInterval(t);
  }, []);
  const [a, b] = PAIRS[i];
  return (
    <p className="lp-rotator" aria-live="polite">
      One plant's <span key={`a${i}`} className="swap src">{a}</span> is another plant's <span key={`b${i}`} className="swap dst">{b}</span>.
    </p>
  );
}

const PATHS = {
  p1: 'M90,140 C220,120 250,230 400,250',
  p2: 'M110,330 C230,330 270,260 400,250',
  p3: 'M400,250 C520,240 560,130 700,120',
  p4: 'M400,250 C540,260 560,330 700,340',
  p5: 'M110,330 C300,420 520,470 700,480',
  p6: 'M90,470 C220,500 290,440 400,430',
  p7: 'M400,430 C520,420 600,470 700,480',
};

function HeroNetwork() {
  const flows = [
    ['p1', 3.2, 0, 'var(--lp-rust)'], ['p1', 3.2, 1.6, 'var(--lp-rust)'],
    ['p2', 3.6, 0.4, 'var(--lp-rust)'], ['p3', 3, 0.8, 'var(--lp-purple)'], ['p3', 3, 2.3, 'var(--lp-purple)'],
    ['p4', 3.4, 1.2, 'var(--lp-purple)'], ['p5', 5, 0.2, 'var(--lp-moon-mark)'], ['p5', 5, 2.7, 'var(--lp-moon-mark)'],
    ['p6', 3.4, 0.6, 'var(--lp-rust)'], ['p7', 3.2, 1.9, 'var(--lp-amber)'],
  ];
  return (
    <svg className="lp-net" viewBox="0 0 800 600" role="img" aria-label="Animated network: by-products flowing from source plants through processing hubs to consumer industries">
      <defs>
        {Object.entries(PATHS).map(([id, d]) => <path key={id} id={id} d={d} />)}
      </defs>
      {Object.entries(PATHS).map(([id, d], i) => (
        <path key={id} d={d} className={`lp-link ${id === 'p6' || id === 'p7' ? 'dashed' : ''}`} style={{ animationDelay: `${300 + i * 120}ms` }} />
      ))}
      {flows.map(([id, dur, begin, color], i) => (
        <circle key={i} r="6" className="lp-particle" style={{ fill: color }}>
          <animateMotion dur={`${dur}s`} begin={`${begin}s`} repeatCount="indefinite" rotate="auto">
            <mpath href={`#${id}`} />
          </animateMotion>
        </circle>
      ))}
      {[[90, 140], [110, 330], [90, 470]].map(([x, y], i) => (
        <g key={`s${i}`} className="lp-node" style={{ animationDelay: `${i * 400}ms` }}>
          <circle cx={x} cy={y} r="26" className="halo" style={{ fill: 'var(--lp-rust)' }} />
          <circle cx={x} cy={y} r="14" style={{ fill: 'var(--lp-rust)' }} />
        </g>
      ))}
      <g className="lp-node" style={{ animationDelay: '200ms' }}>
        <circle cx="400" cy="250" r="30" className="halo" style={{ fill: 'var(--lp-purple)' }} />
        <rect x="384" y="234" width="32" height="32" rx="8" style={{ fill: 'var(--lp-purple)' }} />
      </g>
      <g className="lp-node proposed">
        <circle cx="400" cy="430" r="18" style={{ fill: 'var(--lp-cream)', stroke: 'var(--lp-amber)', strokeWidth: 3, strokeDasharray: '5 4' }} />
      </g>
      {[[700, 120], [700, 340], [700, 480]].map(([x, y], i) => (
        <g key={`c${i}`} className="lp-node" style={{ animationDelay: `${600 + i * 300}ms` }}>
          <circle cx={x} cy={y} r="24" className="halo" style={{ fill: 'var(--lp-moon-mark)' }} />
          <circle cx={x} cy={y} r="13" style={{ fill: 'var(--lp-moon-mark)' }} />
        </g>
      ))}
    </svg>
  );
}

function Ring({ label, value, delay }) {
  const ref = useRef(null);
  const seen = useInView(ref, 0.3);
  const C = 2 * Math.PI * 42;
  return (
    <div ref={ref} className={`lp-ring ${seen ? 'in' : ''}`} style={{ transitionDelay: `${delay}ms` }}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <circle cx="50" cy="50" r="42" className="track" />
        <circle cx="50" cy="50" r="42" className="val" style={{ strokeDasharray: C, strokeDashoffset: seen ? C * (1 - value / 100) : C, transitionDelay: `${delay + 150}ms` }} />
      </svg>
      <span className="lp-ring-num">{value}</span>
      <span className="lp-ring-label">{label}</span>
    </div>
  );
}

function PathCard({ kind, title, text, example, delay }) {
  const ref = useRef(null);
  const seen = useInView(ref, 0.3);
  const shapes = {
    direct: <><circle cx="30" cy="40" r="12" fill="#B4441C" /><path className="draw" d="M44,40 L276,40" stroke="#1A93AD" /><circle cx="290" cy="40" r="12" fill="#1A93AD" /></>,
    multi: <><circle cx="30" cy="40" r="12" fill="#B4441C" /><path className="draw" d="M44,40 L144,40" stroke="#6D4BB3" /><rect x="146" y="28" width="24" height="24" rx="6" fill="#6D4BB3" /><path className="draw d2" d="M172,40 L276,40" stroke="#6D4BB3" /><circle cx="290" cy="40" r="12" fill="#1A93AD" /></>,
    hidden: <><circle cx="30" cy="40" r="12" fill="#B4441C" /><path className="draw dash" d="M44,40 L144,40" stroke="#B7791F" /><circle cx="158" cy="40" r="12" fill="#FFF8E6" stroke="#B7791F" strokeWidth="3" strokeDasharray="4 3" /><path className="draw dash d2" d="M172,40 L276,40" stroke="#B7791F" /><circle cx="290" cy="40" r="12" fill="#1A93AD" /></>,
  };
  return (
    <div ref={ref} className={`lp-path rv ${seen ? 'in' : ''}`} style={{ transitionDelay: `${delay}ms` }}>
      <svg viewBox="0 0 320 80" aria-hidden="true">{shapes[kind]}</svg>
      <h3>{title}</h3>
      <p>{text}</p>
      <p className="lp-example">{example}</p>
    </div>
  );
}

export default function Landing() {
  const [t, setT] = useState(null);
  const progress = useRef(null);
  const hero = useRef(null);

  useEffect(() => { api.overview().then((d) => setT(d.totals)).catch(() => {}); }, []);

  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const h = document.documentElement;
        const p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
        if (progress.current) progress.current.style.transform = `scaleX(${p})`;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(raf); };
  }, []);

  const onPointer = (e) => {
    const el = hero.current;
    if (!el || reduceMotion()) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
    el.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
  };

  const go = (hash) => { window.location.hash = hash; window.scrollTo(0, 0); };
  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: reduceMotion() ? 'auto' : 'smooth' });

  return (
    <div className="lp">
      <div className="lp-progress" ref={progress} aria-hidden="true" />
      <header className="lp-nav">
        <button type="button" className="lp-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <span className="lp-mark" aria-hidden="true" />Byloop
        </button>
        <nav aria-label="Landing sections">
          <button type="button" onClick={() => scrollTo('how')}>How it works</button>
          <button type="button" onClick={() => scrollTo('score')}>Scoring</button>
          <button type="button" onClick={() => scrollTo('loop')}>The loop</button>
        </nav>
        <button type="button" className="lp-btn" onClick={() => go('#/command')}>Launch platform</button>
      </header>

      <section className="lp-hero" ref={hero} onPointerMove={onPointer}>
        <div className="lp-hero-copy">
          <p className="lp-eyebrow word" style={{ animationDelay: '0ms' }}>Industrial symbiosis intelligence · India</p>
          <h1 className="lp-h1">
            <SplitWords text="Waste is a resource" start={120} />
            <br />
            <SplitWords text="in the" start={480} />
            <em><SplitWords text="wrong place." start={660} /></em>
          </h1>
          <Rotator />
          <div className="lp-cta word" style={{ animationDelay: '1100ms' }}>
            <button type="button" className="lp-btn lg" onClick={() => go('#/analyse')}>Analyse a by-product</button>
            <button type="button" className="lp-btn ghost lg" onClick={() => go('#/command')}>See the live network</button>
          </div>
        </div>
        <div className="lp-hero-art">
          <HeroNetwork />
          <ul className="lp-legend" aria-label="Legend">
            <li><i style={{ background: '#B4441C' }} />Source</li>
            <li><i style={{ background: '#6D4BB3' }} />Processing hub</li>
            <li><i style={{ background: '#1A93AD' }} />Consumer</li>
            <li><i className="ring" />Proposed hub</li>
          </ul>
        </div>
      </section>

      <div className="lp-marquee" aria-label="Example exchanges">
        <div className="lp-track">
          {[...MARQUEE, ...MARQUEE].map((m, i) => <span key={i}>{m}<b aria-hidden="true">✳</b></span>)}
        </div>
      </div>

      <section className="lp-stats">
        <Reveal as="h2" className="lp-h2">The network, <em>right now.</em></Reveal>
        <div className="lp-stat-grid">
          {[
            ['Waste available', t?.waste_available_tpy / 1e6, (v) => `${v.toFixed(1)} Mt`, 'per year across 32 streams'],
            ['Potentially diverted', t?.potentially_diverted_tpy / 1e6, (v) => `${v.toFixed(1)} Mt`, 'allocated, never double counted'],
            ['Net CO₂e avoided', t?.net_tco2e_per_year / 1e6, (v) => `${v.toFixed(2)} Mt`, 'after processing and transport'],
            ['Economic opportunity', t?.net_inr_per_year / 1e7, (v) => `₹${Math.round(v).toLocaleString('en-IN')} Cr`, 'per year, estimated'],
            ['Opportunities', t?.opportunities, undefined, 'direct, multi-step and hidden'],
          ].map(([label, value, format, sub], i) => (
            <Reveal key={label} className="lp-stat" delay={i * 90}>
              <span className="lp-stat-num"><Counter value={value} format={format} /></span>
              <span className="lp-stat-label">{label}</span>
              <span className="lp-stat-sub">{sub}</span>
            </Reveal>
          ))}
        </div>
        <p className="lp-fine">Live from the engine. Plant locations are real (town-level); volumes and factors are illustrative screening values.</p>
      </section>

      <section className="lp-poster" id="how">
        <div className="lp-poster-top">
          <Reveal as="p" className="lp-poster-meta">Material <span /> Quantity <span /> Geography <span /> Processing <span /> Timing <span /> Environment <span /> Economics</Reveal>
          <Reveal as="h2" className="lp-giant moon">Discover</Reveal>
          <Reveal as="p" className="lp-poster-copy" delay={120}>
            A name match isn't enough. Byloop reads an industrial email, finds every sector that can replace a virgin input with the by-product,
            and checks all seven questions before calling it an opportunity.
          </Reveal>
        </div>
        <div className="lp-poster-bottom">
          <Reveal as="h2" className="lp-giant vanilla">Connect</Reveal>
          <div className="lp-paths">
            <PathCard kind="direct" title="Direct" delay={0} text="Straight from source to consumer, or processed in-house." example="NTPC Dadri → UltraTech Dadri · 9 km" />
            <PathCard kind="multi" title="Multi-step" delay={120} text="Routed through a hub with the right capability and capacity." example="Pune slag → Chakan yard → road works" />
            <PathCard kind="hidden" title="Hidden" delay={240} text="Asks what's missing, and proposes the processing hub that would unlock demand." example="Missing link near Kalinganagar" />
          </div>
        </div>
      </section>

      <section className="lp-score" id="score">
        <Reveal as="h2" className="lp-h2">Not “AI says 93%”.<br /><em>Here's why it's 93.</em></Reveal>
        <div className="lp-rings">
          {DIMS.map(([l, v], i) => <Ring key={l} label={l} value={v} delay={i * 110} />)}
        </div>
        <Reveal as="p" className="lp-lede" delay={200}>
          Every opportunity is scored on seven weighted dimensions, with a reason for each: ✓ meets, ! caution, × fails.
          Net CO₂e counts the emissions of processing and trucking, so we never overclaim.
        </Reveal>
      </section>

      <section className="lp-loop" id="loop">
        <div className="lp-orbit" aria-hidden="true">
          <div className="lp-orbit-ring" />
          <div className="lp-orbit-dot" />
          {['Find', 'Explain', 'Quantify', 'Contact', 'Respond', 'Re-rank'].map((w, i) => (
            <span key={w} className="lp-orbit-label" style={{ '--a': `${i * 60 - 90}deg` }}>{w}</span>
          ))}
          <div className="lp-orbit-core"><b>94 → 76</b><span>after a “Not feasible” reply</span></div>
        </div>
        <div className="lp-loop-copy">
          <Reveal as="h2" className="lp-h2 light">It doesn't stop at <em>a recommendation.</em></Reveal>
          <Reveal as="p" className="lp-lede light" delay={120}>
            Byloop writes the outreach email, with one-click Interested / Need info / Not feasible links. Every reply lands back
            in the platform and re-ranks the next recommendation.
          </Reveal>
          <Reveal className="lp-cta" delay={240}>
            <button type="button" className="lp-btn vanilla lg" onClick={() => go('#/outreach')}>Open outreach</button>
          </Reveal>
        </div>
      </section>

      <section className="lp-final">
        <Reveal as="h2" className="lp-giant moon">Close the loop.</Reveal>
        <Reveal className="lp-cta center" delay={150}>
          <button type="button" className="lp-btn lg" onClick={() => go('#/analyse')}>Analyse a by-product</button>
          <button type="button" className="lp-btn ghost lg" onClick={() => go('#/command')}>Launch platform</button>
        </Reveal>
        <p className="lp-fine">Byloop · PS 5 Sustainability · Screening estimates to be validated with lab tests, LCA data and logistics quotes.</p>
      </section>
    </div>
  );
}
