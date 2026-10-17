import React from 'react';
import { AlertTriangle, ExternalLink, ShieldAlert, Cpu, ShieldCheck } from 'lucide-react';

export default function IncidentOverview({ incident, safeSites = [] }) {
  if (!incident) {
    return (
      <div className="card">
        <div className="card-body">Loading incident details...</div>
      </div>
    );
  }

  const { id, kind, status, created_at, script, summary, affected = [] } = incident;

  // Helper to format breadcrumb items
  const formatHop = (hop) => {
    try {
      if (hop.startsWith('http://') || hop.startsWith('https://')) {
        const u = new URL(hop);
        if (u.pathname && u.pathname !== '/') {
          return u.pathname.replace(/^\//, '');
        }
        return u.hostname;
      }
      return hop;
    } catch {
      return hop;
    }
  };

  return (
    <div className="incident-section">
      {/* 1. Summary at Top */}
      <div className="incident-summary-banner">
        <div className="incident-summary-icon">
          <ShieldAlert size={28} />
        </div>
        <div className="incident-summary-content" style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Supply Chain Threat Detected: {script ? script.split('/').pop() : 'Unknown Script'}</h2>
            <span className="badge-runtime-only" style={{ background: '#fef2f2', borderColor: '#f87171' }}>
              Status: {status.toUpperCase()}
            </span>
          </div>
          <p style={{ marginTop: '4px', fontSize: '15px' }}>{summary}</p>
          <div className="incident-meta-tags">
            <span className="meta-pill">Incident ID: {id}</span>
            <span className="meta-pill">Type: {kind}</span>
            <span className="meta-pill">Pages Affected: {affected.length}</span>
            {created_at && <span className="meta-pill">Detected: {new Date(created_at).toLocaleTimeString()}</span>}
          </div>
        </div>
      </div>

      {/* Safe Sites Banner */}
      <div className="safe-sites-banner">
        <ShieldCheck size={18} color="#16a34a" />
        <span style={{ fontSize: '13px' }}>
          {safeSites.length > 0 ? (
            <>
              <strong>{safeSites.length} site{safeSites.length === 1 ? '' : 's'} safe:</strong>{' '}
              {safeSites.map((s) => s.displayName || s.name || s.id).join(', ')}
            </>
          ) : (
            <>
              <strong>Perimeter Impact Assessment:</strong> All client websites in the knowledge graph are affected by this script.
            </>
          )}
        </span>
      </div>

      {/* Table of affected sites/pages */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <AlertTriangle size={18} color="#dc2626" />
            <span>Affected Client Sites & Injection Vector</span>
          </div>
          <span style={{ fontSize: '13px', color: '#64748b' }}>
            {affected.length} affected page{affected.length === 1 ? '' : 's'} identified across knowledge graph
          </span>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Client</th>
                <th>Target Page</th>
                <th>Loading Chain (Breadcrumbs)</th>
                <th>Detection Type</th>
                <th>Site Maintainer</th>
              </tr>
            </thead>
            <tbody>
              {affected.map((item, idx) => {
                const chain = item.chain || [];
                return (
                  <tr key={idx}>
                    <td>
                      <strong>{item.client}</strong>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>
                        <a href={item.site} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'none' }}>
                          {item.site} <ExternalLink size={10} style={{ display: 'inline' }} />
                        </a>
                      </div>
                    </td>
                    <td>
                      <a href={item.page} target="_blank" rel="noreferrer" style={{ color: '#0f172a', textDecoration: 'underline', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                        {item.page}
                      </a>
                    </td>
                    <td>
                      <div className="chain-breadcrumbs">
                        {chain.map((hop, hIdx) => {
                          const isTarget = hIdx === chain.length - 1;
                          return (
                            <React.Fragment key={hIdx}>
                              <span className={`chain-hop ${isTarget ? 'target' : ''}`} title={hop}>
                                {formatHop(hop)}
                              </span>
                              {hIdx < chain.length - 1 && <span className="chain-arrow">→</span>}
                            </React.Fragment>
                          );
                        })}
                      </div>
                    </td>
                    <td>
                      {item.runtime_only ? (
                        <span className="badge-runtime-only" title="Injected dynamically via script; invisible in HTML source">
                          <Cpu size={12} /> RUNTIME ONLY
                        </span>
                      ) : (
                        <span className="badge-html-direct" title="Loaded directly in static HTML">
                          DIRECT HTML
                        </span>
                      )}
                    </td>
                    <td>
                      <span style={{ fontWeight: 500, color: '#334155' }}>
                        {item.owner || 'Unassigned'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
