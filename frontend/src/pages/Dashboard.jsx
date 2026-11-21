import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, Legend } from 'recharts';
import { api } from '../api';
import { Badge } from '../components/Badge';
import { Loading, ErrorBanner } from '../components/Loading';

export const moneyINR = (n) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(Number(n) || 0);

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = () => {
    setLoading(true);
    api('/dashboard')
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <Loading message="Loading financial intelligence overview…" />;
  if (error) return <ErrorBanner error={error} retry={loadData} />;
  if (!data) return null;

  const riskPie = Object.entries(data.risk_distribution || {}).map(([name, value]) => ({ name, value }));
  const riskColors = {
    Low: '#10b981',
    Medium: '#f59e0b',
    High: '#f97316',
    Critical: '#ef4444'
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Financial Intelligence Overview</h1>
          <p className="page-desc">
            Autonomous Graph Neural Network & Typology Monitoring Platform
          </p>
        </div>
        <div>
          <button className="secondary" onClick={loadData}>Refresh Data</button>
        </div>
      </div>

      <div className="scope-banner demo-scope">
        <div className="scope-icon">💼</div>
        <div className="scope-text">
          <strong>Operational Demo Scope (100 Accounts):</strong> Reflecting live transactions and accounts stored in the application database. To explore multi-tier scale benchmarks, visit the <strong>Research Lab (100K Flagship Default)</strong>.
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Total Accounts</span>
          <span className="stat-value">{Number(data.total_accounts).toLocaleString()}</span>
          <span className="stat-subtext">Monitored graph entities</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Total Transactions</span>
          <span className="stat-value">{Number(data.total_transactions).toLocaleString()}</span>
          <span className="stat-subtext">Processed directed edges</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Total Volume</span>
          <span className="stat-value">{moneyINR(data.total_volume)}</span>
          <span className="stat-subtext">Aggregated capital flow (INR)</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Suspicious Ground Truth</span>
          <span className="stat-value" style={{ color: '#f59e0b' }}>
            {data.suspicious_accounts}
          </span>
          <span className="stat-subtext">Labeled SAR targets</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">High & Critical Risk</span>
          <span className="stat-value" style={{ color: '#ef4444' }}>
            {data.high_risk_accounts}
          </span>
          <span className="stat-subtext">
            {data.critical_risk_accounts || 0} critical priority
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Active Model Engine</span>
          <span className="stat-value" style={{ fontSize: 16, color: '#00c2b2' }}>
            {data.active_model || 'AMLNet-GCN'}
          </span>
          <span className="stat-subtext">Versioned checkpoint</span>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Risk Level Distribution</h2>
              <span className="panel-subtitle">Accounts stratified across calibrated risk tiers</span>
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskPie} dataKey="value" nameKey="name" outerRadius={95} innerRadius={50}>
                  {riskPie.map((entry) => (
                    <Cell key={entry.name} fill={riskColors[entry.name] || '#64748b'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#091526', borderColor: '#173256', color: '#fff' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Recent Suspicious Activity Signals</h2>
              <span className="panel-subtitle">Rule-based detection & graph topological patterns</span>
            </div>
          </div>
          <div className="table-container" style={{ maxHeight: 280 }}>
            <table>
              <thead>
                <tr>
                  <th>Pattern</th>
                  <th>Risk</th>
                  <th>Amount</th>
                  <th>Accounts</th>
                </tr>
              </thead>
              <tbody>
                {(data.recent_alerts || []).map((alert) => (
                  <tr key={alert.id}>
                    <td>
                      <b style={{ color: '#00c2b2' }}>{alert.pattern_type.replace('_', ' ').toUpperCase()}</b>
                    </td>
                    <td>
                      <Badge level={alert.risk_level} />
                    </td>
                    <td className="mono">{moneyINR(alert.amount)}</td>
                    <td className="mono" style={{ fontSize: 11 }}>
                      {alert.account_ids.slice(0, 3).join(', ')}
                      {alert.account_ids.length > 3 && ` +${alert.account_ids.length - 3}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
