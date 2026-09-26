function toMessage(detail, status) {
  if (!detail) return `Request failed (${status})`;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? JSON.stringify(d)).join('; ');
  return detail.msg ?? JSON.stringify(detail);
}

async function request(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach the API. Is the backend running on port 8000?');
  }
  if (!(res.headers.get('content-type') || '').includes('json')) {
    throw new Error('The API returned a web page instead of data. Restart the frontend dev server so its /api proxy to port 8000 takes effect.');
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(toMessage(data?.detail, res.status));
  return data;
}

export const api = {
  meta: () => request('/api/meta'),
  overview: () => request('/api/overview'),
  network: (scenario = {}, limit = 150) => request(`/api/network?limit=${limit}`, { method: 'POST', body: scenario }),
  material: (id) => request(`/api/materials/${id}`),
  schemes: () => request('/api/schemes'),
  extract: (text) => request('/api/extract', { method: 'POST', body: { text } }),
  analyze: (payload) => request('/api/analyze', { method: 'POST', body: payload }),
  history: () => request('/api/history?limit=8'),
  historyItem: (id) => request(`/api/history/${id}`),
  outreach: () => request('/api/outreach'),
  createOutreach: (payload) => request('/api/outreach', { method: 'POST', body: payload }),
  updateOutreach: (id, fields) => request(`/api/outreach/${id}`, { method: 'PATCH', body: fields }),
  sendOutreach: (id) => request(`/api/outreach/${id}/send`, { method: 'POST', body: {} }),
  seedDemoOutreach: () => request('/api/demo/outreach', { method: 'POST', body: {} }),
  clearDemoOutreach: () => request('/api/demo/outreach', { method: 'DELETE' }),
  customIndustries: () => request('/api/custom-industries'),
  addCustomIndustry: (payload) => request('/api/custom-industries', { method: 'POST', body: payload }),
  deleteCustomIndustry: (id) => request(`/api/custom-industries/${id}`, { method: 'DELETE' }),
};
