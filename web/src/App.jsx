import React, { useState, useEffect } from 'react';
import { Shield, AlertCircle, HelpCircle, Network, Layers, RefreshCw, Flame } from 'lucide-react';
import { fetchIncidents, fetchIncident, simulateHack } from './services/api';
import IncidentOverview from './components/IncidentOverview';
import TracePanel from './components/TracePanel';
import FixPanel from './components/FixPanel';
import AskBox from './components/AskBox';

export default function App() {
  const [activeTab, setActiveTab] = useState('incident'); // incident | ask | graph | spof
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);

  // Load incident list on mount
  useEffect(() => {
    loadIncidents();
  }, []);

  const loadIncidents = async () => {
    setLoading(true);
    const list = await fetchIncidents();
    setIncidents(list);
    if (list && list.length > 0) {
      const activeId = list[0].id;
      setSelectedIncidentId(activeId);
      const detail = await fetchIncident(activeId);
      setIncidentDetail(detail);
    }
    setLoading(false);
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
        // Refresh incidents list and switch to the new incident
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
            <span>Graph Connected (FalkorDB)</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-wrapper">
        <header className="top-bar">
          <div className="top-bar-title">
            <Shield size={20} color="#2563eb" />
            <span>Third-Party Script Blast Radius Monitor</span>
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
              {activeTab === 'incident' && (
                <>
                  <IncidentOverview incident={incidentDetail} />
                  <TracePanel trace={incidentDetail?.trace} />
                  <FixPanel incident={incidentDetail} onIncidentUpdated={(updated) => setIncidentDetail(updated)} />
                </>
              )}

              {activeTab === 'ask' && (
                <AskBox />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
