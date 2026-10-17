import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { Network, ZoomIn, ZoomOut, Maximize2, Info, Filter } from 'lucide-react';
import { fetchGraph } from '../services/api';

const NODE_COLORS = {
  Script: '#ef4444', // Red for Scripts (as requested)
  Client: '#8b5cf6', // Violet
  Site: '#2563eb',   // Blue
  Page: '#0891b2',   // Cyan
  Domain: '#64748b', // Slate
  Developer: '#16a34a', // Green
  default: '#94a3b8',
};

export default function GraphView() {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      setLoading(true);
      const data = await fetchGraph();
      if (mounted) {
        setGraphData(data);
        setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, []);

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    const nodes = (graphData.nodes || []).map((n) => {
      const label = n.label || 'Node';
      const color = NODE_COLORS[label] || NODE_COLORS.default;
      return {
        data: {
          id: String(n.id),
          label: n.name || n.id,
          type: label,
          color: color,
        },
      };
    });

    const edges = (graphData.edges || []).map((e, idx) => ({
      data: {
        id: `e-${idx}`,
        source: String(e.from),
        target: String(e.to),
        label: e.type || '',
      },
    }));

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#0f172a',
            'font-family': 'Inter, sans-serif',
            'font-size': '11px',
            'font-weight': 600,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'width': 28,
            'height': 28,
            'border-width': 2,
            'border-color': '#ffffff',
            'shadow-blur': 6,
            'shadow-color': 'rgba(0,0,0,0.15)',
            'shadow-opacity': 0.8,
          },
        },
        {
          selector: 'node[type = "Script"]',
          style: {
            'width': 34,
            'height': 34,
            'border-width': 3,
            'border-color': '#fee2e2',
            'font-weight': 700,
            'color': '#b91c1c',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            'label': 'data(label)',
            'font-size': '9px',
            'color': '#64748b',
            'font-family': 'monospace',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        {
          selector: 'edge[label = "LOADS"]',
          style: {
            'line-color': '#f87171',
            'target-arrow-color': '#ef4444',
            'width': 2,
            'color': '#dc2626',
            'font-weight': 600,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#0f172a',
            'line-color': '#2563eb',
            'target-arrow-color': '#2563eb',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: false,
        componentSpacing: 60,
        nodeOverlap: 20,
        idealEdgeLength: 70,
      },
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedNode({
        id: node.id(),
        label: node.data('type'),
        name: node.data('label'),
      });
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;
  }, [graphData]);

  // Handle zoom / fit
  const handleZoomIn = () => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current && cyRef.current.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current && cyRef.current.fit(null, 30);

  // Filter
  const handleFilter = (type) => {
    setFilterType(type);
    if (!cyRef.current) return;
    if (type === 'ALL') {
      cyRef.current.elements().show();
    } else {
      cyRef.current.elements().hide();
      const matched = cyRef.current.nodes(`[type = "${type}"]`);
      matched.show();
      matched.connectedEdges().show();
      matched.neighborhood().show();
    }
  };

  return (
    <div className="graph-view-section">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Network size={18} color="#2563eb" />
            <span>FalkorDB Knowledge Graph Map</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginRight: '12px' }}>
              <Filter size={14} color="#64748b" />
              <select
                value={filterType}
                onChange={(e) => handleFilter(e.target.value)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '12px',
                  outline: 'none',
                }}
              >
                <option value="ALL">Show All Nodes</option>
                <option value="Script">Scripts Only (Red)</option>
                <option value="Site">Sites Only</option>
                <option value="Page">Pages Only</option>
                <option value="Domain">Domains Only</option>
              </select>
            </div>

            <button className="btn btn-outline" style={{ padding: '4px 8px' }} onClick={handleZoomIn} title="Zoom In">
              <ZoomIn size={14} />
            </button>
            <button className="btn btn-outline" style={{ padding: '4px 8px' }} onClick={handleZoomOut} title="Zoom Out">
              <ZoomOut size={14} />
            </button>
            <button className="btn btn-outline" style={{ padding: '4px 8px' }} onClick={handleFit} title="Fit to Screen">
              <Maximize2 size={14} />
            </button>
          </div>
        </div>

        <div className="card-body" style={{ padding: '16px' }}>
          {/* Legend */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginBottom: '14px', fontSize: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444' }}></span>
              <strong style={{ color: '#ef4444' }}>Script (Security Focus)</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#2563eb' }}></span>
              <span>Site</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#0891b2' }}></span>
              <span>Page</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#8b5cf6' }}></span>
              <span>Client</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#64748b' }}></span>
              <span>Domain</span>
            </div>
          </div>

          {/* Cytoscape Container */}
          <div className="graph-container" ref={containerRef}>
            {loading && (
              <div style={{ position: 'absolute', top: '45%', left: '42%', color: '#64748b' }}>
                Rendering graph nodes...
              </div>
            )}
          </div>

          {/* Selected Node Details Drawer */}
          {selectedNode && (
            <div style={{ marginTop: '14px', background: '#f8fafc', padding: '12px 16px', borderRadius: '6px', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Info size={16} color="#2563eb" />
                <span style={{ fontSize: '13px' }}>
                  Selected <strong>{selectedNode.label}</strong>: <code style={{ background: '#e2e8f0', padding: '2px 6px', borderRadius: 4 }}>{selectedNode.name}</code> (ID: {selectedNode.id})
                </span>
              </div>
              <button className="btn btn-outline" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => setSelectedNode(null)}>
                Dismiss
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
