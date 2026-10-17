import React, { useState } from 'react';
import { Database, Clock, Table, Check, Copy } from 'lucide-react';

export default function TracePanel({ trace = [] }) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (!trace || trace.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Database size={18} color="#2563eb" />
            <span>What FalkorDB did</span>
          </div>
        </div>
        <div className="card-body" style={{ color: '#64748b', fontSize: '14px' }}>
          No graph query traces available for this incident.
        </div>
      </div>
    );
  }

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const totalTime = trace.reduce((acc, curr) => acc + (Number(curr.time_ms) || 0), 0);

  return (
    <div className="card" style={{ marginTop: '24px' }}>
      <div className="card-header">
        <div className="card-title">
          <Database size={18} color="#2563eb" />
          <span>What FalkorDB did</span>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#64748b' }}>
          <span>{trace.length} graph query step{trace.length === 1 ? '' : 's'}</span>
          <span>•</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={14} /> Total: {totalTime.toFixed(1)} ms
          </span>
        </div>
      </div>

      <div className="card-body">
        {trace.map((step, idx) => {
          const stepNum = step.step || idx + 1;
          const isCopied = copiedIndex === idx;

          return (
            <div key={idx} className="trace-step">
              <div className="trace-step-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className="step-num">Step {stepNum}</span>
                  <span className="step-tool">{step.tool || 'cypher_query'}</span>
                  {step.inputs && Object.keys(step.inputs).length > 0 && (
                    <span style={{ color: '#64748b', fontSize: '11px' }}>
                      ({Object.entries(step.inputs).map(([k, v]) => `${k}="${v}"`).join(', ')})
                    </span>
                  )}
                </div>

                <div className="step-stats">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Table size={13} /> {step.rows} row{step.rows === 1 ? '' : 's'}
                  </span>
                  <span>•</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={13} /> {step.time_ms ? `${Number(step.time_ms).toFixed(1)} ms` : '< 1 ms'}
                  </span>
                  <button
                    onClick={() => handleCopy(step.cypher, idx)}
                    className="btn btn-outline"
                    style={{ padding: '2px 8px', fontSize: '11px', height: '24px', marginLeft: '8px' }}
                    title="Copy Cypher Query"
                  >
                    {isCopied ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
                    {isCopied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              {step.cypher && (
                <pre className="cypher-box">
                  <code>{step.cypher}</code>
                </pre>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
