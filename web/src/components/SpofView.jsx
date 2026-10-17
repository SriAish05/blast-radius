import React, { useEffect, useState } from 'react';
import { Layers, AlertOctagon, ExternalLink, ShieldCheck, RefreshCw, Search } from 'lucide-react';
import { fetchSpof } from '../services/api';

export default function SpofView() {
  const [spofList, setSpofList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    setLoading(true);
    const data = await fetchSpof();
    setSpofList(data || []);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = spofList.filter((item) =>
    (item.domain || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const maxSites = Math.max(...spofList.map((s) => s.sites_reached || 1), 1);

  return (
    <div className="spof-section">
      {/* Top Banner Metric Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '24px' }}>
        <div className="card" style={{ marginBottom: 0, padding: '20px' }}>
          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
            Shared 3rd-Party Domains
          </span>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
            {spofList.length}
          </div>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
            External domains loaded across client perimeter
          </p>
        </div>

        <div className="card" style={{ marginBottom: 0, padding: '20px' }}>
          <span style={{ fontSize: '12px', color: '#dc2626', fontWeight: 600, textTransform: 'uppercase' }}>
            Top Single Point of Failure
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#dc2626', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {spofList[0]?.domain || 'None detected'}
          </div>
          <p style={{ fontSize: '12px', color: '#b91c1c', marginTop: '4px' }}>
            Reaches {spofList[0]?.sites_reached || 0} client websites simultaneously
          </p>
        </div>

        <div className="card" style={{ marginBottom: 0, padding: '20px' }}>
          <span style={{ fontSize: '12px', color: '#2563eb', fontWeight: 600, textTransform: 'uppercase' }}>
            Perimeter Security Posture
          </span>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#2563eb', marginTop: '4px' }}>
            SRI / CSP Required
          </div>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
            Subresource integrity pins mitigate supply chain drift
          </p>
        </div>
      </div>

      {/* Main SPOF Table Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <AlertOctagon size={18} color="#f59e0b" />
            <span>Single Points of Failure (SPOF) Analysis</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ position: 'relative', width: '220px' }}>
              <input
                type="text"
                placeholder="Search domain..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px 6px 30px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '12px',
                  outline: 'none',
                }}
              />
              <Search size={14} color="#94a3b8" style={{ position: 'absolute', left: 9, top: 9 }} />
            </div>

            <button className="btn btn-outline" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={loadData} title="Refresh SPOF List">
              <RefreshCw size={13} /> Refresh
            </button>
          </div>
        </div>

        <div className="table-container">
          {loading ? (
            <div style={{ padding: '24px', color: '#64748b' }}>Calculating single points of failure...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '60px' }}>Rank</th>
                  <th>Third-Party Domain</th>
                  <th style={{ width: '250px' }}>Sites Reached & Blast Radius</th>
                  <th>Risk Classification</th>
                  <th>Recommended Hardening</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, index) => {
                  const percentage = Math.round(((item.sites_reached || 1) / maxSites) * 100);
                  const isCritical = (item.sites_reached || 0) >= 3;
                  const isElevated = (item.sites_reached || 0) === 2;

                  return (
                    <tr key={index}>
                      <td>
                        <span
                          style={{
                            background: index === 0 ? '#fee2e2' : '#f1f5f9',
                            color: index === 0 ? '#b91c1c' : '#475569',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '12px',
                          }}
                        >
                          #{index + 1}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
                            {item.domain}
                          </span>
                          <a
                            href={`https://${item.domain}`}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: '#94a3b8' }}
                            title={`Inspect ${item.domain}`}
                          >
                            <ExternalLink size={12} />
                          </a>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600 }}>
                          <span>{item.sites_reached} client site{item.sites_reached === 1 ? '' : 's'}</span>
                          <span style={{ color: '#64748b' }}>{percentage}%</span>
                        </div>
                        <div className="spof-bar">
                          <div
                            className="spof-bar-fill"
                            style={{
                              width: `${percentage}%`,
                              background: isCritical
                                ? 'linear-gradient(90deg, #f87171, #dc2626)'
                                : isElevated
                                ? 'linear-gradient(90deg, #fbbf24, #f59e0b)'
                                : '#94a3b8',
                            }}
                          />
                        </div>
                      </td>
                      <td>
                        {isCritical ? (
                          <span className="badge-runtime-only" style={{ background: '#fef2f2', color: '#991b1b', borderColor: '#fca5a5' }}>
                            CRITICAL SPOF
                          </span>
                        ) : isElevated ? (
                          <span className="badge-runtime-only" style={{ background: '#fffbeb', color: '#b45309', borderColor: '#fde68a' }}>
                            ELEVATED RISK
                          </span>
                        ) : (
                          <span className="badge-html-direct">
                            ISOLATED
                          </span>
                        )}
                      </td>
                      <td>
                        <span style={{ fontSize: '12px', color: '#334155' }}>
                          {isCritical
                            ? 'Enforce Subresource Integrity (SRI) & strict CSP whitelist'
                            : 'Monitor hash changes with script watcher daemon'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
