import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Badge } from '../components/Badge';
import { Loading, ErrorBanner } from '../components/Loading';
import { moneyINR } from './Dashboard';
import { useResearch } from '../context/ResearchContext';

export default function Alerts() {
  const navigate = useNavigate();
  const { selectedTier } = useResearch();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [patternFilter, setPatternFilter] = useState('');

  const loadAlerts = () => {
    setLoading(true);
    const params = new URLSearchParams({ tier: selectedTier });
    if (patternFilter) params.append('pattern_type', patternFilter);
    api(`/alerts?${params.toString()}`)
      .then((res) => {
        setAlerts(res.items || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadAlerts();
  }, [patternFilter, selectedTier]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Suspicious Activity Signals</h1>
          <p className="page-desc">
            Rule-based and graph topological alert indicators identified across transaction sequences · Tier {selectedTier}
          </p>
        </div>
      </div>

      <div className="toolbar">
        <select value={patternFilter} onChange={(e) => setPatternFilter(e.target.value)}>
          <option value="">All Pattern Typologies</option>
          <option value="circular">Circular Flow (Cycles)</option>
          <option value="rapid">Rapid Outgoing Sequences</option>
          <option value="fan_in">Fan-In (Concentration)</option>
          <option value="fan_out">Fan-Out (Dispersal)</option>
        </select>
        <span style={{ fontSize: 12, color: '#96adcc', marginLeft: 'auto' }}>
          {alerts.length} alerts detected
        </span>
      </div>

      {error && <ErrorBanner error={error} retry={loadAlerts} />}

      {loading ? (
        <Loading message="Compiling suspicious signals…" />
      ) : (
        <div className="panel">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Alert ID</th>
                  <th>Typology</th>
                  <th>Risk Tier</th>
                  <th>Amount</th>
                  <th>Involved Accounts</th>
                  <th>Explanation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alt) => (
                  <tr key={alt.id}>
                    <td className="mono" style={{ fontWeight: 600 }}>{alt.id}</td>
                    <td>
                      <b style={{ color: '#00c2b2' }}>
                        {alt.pattern_type.replace('_', ' ').toUpperCase()}
                      </b>
                    </td>
                    <td>
                      <Badge level={alt.risk_level} />
                    </td>
                    <td className="mono" style={{ color: '#00c2b2', fontWeight: 600 }}>
                      {moneyINR(alt.amount)}
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>
                      {alt.account_ids.join(', ')}
                    </td>
                    <td style={{ fontSize: 12, color: '#cbd5e1' }}>
                      {alt.explanation}
                    </td>
                    <td>
                      <button
                        className="secondary"
                        style={{ padding: '4px 8px', fontSize: 11 }}
                        onClick={() => navigate(`/graph?account=${alt.account_ids[0]}`)}
                      >
                        Inspect Ego-Net
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
