import { useEffect, useRef, useState } from 'react';

export const reduceMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function useInView(ref, threshold = 0.25) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, threshold]);
  return seen;
}

export function Counter({ value, format = (v) => Math.round(v).toLocaleString('en-IN'), duration = 1400 }) {
  const ref = useRef(null);
  const seen = useInView(ref, 0.2);
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!seen || value == null || Number.isNaN(value)) return undefined;
    if (reduceMotion()) { setV(value); return undefined; }
    let raf;
    const t0 = performance.now();
    const from = 0;
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / duration);
      setV(from + (value - from) * (1 - (1 - p) ** 3));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, value, duration]);
  return <span ref={ref}>{value == null || Number.isNaN(value) ? '—' : format(v)}</span>;
}

export function SplitWords({ text, start = 0, step = 80 }) {
  return text.split(' ').map((w, i) => (
    <span key={`${w}-${i}`} className="word" style={{ animationDelay: `${start + i * step}ms` }}>{w}&nbsp;</span>
  ));
}
