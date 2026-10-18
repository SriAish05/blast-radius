import mockIncident from '../mocks/incident.json';
import mockIncidents from '../mocks/incidents.json';
import mockSpof from '../mocks/spof.json';
import mockGraph from '../mocks/graph.json';
import mockAsk from '../mocks/ask.json';
import mockApprove from '../mocks/approve.json';

const rawBase =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) ||
  'http://localhost:8000/api';
export const API_BASE = rawBase.replace(/\/+$/, '');

let apiListeners = [];
let isLiveApi = false;

function notifyStatus(status) {
  if (isLiveApi !== status) {
    isLiveApi = status;
    apiListeners.forEach((fn) => fn(status));
  }
}

export function subscribeApiStatus(fn) {
  apiListeners.push(fn);
  fn(isLiveApi);
  return () => {
    apiListeners = apiListeners.filter((l) => l !== fn);
  };
}

export function getApiStatus() {
  return isLiveApi;
}

export async function checkApiHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      if (data && data.ok !== false) {
        notifyStatus(true);
        return true;
      }
    }
    notifyStatus(false);
    return false;
  } catch {
    notifyStatus(false);
    return false;
  }
}

async function safeFetch(url, options = {}, fallbackData = null) {
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      console.warn(`API ${url} returned ${res.status}. Using fallback.`);
      notifyStatus(false);
      return fallbackData;
    }
    const data = await res.json();
    notifyStatus(true);
    return data;
  } catch (err) {
    console.warn(`API ${url} fetch error: ${err.message}. Using fallback.`);
    notifyStatus(false);
    return fallbackData;
  }
}

export async function fetchIncidents() {
  const data = await safeFetch(`${API_BASE}/incidents`, {}, null);
  // If API was unreachable or failed, data is null -> fall back to mocks
  if (data === null) {
    return mockIncidents;
  }
  // When live, preserve real response (even if empty [])
  return data;
}

export async function fetchIncident(id) {
  const data = await safeFetch(`${API_BASE}/incidents/${id}`, {}, null);
  return data !== null ? data : mockIncident;
}

export async function simulateHack(script = 'chat-widget.js') {
  const fallback = { id: `inc-${Date.now().toString().slice(-6)}`, script };
  const res = await safeFetch(
    `${API_BASE}/incidents/simulate`,
    {
      method: 'POST',
      body: JSON.stringify({ script }),
    },
    fallback
  );
  return res || fallback;
}

export async function approveIncident(id) {
  const fallback = { ...mockApprove, id };
  const res = await safeFetch(
    `${API_BASE}/incidents/${id}/approve`,
    {
      method: 'POST',
    },
    fallback
  );
  return res || fallback;
}

export async function askAgent(question) {
  const fallback = {
    ...mockAsk,
    question,
  };
  const res = await safeFetch(
    `${API_BASE}/ask`,
    {
      method: 'POST',
      body: JSON.stringify({ question }),
    },
    fallback
  );
  return res || fallback;
}

export async function fetchGraph() {
  const data = await safeFetch(`${API_BASE}/graph`, {}, mockGraph);
  return data || mockGraph;
}

export async function fetchSpof() {
  const data = await safeFetch(`${API_BASE}/spof`, {}, mockSpof);
  return data || mockSpof;
}
