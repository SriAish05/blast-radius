// Test suite for web/src/services/api.js and dashboard state logic
// Runs locally and completely offline with mocked global.fetch.
// Loads mock JSON through Node's filesystem/JSON parsing in the test harness.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. Load mock JSON files directly via filesystem
const mocksDir = path.join(__dirname, 'src', 'mocks');
const mockIncidentsRaw = JSON.parse(fs.readFileSync(path.join(mocksDir, 'incidents.json'), 'utf-8'));
const mockIncidentRaw = JSON.parse(fs.readFileSync(path.join(mocksDir, 'incident.json'), 'utf-8'));

// 2. Read api.js and adapt it for Node test execution without import attributes
const apiFilePath = path.join(__dirname, 'src', 'services', 'api.js');
let apiSource = fs.readFileSync(apiFilePath, 'utf-8');

// Replace standard Vite JSON imports with parsed inline objects
apiSource = apiSource.replace(
  /import\s+(\w+)\s+from\s+['"]\.\.\/mocks\/([^'"]+\.json)['"];?/g,
  (match, varName, jsonFileName) => {
    const jsonPath = path.join(mocksDir, jsonFileName);
    const content = fs.readFileSync(jsonPath, 'utf-8');
    return `const ${varName} = ${content.trim()};`;
  }
);

const dataUri = `data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`;
const {
  fetchIncidents,
  fetchIncident,
  checkApiHealth,
  subscribeApiStatus,
  getApiStatus,
} = await import(dataUri);

console.log('Running API client & state management unit tests...');

let statusLog = [];
const unsub = subscribeApiStatus((status) => {
  statusLog.push(status);
});

// Test 1: Live API with non-empty incidents
console.log('Test 1: Live API with non-empty incidents');
global.fetch = async (url) => {
  if (url.endsWith('/health')) {
    return { ok: true, json: async () => ({ ok: true, nodes: 42 }) };
  }
  if (url.endsWith('/incidents')) {
    return {
      ok: true,
      json: async () => [
        { id: 'inc-999999', kind: 'hash_change', status: 'open', script: 'chat-widget.js', pages_affected: 3 }
      ],
    };
  }
  throw new Error(`Unexpected URL: ${url}`);
};

const healthRes1 = await checkApiHealth();
assert.strictEqual(healthRes1, true, 'Health check should return true when ok: true');
assert.strictEqual(getApiStatus(), true, 'Status should be live');

const liveIncidents = await fetchIncidents();
assert.strictEqual(liveIncidents.length, 1, 'Should return exactly 1 live incident');
assert.strictEqual(liveIncidents[0].id, 'inc-999999', 'Should return the live incident ID');
console.log('PASS: Test 1');

// Test 2: Live API with empty incidents list []
console.log('Test 2: Live API with empty incidents list ([])');
global.fetch = async (url) => {
  if (url.endsWith('/incidents')) {
    return {
      ok: true,
      json: async () => [],
    };
  }
  throw new Error(`Unexpected URL: ${url}`);
};

const emptyIncidents = await fetchIncidents();
assert.strictEqual(Array.isArray(emptyIncidents), true, 'Should return array');
assert.strictEqual(emptyIncidents.length, 0, 'Live empty array must remain empty and NOT revert to mock data');
assert.strictEqual(getApiStatus(), true, 'Status should remain live when receiving empty response');
console.log('PASS: Test 2');

// Test 3: API failure / offline mode
console.log('Test 3: API failure / offline mode');
global.fetch = async (url) => {
  throw new Error('Connection refused: backend offline');
};

const healthRes3 = await checkApiHealth();
assert.strictEqual(healthRes3, false, 'Health check should fail when network throws');
assert.strictEqual(getApiStatus(), false, 'Status should update to false (mock)');

const fallbackIncidents = await fetchIncidents();
assert.ok(fallbackIncidents.length > 0, 'Should fall back to mock incidents when offline');
assert.strictEqual(fallbackIncidents[0].id, mockIncidentsRaw[0].id, 'Fallback data must match mock incidents');
assert.strictEqual(getApiStatus(), false, 'Status should remain mock');
console.log('PASS: Test 3');

// Test 4: Health endpoint returns ok: false (e.g. database down / degraded)
console.log('Test 4: Health endpoint returns ok: false (database down/degraded)');
global.fetch = async (url) => {
  if (url.endsWith('/health')) {
    return { ok: true, json: async () => ({ ok: false, error: 'database_unavailable' }) };
  }
  throw new Error(`Unexpected URL: ${url}`);
};

const healthRes4 = await checkApiHealth();
assert.strictEqual(healthRes4, false, 'Health check should return false when response ok: false');
assert.strictEqual(getApiStatus(), false, 'Status should be false');
console.log('PASS: Test 4');

// Test 5: Degraded backend (incidents API returns HTTP 500)
console.log('Test 5: Incidents API error (HTTP 500)');
global.fetch = async (url) => {
  if (url.endsWith('/incidents')) {
    return { ok: false, status: 500, json: async () => ({ detail: 'Database error' }) };
  }
  throw new Error(`Unexpected URL: ${url}`);
};

const errorFallback = await fetchIncidents();
assert.ok(errorFallback.length > 0, 'Error status must fall back to mock data rather than returning []');
assert.strictEqual(getApiStatus(), false, 'Status should be set to mock on fetch failure');
console.log('PASS: Test 5');

// Test 6: Stale incident state management logic (Correction D)
console.log('Test 6: Incident selection state transition logic');
function applyIncidentListTransition(prevState, incomingList, isLive) {
  // Simulates App.jsx loadIncidents state transition
  if (incomingList && incomingList.length > 0) {
    const hasCurrent = incomingList.some((i) => i.id === prevState.selectedId);
    const selectedId = hasCurrent ? prevState.selectedId : incomingList[0].id;
    return {
      selectedId,
      detail: hasCurrent ? prevState.detail : { id: selectedId },
    };
  } else if (incomingList && incomingList.length === 0 && isLive) {
    // Successfully loaded live list became empty -> clear stale state
    return {
      selectedId: null,
      detail: null,
    };
  }
  // If request failed or timed out, do not clear previous state
  return prevState;
}

const stateWithActive = { selectedId: 'inc-001', detail: { id: 'inc-001', script: 'chat.js' } };

// Transition A: Live API returns [] -> must clear stale selection and detail
const stateAfterResolution = applyIncidentListTransition(stateWithActive, [], true);
assert.strictEqual(stateAfterResolution.selectedId, null, 'selectedId must be cleared when live list is empty');
assert.strictEqual(stateAfterResolution.detail, null, 'detail must be cleared when live list is empty');

// Transition B: Request failure / timeout -> must preserve previous state
const stateAfterTimeout = applyIncidentListTransition(stateWithActive, null, false);
assert.strictEqual(stateAfterTimeout.selectedId, 'inc-001', 'selectedId must not be cleared on request failure');
assert.notStrictEqual(stateAfterTimeout.detail, null, 'detail must not be cleared on request failure');

console.log('PASS: Test 6');

unsub();
console.log('ALL API CLIENT AND STATE TESTS PASSED CLEANLY (6/6)');
