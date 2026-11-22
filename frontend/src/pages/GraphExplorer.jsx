import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import cytoscape from 'cytoscape';
import { api } from '../api';
import { Badge } from '../components/Badge';
import { Loading, ErrorBanner } from '../components/Loading';
import { moneyINR } from './Dashboard';
import { useResearch } from '../context/ResearchContext';

export default function GraphExplorer() {
  const { selectedTier } = useResearch();
  const [searchParams] = useSearchParams();
  const initialAccount = searchParams.get('account') || '';

  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [searchQuery, setSearchQuery] = useState(initialAccount);
  const [riskFilter, setRiskFilter] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [isNeighborhood, setIsNeighborhood] = useState(false);

  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const loadFullGraph = () => {
    setLoading(true);
    setIsNeighborhood(false);
    const params = new URLSearchParams({ tier: selectedTier, limit: '80' });
    if (riskFilter) params.append('risk_level', riskFilter);

    api(`/graph?${params.toString()}`)
      .then((res) => {
        setGraphData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  const loadNeighborhood = (accountId) => {
    if (!accountId) return;
    setLoading(true);
    setIsNeighborhood(true);
    api(`/graph/subgraph?tier=${selectedTier}&account_id=${encodeURIComponent(accountId)}&hops=1&limit=80`)
      .then((res) => {
        setGraphData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    if (initialAccount) {
      loadNeighborhood(initialAccount);
    } else {
      loadFullGraph();
    }
  }, [riskFilter, selectedTier]);

  // Initialize Cytoscape
  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements = [...(graphData.nodes || []), ...(graphData.edges || [])];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-size': 9,
            'font-weight': '600',
            color: '#cbd5e1',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-background-opacity': 0.8,
            'text-background-color': '#0b1120',
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
            'background-color': (ele) => {
              if (ele.data('is_root')) return '#38bdf8';
              const r = ele.data('risk_level');
              if (r === 'Critical') return '#ef4444';
              if (r === 'High') return '#f97316';
              if (r === 'Medium') return '#f59e0b';
              return '#10b981';
            },
            width: (ele) => (ele.data('is_root') ? 34 : 20 + Math.min(18, (ele.data('risk') || 0.1) * 20)),
            height: (ele) => (ele.data('is_root') ? 34 : 20 + Math.min(18, (ele.data('risk') || 0.1) * 20)),
            'border-width': (ele) => (ele.data('is_root') ? 3 : 1.5),
            'border-color': (ele) => (ele.data('is_root') ? '#ffffff' : '#1e293b'),
            'shadow-blur': (ele) => (ele.data('risk_level') === 'Critical' ? 12 : 0),
            'shadow-color': 'rgba(239, 68, 68, 0.5)',
            'shadow-opacity': 0.8
          }
        },
        {
          selector: 'edge',
          style: {
            width: (ele) => Math.max(1.8, Math.min(6, (ele.data('amount') || 1000) / 4000)),
            'line-color': (ele) => (ele.data('is_fraud') ? '#ef4444' : '#475569'),
            'target-arrow-color': (ele) => (ele.data('is_fraud') ? '#ef4444' : '#00c2b2'),
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.15,
            'curve-style': 'bezier',
            opacity: 0.75
          }
        },
        {
          selector: 'edge[?is_fraud]',
          style: {
            'line-color': '#ef4444',
            'target-arrow-color': '#ef4444',
            width: 3.5,
            opacity: 0.95,
            'z-index': 10
          }
        },
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#38bdf8',
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            opacity: 1
          }
        }
      ],
      layout: {
        name: isNeighborhood ? 'concentric' : 'cose',
        animate: true,
        animationDuration: 400,
        nodeRepulsion: 12000,
        idealEdgeLength: 110,
        edgeElasticity: 100,
        gravity: 0.35,
        numIter: 350,
        padding: 40
      }
    });

    cy.on('tap', 'node', (evt) => {
      setSelectedNode(evt.target.data());
      setSelectedEdge(null);
    });

    cy.on('tap', 'edge', (evt) => {
      setSelectedEdge(evt.target.data());
      setSelectedNode(null);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData]);

  // Highlight search matches
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    if (!searchQuery) {
      cy.elements().style('opacity', 1);
      return;
    }
    const q = searchQuery.toLowerCase();
    cy.nodes().forEach((n) => {
      const match = n.data('id').toLowerCase().includes(q);
      n.style('opacity', match ? 1 : 0.15);
    });
  }, [searchQuery]);

  const fitView = () => cyRef.current?.fit();
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const resetLayout = () => {
    cyRef.current?.layout({ name: 'cose', animate: true, animationDuration: 400 }).run();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Graph Explorer</h1>
          <p className="page-desc">
            Interactive directed network visualization with multi-hop ego-neighborhood expansion · Tier {selectedTier}
          </p>
        </div>
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Search Account ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          className="secondary"
          onClick={() => loadNeighborhood(searchQuery)}
          disabled={!searchQuery}
        >
          Expand Neighborhood (1-Hop)
        </button>
        {isNeighborhood && (
          <button className="secondary" onClick={loadFullGraph}>
            Show Full Network
          </button>
        )}
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          disabled={isNeighborhood}
        >
          <option value="">All Risk Tiers</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>

      <div className="graph-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ background: '#10b981' }} />
          <span>Low Risk (&lt;30)</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: '#f59e0b' }} />
          <span>Medium Risk (30-59)</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: '#f97316' }} />
          <span>High Risk (60-79)</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: '#ef4444' }} />
          <span>Critical (≥80)</span>
        </div>
        <div className="legend-item">
          <span style={{ color: '#00c2b2' }}>→</span>
          <span>Arrows indicate capital flow direction</span>
        </div>
      </div>

      {error && <ErrorBanner error={error} retry={loadFullGraph} />}

      <div style={{ position: 'relative', marginTop: 12 }}>
        {loading && <Loading message="Rendering graph topology…" />}

        <div className="graph-viewport" ref={containerRef}>
          <div className="graph-hud">
            <button className="secondary" style={{ padding: '4px 8px' }} onClick={zoomIn}>➕</button>
            <button className="secondary" style={{ padding: '4px 8px' }} onClick={zoomOut}>➖</button>
            <button className="secondary" style={{ padding: '4px 8px' }} onClick={fitView}>Fit</button>
            <button className="secondary" style={{ padding: '4px 8px' }} onClick={resetLayout}>Reset</button>
          </div>
        </div>
      </div>

      {/* Selected Entity / Edge Inspector Panel */}
      {selectedNode && (
        <div className="panel" style={{ marginTop: 18 }}>
          <div className="panel-header">
            <h2 className="panel-title">Inspected Account Node: {selectedNode.id}</h2>
            <button className="secondary" onClick={() => loadNeighborhood(selectedNode.id)}>
              Expand This Ego-Net
            </button>
          </div>
          <div className="grid-3">
            <div className="stat-card">
              <span className="stat-label">Composite Risk</span>
              <span className="stat-value" style={{ color: '#ef4444' }}>
                {Number(selectedNode.risk || 0).toFixed(1)}
              </span>
              <span className="stat-subtext"><Badge level={selectedNode.risk_level} /></span>
            </div>
            <div className="stat-card">
              <span className="stat-label">GNN Probability</span>
              <span className="stat-value" style={{ color: '#00c2b2' }}>
                {selectedNode.gnn_prob || 0}%
              </span>
              <span className="stat-subtext">Graph representation confidence</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Rule Score</span>
              <span className="stat-value" style={{ color: '#f59e0b' }}>
                {selectedNode.rule_score || 0}
              </span>
              <span className="stat-subtext">Pattern heuristic points</span>
            </div>
          </div>
        </div>
      )}

      {selectedEdge && (
        <div className="panel" style={{ marginTop: 18 }}>
          <div className="panel-header">
            <h2 className="panel-title">Inspected Transaction Edge</h2>
          </div>
          <p className="mono" style={{ fontSize: 14 }}>
            <b>{selectedEdge.source}</b> → <b>{selectedEdge.target}</b>
          </p>
          <p style={{ marginTop: 8 }}>
            Amount: <b style={{ color: '#00c2b2' }}>{moneyINR(selectedEdge.amount)}</b> | Scenario: <b>{selectedEdge.scenario || 'normal'}</b>
          </p>
        </div>
      )}
    </div>
  );
}
