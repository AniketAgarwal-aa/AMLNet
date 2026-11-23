import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Loading, ErrorBanner } from '../components/Loading';
import { moneyINR } from './Dashboard';
import { useResearch } from '../context/ResearchContext';

export default function Transactions() {
  const navigate = useNavigate();
  const { selectedTier, formatTime } = useResearch();
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [accountFilter, setAccountFilter] = useState('');
  const [minAmount, setMinAmount] = useState('');
  const [scenarioFilter, setScenarioFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedTx, setSelectedTx] = useState(null);

  const loadTransactions = () => {
    setLoading(true);
    const params = new URLSearchParams({
      tier: selectedTier,
      account: accountFilter,
      page: page.toString(),
      page_size: '50'
    });
    if (minAmount) params.append('min_amount', minAmount);
    if (scenarioFilter) params.append('scenario', scenarioFilter);

    api(`/transactions?${params.toString()}`)
      .then((res) => {
        setTransactions(res.items || []);
        setTotal(res.total || 0);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadTransactions();
  }, [accountFilter, minAmount, scenarioFilter, page, selectedTier]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Transaction Explorer</h1>
          <p className="page-desc">
            Filter, inspect, and trace directed financial transactions across the counterparty network · Tier {selectedTier}
          </p>
        </div>
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Filter by account ID (sender or receiver)..."
          value={accountFilter}
          onChange={(e) => {
            setAccountFilter(e.target.value);
            setPage(1);
          }}
        />
        <input
          type="number"
          placeholder="Min Amount (₹)..."
          value={minAmount}
          onChange={(e) => {
            setMinAmount(e.target.value);
            setPage(1);
          }}
          style={{ width: 140 }}
        />
        <select
          value={scenarioFilter}
          onChange={(e) => {
            setScenarioFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Scenarios / Types</option>
          <option value="normal">Normal</option>
          <option value="circular">Circular Transfer</option>
          <option value="rapid">Rapid Outbound Sequence</option>
          <option value="fan_in">Fan-In Concentration</option>
          <option value="fan_out">Fan-Out Scattering</option>
        </select>
        <span style={{ fontSize: 12, color: '#96adcc', marginLeft: 'auto' }}>
          Showing {transactions.length} of {total} transactions
        </span>
      </div>

      {error && <ErrorBanner error={error} retry={loadTransactions} />}

      <div className="split-layout">
        {/* Transaction Table */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Transaction Records</h2>
          </div>
          {loading ? (
            <Loading message="Querying transactions…" />
          ) : (
            <div className="table-container" style={{ maxHeight: 600 }}>
              <table>
                <thead>
                  <tr>
                    <th>Tx ID</th>
                    <th>From → To</th>
                    <th>Amount (INR)</th>
                    <th>Timestamp</th>
                    <th>Scenario</th>
                  </tr>
                </thead>
                <tbody>
                  {(transactions || []).map((tx) => (
                    <tr
                      key={tx.id}
                      className={selectedTx?.id === tx.id ? 'selected' : ''}
                      onClick={() => setSelectedTx(tx)}
                    >
                      <td className="mono" style={{ fontWeight: 600 }}>{tx.id}</td>
                      <td className="mono">{tx.source_id} → {tx.target_id}</td>
                      <td className="mono" style={{ color: '#00c2b2', fontWeight: 600 }}>
                        {moneyINR(tx.amount)}
                      </td>
                      <td style={{ fontSize: 11, color: '#96adcc' }}>
                        {formatTime(tx.timestamp)}
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: 11,
                            color: tx.scenario !== 'normal' ? '#f59e0b' : '#94a3b8'
                          }}
                        >
                          {tx.scenario || 'normal'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Selected Transaction Detail */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Transaction Intelligence</h2>
            {selectedTx && (
              <button
                className="secondary"
                onClick={() => navigate(`/graph?account=${selectedTx.source_id}`)}
              >
                Inspect Source in Graph
              </button>
            )}
          </div>

          {!selectedTx ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#5f7a9d' }}>
              Select a transaction on the left to inspect counterparty accounts, timing attributes, and typology context.
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: 16 }}>
                <span className="stat-label">Transaction Identifier</span>
                <h3 className="mono" style={{ color: '#fff', fontSize: 18 }}>{selectedTx.id}</h3>
              </div>

              <div className="grid-2" style={{ marginBottom: 16 }}>
                <div className="stat-card" style={{ padding: 12 }}>
                  <span className="stat-label">Originating Sender</span>
                  <span className="stat-value mono" style={{ fontSize: 16, color: '#93c5fd' }}>
                    {selectedTx.source_id}
                  </span>
                  <button
                    className="secondary"
                    style={{ marginTop: 8, padding: '4px 8px', fontSize: 11 }}
                    onClick={() => navigate(`/accounts?search=${selectedTx.source_id}`)}
                  >
                    View Account
                  </button>
                </div>
                <div className="stat-card" style={{ padding: 12 }}>
                  <span className="stat-label">Beneficiary Receiver</span>
                  <span className="stat-value mono" style={{ fontSize: 16, color: '#93c5fd' }}>
                    {selectedTx.target_id}
                  </span>
                  <button
                    className="secondary"
                    style={{ marginTop: 8, padding: '4px 8px', fontSize: 11 }}
                    onClick={() => navigate(`/accounts?search=${selectedTx.target_id}`)}
                  >
                    View Account
                  </button>
                </div>
              </div>

              <div className="stat-card" style={{ marginBottom: 16 }}>
                <span className="stat-label">Transaction Amount</span>
                <span className="stat-value" style={{ color: '#00c2b2' }}>
                  {moneyINR(selectedTx.amount)}
                </span>
                <span className="stat-subtext">Denominated in Indian Rupee (INR)</span>
              </div>

              <div className="explain-card">
                <div className="explain-title">
                  <span>Typology Classification</span>
                  <span className="mono" style={{ color: selectedTx.scenario !== 'normal' ? '#f59e0b' : '#94a3b8' }}>
                    {selectedTx.scenario || 'normal'}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: '#cbd5e1' }}>
                  Recorded at {formatTime(selectedTx.timestamp)} ({selectedTx.transaction_type || 'wire_transfer'}).
                </p>
                <div className="explain-caveat">
                  Direct transfer edge in the multi-hop financial graph.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
