import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Shield, AlertCircle, HelpCircle, Network, Layers, RefreshCw, Flame, X, Bell } from 'lucide-react';
import {
  fetchIncidents,
  fetchIncident,
  fetchGraph,
  simulateHack,
  subscribeApiStatus,
  checkApiHealth,
} from './services/api';
import IncidentOverview from './components/IncidentOverview';
import TracePanel from './components/TracePanel';
import FixPanel from './components/FixPanel';
import AskBox from './components/AskBox';
import GraphView from './components/GraphView';
import SpofView from './components/SpofView';

export default function App() {
  const getInitialTab = () => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab');
      if (tabParam && ['incident', 'ask', 'graph', 'spof'].includes(tabParam)) return tabParam;
      const hash = window.location.hash.replace('#', '');
      if (hash && ['incident', 'ask', 'graph', 'spof'].includes(hash)) return hash;
    } catch {}
    return 'incident';
  };

  const [activeTab, setActiveTabState] = useState(getInitialTab); // incident | ask | graph | spof
  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    window.location.hash = tab;
  };
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [isLiveApi, setIsLiveApi] = useState(false);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [toast, setToast] = useState(null);

  const knownIdsRef = useRef(new Set());

  // Initial load
  useEffect(() => {
    checkApiHealth();
    const unsub = subscribeApiStatus((live) => setIsLiveApi(live));

    async function init() {
      setLoading(true);
      const [list, graph] = await Promise.all([fetchIncidents(), fetchGraph()]);
      setIncidents(list);
      setGraphData(graph);

      if (list && list.length > 0) {
        list.forEach((i) => knownIdsRef.current.add(i.id));
        const activeId = list[0].id;
        setSelectedIncidentId(activeId);
        const detail = await fetchIncident(activeId);
        setIncidentDetail(detail);
      }
      setLoading(false);
    }

    init();

    // 5-second polling for incidents
    const interval = setInterval(async () => {
      const list = await fetchIncidents();
      if (list && list.length > 0) {
        const known = knownIdsRef.current;
        const newOnes = list.filter((i) => !known.has(i.id));

        if (newOnes.length > 0) {
          const newest = newOnes[0];
          const scriptName = newest.script ? newest.script.split('/').pop() : 'script';
          setToast({
            id: newest.id,
            title: `New alarm: ${scriptName} changed`,
            message: `Incident ${newest.id} detected across client perimeter.`,
          });
          newOnes.forEach((i) => known.add(i.id));
          setIncidents(list);
          // Open the new alarm straight away
          setSelectedIncidentId(newest.id);
          const detail = await fetchIncident(newest.id);
          setIncidentDetail(detail);
        }
      }
    }, 5000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, []);

  // Compute safe sites from graph not present in affected
  const safeSites = useMemo(() => {
    if (!graphData || !incidentDetail) return [];

    const siteNodes = (graphData.nodes || []).filter((n) => n.label === 'Site');
    const affectedUrls = new Set(
      (incidentDetail.affected || []).map((a) =>
        (a.site || '').toLowerCase().trim().replace(/\/$/, '')
      )
    );

    // Clients map: { siteUrl: clientName }
    const clientMap = {};
    const edges = graphData.edges || [];
    const nodesById = {};
    (graphData.nodes || []).forEach((n) => {
      nodesById[n.id] = n;
    });

    edges.forEach((e) => {
      if (e.type === 'OWNS') {
        const clientNode = nodesById[e.from];
        const siteNode = nodesById[e.to];
        if (clientNode && siteNode) {
          clientMap[siteNode.name] = clientNode.name;
        }
      }
    });

    return siteNodes
      .filter((s) => {
        const url = (s.name || '').toLowerCase().trim().replace(/\/$/, '');
        return !affectedUrls.has(url);
      })
      .map((s) => ({
        ...s,
        displayName: clientMap[s.name] || s.name.replace(/^https?:\/\//, '').replace(/\.netlify\.app.*$/, ''),
      }));
  }, [graphData, incidentDetail]);

  const loadIncidents = async () => {
    const list = await fetchIncidents();
    setIncidents(list);
    if (list && list.length > 0 && !selectedIncidentId) {
      handleSelectIncident(list[0].id);
    }
  };

  const handleSelectIncident = async (id) => {
    setSelectedIncidentId(id);
    const detail = await fetchIncident(id);
    setIncidentDetail(detail);
  };

  const handleSimulateHack = async () => {
    setSimulating(true);
    try {
      const res = await simulateHack('chat-widget.js');
      if (res && res.id) {
        knownIdsRef.current.add(res.id);
        const list = await fetchIncidents();
        setIncidents(list);
        setSelectedIncidentId(res.id);
        const detail = await fetchIncident(res.id);
        setIncidentDetail(detail);
        setActiveTab('incident');
      }
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-badge">BR</div>
          <div className="logo-text">
            <h1>BLAST RADIUS</h1>
            <p>FalkorDB Supply Chain</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-link ${activeTab === 'incident' ? 'active' : ''}`}
            onClick={() => setActiveTab('incident')}
          >
            <AlertCircle size={18} />
            <span>Incident Response</span>
          </button>

          <button
            className={`nav-link ${activeTab === 'ask' ? 'active' : ''}`}
            onClick={() => setActiveTab('ask')}
          >
            <HelpCircle size={18} />
            <span>Ask Security Agent</span>
          </button>

          <button
            className={`nav-link ${activeTab === 'graph' ? 'active' : ''}`}
            onClick={() => setActiveTab('graph')}
          >
            <Network size={18} />
            <span>Dependency Graph</span>
          </button>

          <button
            className={`nav-link ${activeTab === 'spof' ? 'active' : ''}`}
            onClick={() => setActiveTab('spof')}
          >
            <Layers size={18} />
            <span>SPOF Analysis</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>Graph: FalkorDB Cloud</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-wrapper">
        <header className="top-bar">
          <div className="top-bar-title">
            <Shield size={20} color="#2563eb" />
            <span>Third-Party Script Blast Radius Monitor</span>
            {/* Header Badge: LIVE API / MOCK DATA */}
            <span className={`api-badge ${isLiveApi ? 'live' : 'mock'}`} style={{ marginLeft: '12px' }}>
              <span className="dot"></span>
              {isLiveApi ? 'LIVE API' : 'MOCK DATA'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {incidents.length > 1 && (
              <select
                value={selectedIncidentId || ''}
                onChange={(e) => handleSelectIncident(e.target.value)}
                style={{
                  padding: '7px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '13px',
                  background: '#ffffff',
                  fontWeight: 500,
                  outline: 'none',
                }}
              >
                {incidents.map((inc) => (
                  <option key={inc.id} value={inc.id}>
                    {inc.id} ({inc.script ? inc.script.split('/').pop() : 'script'}) - {inc.pages_affected || 3} pages
                  </option>
                ))}
              </select>
            )}

            <button
              className="btn btn-danger"
              onClick={handleSimulateHack}
              disabled={simulating}
              title="Simulate 3rd-party script compromise"
            >
              <Flame size={15} />
              {simulating ? 'Simulating...' : 'Simulate hack'}
            </button>

            <button className="btn btn-outline" onClick={loadIncidents} title="Refresh Data">
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </header>

        <div className="content-container">
          {loading ? (
            <div className="card">
              <div className="card-body">Loading security monitor data...</div>
            </div>
          ) : (
            <>
              {activeTab === 'incident' && !incidentDetail && (
                <div className="card">
                  <div className="card-body">
                    <strong>All clear.</strong> No script changes detected.{' '}
                    Monitoring {(graphData?.nodes || []).filter((n) => n.label === 'Site').length} client site(s).
                    New alarms appear here automatically.
                  </div>
                </div>
              )}

              {activeTab === 'incident' && incidentDetail && (
                <>
                  <IncidentOverview incident={incidentDetail} safeSites={safeSites} />
                  <TracePanel trace={incidentDetail?.trace} />
                  <FixPanel incident={incidentDetail} onIncidentUpdated={(updated) => setIncidentDetail(updated)} />
                </>
              )}

              {activeTab === 'ask' && (
                <AskBox />
              )}

              {activeTab === 'graph' && (
                <GraphView />
              )}

              {activeTab === 'spof' && (
                <SpofView />
              )}
            </>
          )}
        </div>

        {/* Live Alarm Toast */}
        {toast && (
          <div className="alarm-toast">
            <Bell size={22} color="#fca5a5" style={{ animation: 'bounce 1s infinite' }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '14px' }}>{toast.title}</div>
              <div style={{ fontSize: '12px', color: '#fca5a5', marginTop: '2px' }}>{toast.message}</div>
            </div>
            <button
              className="btn btn-outline"
              style={{ padding: '4px 8px', fontSize: '11px', color: '#ffffff', borderColor: '#ef4444', background: '#991b1b' }}
              onClick={() => {
                handleSelectIncident(toast.id);
                setActiveTab('incident');
                setToast(null);
              }}
            >
              View
            </button>
            <button
              onClick={() => setToast(null)}
              style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer' }}
            >
              <X size={16} />
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
