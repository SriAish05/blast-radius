import React, { useState } from 'react';
import { Wrench, CheckCircle, ShieldCheck, MessageSquare, AlertTriangle, Copy, Check } from 'lucide-react';
import { approveIncident } from '../services/api';

export default function FixPanel({ incident, onIncidentUpdated }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [approvalResult, setApprovalResult] = useState(null);
  const [copiedMsg, setCopiedMsg] = useState(false);
  const [copiedCsp, setCopiedCsp] = useState(false);

  if (!incident || !incident.fix) {
    return null;
  }

  const { id, fix, message, affected = [], status } = incident;
  const isApproved = status === 'approved' || approvalResult !== null;

  // Compute number of unique sites
  const uniqueSites = Array.from(new Set(affected.map((a) => a.site || a.client)));
  const sitesCount = uniqueSites.length || (fix.sites ? fix.sites.length : 3);

  const handleApprove = async () => {
    setIsApproving(true);
    const res = await approveIncident(id);
    setApprovalResult(res);
    setIsApproving(false);
    setShowConfirm(false);
    if (onIncidentUpdated) {
      onIncidentUpdated({ ...incident, status: 'approved' });
    }
  };

  const handleCopyMessage = () => {
    if (message) {
      navigator.clipboard.writeText(message);
      setCopiedMsg(true);
      setTimeout(() => setCopiedMsg(false), 2000);
    }
  };

  const handleCopyCsp = () => {
    if (fix.csp) {
      navigator.clipboard.writeText(fix.csp);
      setCopiedCsp(true);
      setTimeout(() => setCopiedCsp(false), 2000);
    }
  };

  // Render patch diff line by line
  const renderPatchDiff = (patchText) => {
    if (!patchText) return <div>No patch generated.</div>;
    const lines = patchText.split('\n');

    return (
      <div className="code-diff">
        {lines.map((line, i) => {
          if (line.startsWith('-')) {
            return <span key={i} className="diff-line-delete">{line}</span>;
          }
          if (line.startsWith('+')) {
            return <span key={i} className="diff-line-add">{line}</span>;
          }
          return <span key={i} style={{ display: 'block', padding: '2px 4px' }}>{line}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="card" style={{ marginTop: '24px' }}>
      <div className="card-header">
        <div className="card-title">
          <Wrench size={18} color="#16a34a" />
          <span>Automated Fix & Client Remediation</span>
        </div>
        <div>
          {isApproved ? (
            <span className="btn btn-success" style={{ cursor: 'default' }}>
              <CheckCircle size={15} /> Approved & Pinned
            </span>
          ) : (
            <button
              className="btn btn-success"
              onClick={() => setShowConfirm(true)}
              disabled={isApproving}
            >
              <ShieldCheck size={16} /> Approve & Apply Fix
            </button>
          )}
        </div>
      </div>

      <div className="card-body">
        {/* In-page confirmation banner */}
        {showConfirm && (
          <div className="confirm-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <AlertTriangle size={20} color="#d97706" />
              <div>
                <strong style={{ color: '#92400e' }}>
                  Apply fix to {sitesCount} site{sitesCount === 1 ? '' : 's'}?
                </strong>
                <p style={{ fontSize: '13px', color: '#b45309', marginTop: '2px' }}>
                  This will dispatch automated SRI subresource integrity patches and update client CSP headers.
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn btn-outline"
                onClick={() => setShowConfirm(false)}
                disabled={isApproving}
              >
                Cancel
              </button>
              <button
                className="btn btn-success"
                onClick={handleApprove}
                disabled={isApproving}
              >
                {isApproving ? 'Applying...' : `Confirm: Apply to ${sitesCount} Sites`}
              </button>
            </div>
          </div>
        )}

        {/* Approval Result Banner */}
        {approvalResult && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '14px 18px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#166534', fontWeight: 600 }}>
              <CheckCircle size={16} /> Fix successfully approved and dispatched!
            </div>
            <p style={{ fontSize: '13px', color: '#15803d', marginTop: '4px' }}>
              {approvalResult.note || 'Approval recorded. Pull requests and hash locks initiated across sites.'}
            </p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: showConfirm || approvalResult ? '20px' : '0' }}>
          {/* Left Column: Code Patch Diff */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155' }}>
                Code Patch (SRI Pinning Diff)
              </span>
              {fix.sri && (
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#64748b' }}>
                  SRI: {fix.sri.slice(0, 16)}...
                </span>
              )}
            </div>
            {renderPatchDiff(fix.patch)}
          </div>

          {/* Right Column: CSP Header & Client Message */}
          <div>
            {/* CSP Lines */}
            <div style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155' }}>
                  Recommended Content-Security-Policy (CSP)
                </span>
                <button
                  onClick={handleCopyCsp}
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '11px', height: '22px' }}
                >
                  {copiedCsp ? <Check size={11} color="#16a34a" /> : <Copy size={11} />}
                  {copiedCsp ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="cypher-box" style={{ background: '#f1f5f9', color: '#0f172a', border: '1px solid #cbd5e1', fontSize: '11px' }}>
                <code>{fix.csp || 'No CSP directive available.'}</code>
              </pre>
            </div>

            {/* Client Communication Message */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <MessageSquare size={14} color="#2563eb" /> Client Incident Communication
                </span>
                <button
                  onClick={handleCopyMessage}
                  className="btn btn-outline"
                  style={{ padding: '2px 8px', fontSize: '11px', height: '22px' }}
                >
                  {copiedMsg ? <Check size={11} color="#16a34a" /> : <Copy size={11} />}
                  {copiedMsg ? 'Copied' : 'Copy'}
                </button>
              </div>
              <div className="client-message-box">
                "{message || 'A security alert has been registered for your third-party scripts.'}"
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
