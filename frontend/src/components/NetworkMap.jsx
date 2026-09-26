import { useEffect, useMemo } from 'react';
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORY_LABEL, fmt } from '../format';

const INDIA = [22.5, 79];

function css(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function Fit({ points, focus }) {
  const map = useMap();
  useEffect(() => {
    const pts = focus?.length ? focus : points;
    if (pts.length) map.flyToBounds(pts, { padding: [50, 50], maxZoom: focus?.length ? 10 : 8, duration: 0.5 });
  }, [points, focus, map]);
  return null;
}

function routeOf(o) {
  const a = [o.origin.lat, o.origin.lon];
  if (o.pathway_type === 'via_hub' && o.hub) return [[a, [o.hub.lat, o.hub.lon], [o.consumer.lat, o.consumer.lon]]];
  if (o.pathway_type === 'missing_hub' && o.proposed_hub) {
    const h = [o.proposed_hub.lat, o.proposed_hub.lon];
    return [[a, h], ...o.consumers.map((c) => [h, [c.lat, c.lon]])];
  }
  return [[a, [o.consumer.lat, o.consumer.lon]]];
}

export function MapLegend() {
  return (
    <span className="legend" aria-label="Map legend">
      <span><i className="dot" style={{ background: 'var(--producer)' }} />Source</span>
      <span><i className="dot" style={{ background: 'var(--hub)' }} />Processing hub</span>
      <span><i className="dot" style={{ background: 'var(--consumer)' }} />Consumer</span>
      <span><i className="dot" style={{ border: '1.5px dashed var(--hidden)' }} />Proposed hub</span>
    </span>
  );
}

export function SitesMap({ groups }) {
  const color = { src: css('--producer', '#b4441c'), hub: css('--hub', '#6d4bb3'), dst: css('--consumer', '#00836b') };
  const points = useMemo(() => groups.flatMap((g) => g.sites.map((s) => [s.lat, s.lon])), [groups]);
  return (
    <div className="map-wrap">
      <MapContainer center={INDIA} zoom={5} scrollWheelZoom={false}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
        <Fit points={points} />
        {groups.flatMap((g) => g.sites.map((s) => (
          <CircleMarker key={`${g.role}-${s.id}`} center={[s.lat, s.lon]} radius={g.role === 'src' ? 8 : 6}
            pathOptions={{ color: color[g.role], fillColor: color[g.role], fillOpacity: 0.9, weight: 1.5 }}>
            <Tooltip className="map-tip"><b>{s.name}</b><br />{s.sector} · {s.city}{s.quantity_tpm ? ` · ${fmt(s.quantity_tpm)} t/mo` : ''}</Tooltip>
          </CircleMarker>
        )))}
      </MapContainer>
    </div>
  );
}

export default function NetworkMap({ opportunities, selectedId, onSelect, hero = false, focusSelected = false, sites = [] }) {
  const colors = {
    producer: css('--producer', '#b4441c'),
    consumer: css('--consumer', '#00836b'),
    hub: css('--hub', '#6d4bb3'),
    hidden: css('--hidden', '#b7791f'),
    muted: css('--line-strong', '#cfc9bb'),
  };
  const catColor = { direct: colors.consumer, multi_step: colors.hub, hidden: colors.hidden };

  const { nodes, points } = useMemo(() => {
    const n = new Map();
    const add = (key, v) => { if (!n.has(key)) n.set(key, v); };
    opportunities.forEach((o) => {
      add(`src:${o.origin.lat},${o.origin.lon}`, { role: 'src', lat: o.origin.lat, lon: o.origin.lon, name: o.origin.name, sub: o.material_name });
      if (o.hub) add(`hub:${o.hub.id}`, { role: 'hub', lat: o.hub.lat, lon: o.hub.lon, name: o.hub.name, sub: o.processing?.label });
      if (o.proposed_hub) add(`ph:${o.id}`, { role: 'proposed', lat: o.proposed_hub.lat, lon: o.proposed_hub.lon, name: 'Proposed hub', sub: `${o.proposed_hub.step_label} · near ${o.proposed_hub.label}` });
      o.consumers.forEach((c) => add(`dst:${c.id}`, { role: 'dst', lat: c.lat, lon: c.lon, name: c.name, sub: `${c.sector} · ${c.city}` }));
    });
    const pts = [...n.values()].map((v) => [v.lat, v.lon]);
    return { nodes: [...n.values()], points: pts };
  }, [opportunities]);

  const selected = opportunities.find((o) => o.id === selectedId);
  const focus = useMemo(() => (focusSelected && selected ? routeOf(selected).flat() : null), [focusSelected, selected]);
  const ordered = [...opportunities].sort((a, b) => (a.id === selectedId) - (b.id === selectedId));
  const roleColor = { src: colors.producer, hub: colors.hub, dst: colors.consumer, proposed: colors.hidden };

  return (
    <div className={`map-wrap ${hero ? 'hero' : ''}`}>
      <MapContainer center={INDIA} zoom={5} scrollWheelZoom={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <Fit points={points} focus={focus} />
        {sites.map((s) => (
          <CircleMarker key={`bg-${s.id}`} center={[s.lat, s.lon]} radius={3}
            pathOptions={{ color: colors.muted, fillColor: colors.muted, fillOpacity: 0.8, weight: 0 }}>
            <Tooltip className="map-tip"><b>{s.name}</b><br />{s.sector}</Tooltip>
          </CircleMarker>
        ))}
        {ordered.map((o) => {
          const active = o.id === selectedId;
          const dim = selectedId && !active;
          return routeOf(o).map((line, i) => (
            <Polyline
              key={`${o.id}-${i}-${active ? 'on' : 'off'}`}
              positions={line}
              pathOptions={{
                color: catColor[o.category],
                weight: active ? 4 : 2,
                opacity: dim ? 0.18 : active ? 1 : 0.6,
                dashArray: o.pathway_type === 'missing_hub' ? '6 6' : null,
                className: `flow${active ? ' active' : ''}${o.pathway_type === 'missing_hub' ? ' missing' : ''}`,
              }}
              eventHandlers={{ click: () => onSelect?.(o.id) }}
            >
              <Tooltip sticky className="map-tip">
                <b>{o.title}</b><br />
                {o.material_name} · {CATEGORY_LABEL[o.category]} · score {o.score} · {fmt(o.road_km)} km
              </Tooltip>
            </Polyline>
          ));
        })}
        {nodes.map((n) => (
          <CircleMarker
            key={`${n.role}-${n.lat}-${n.lon}-${n.name}`}
            center={[n.lat, n.lon]}
            radius={n.role === 'src' ? 8 : n.role === 'dst' ? 6 : 7}
            pathOptions={{
              color: roleColor[n.role],
              fillColor: n.role === 'proposed' ? 'transparent' : roleColor[n.role],
              fillOpacity: 0.95,
              weight: n.role === 'proposed' ? 2.5 : 1.5,
              dashArray: n.role === 'proposed' ? '3 3' : null,
              className: `map-node map-${n.role}`,
            }}
          >
            <Tooltip className="map-tip"><b>{n.name}</b><br />{n.sub}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
