import React, { useState, useEffect } from 'react';
import { Shield, AlertCircle, HelpCircle, Network, Layers, RefreshCw } from 'lucide-react';
import { fetchIncidents, fetchIncident } from './services/api';
import IncidentOverview from './components/IncidentOverview';

export default function App() {
  const [activeTab, setActiveTab] = useState('incident'); // incident | ask | graph | spof
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [incidentDetail, setIncidentDetail] = useState(null);
  const [loading, setLoading] = useState(true);

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
          <button className="btn btn-outline" onClick={loadIncidents} title="Refresh Data">
            <RefreshCw size={14} /> Refresh
          </button>
        </header>

        <div className="content-container">
          {loading ? (
            <div className="card">
              <div className="card-body">Loading security monitor data...</div>
            </div>
          ) : (
            <>
              {activeTab === 'incident' && (
                <IncidentOverview incident={incidentDetail} />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
