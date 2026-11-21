import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Badge } from '../components/Badge';
import { Loading, ErrorBanner } from '../components/Loading';
import { moneyINR } from './Dashboard';

export default function Accounts() {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [page, setPage] = useState(1);

  const [selectedAccount, setSelectedAccount] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [explaining, setExplaining] = useState(false);
  const [accountTx, setAccountTx] = useState([]);

  const loadAccounts = () => {
    setLoading(true);
    const params = new URLSearchParams({
      search,
      page: page.toString(),
      page_size: '25'
    });
    if (riskFilter) params.append('risk_level', riskFilter);

    api(`/accounts?${params.toString()}`)
      .then((res) => {
        setAccounts(res.items);
        setTotal(res.total);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadAccounts();
  }, [search, riskFilter, page]);

  const selectAccount = (acc) => {
    setSelectedAccount(acc);
    setExplaining(true);
    setExplanation(null);
    setAccountTx([]);

    // Fetch transactions & explanation in parallel
    Promise.all([
      api(`/accounts/${acc.id}/transactions`),
      api(`/explain/${acc.id}`)
    ])
      .then(([txRes, explainRes]) => {
        setAccountTx(txRes.items || []);
        setExplanation(explainRes);
        setExplaining(false);
      })
      .catch((err) => {
        console.error('Account detail load error:', err);
        setExplaining(false);
      });
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Account Investigation</h1>
          <p className="page-desc">
            Inspect entity risk profiles, GNN predictions, and Explainable AI breakdowns
          </p>
        </div>
      </div>

      <div className="scope-banner demo-scope">
        <div className="scope-icon">👤</div>
        <div className="scope-text">
          <strong>Operational Scope (100 Accounts):</strong> Entities shown below represent the application database.
          High-scale research datasets (100K flagship default, 1M, etc.) are managed in the <strong>Research Lab</strong>.
        </div>
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Search Account ID (e.g. S001, N012)..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          value={riskFilter}
          onChange={(e) => {
            setRiskFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Risk Tiers</option>
          <option value="Critical">Critical (≥80)</option>
          <option value="High">High (60-79)</option>
          <option value="Medium">Medium (30-59)</option>
          <option value="Low">Low (&lt;30)</option>
        </select>
        <span style={{ fontSize: 12, color: '#96adcc', marginLeft: 'auto' }}>
          Showing {accounts.length} of {total} accounts
        </span>
      </div>

      {error && <ErrorBanner error={error} retry={loadAccounts} />}

      <div className="split-layout">
        {/* Accounts Table */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Accounts List</h2>
          </div>
          {loading ? (
            <Loading message="Filtering accounts…" />
          ) : (
            <div className="table-container" style={{ maxHeight: 600 }}>
              <table>
                <thead>
                  <tr>
                    <th>Account ID</th>
                    <th>GNN Prob</th>
                    <th>Rule Score</th>
                    <th>Final Risk</th>
                    <th>Tier</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((acc) => (
                    <tr
                      key={acc.id}
                      className={selectedAccount?.id === acc.id ? 'selected' : ''}
                      onClick={() => selectAccount(acc)}
                    >
                      <td className="mono" style={{ fontWeight: 600 }}>{acc.id}</td>
                      <td className="mono">{(acc.gnn_probability * 100).toFixed(1)}%</td>
                      <td className="mono">{acc.rule_score}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        {Number(acc.final_risk).toFixed(1)}
                      </td>
                      <td>
                        <Badge level={acc.risk_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Account Investigation Details */}
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Entity Dossier & Explainable AI</h2>
            {selectedAccount && (
              <button
                className="secondary"
                onClick={() => navigate(`/graph?account=${selectedAccount.id}`)}
              >
                Inspect in Graph
              </button>
            )}
          </div>

          {!selectedAccount ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#5f7a9d' }}>
              Select an account row on the left to inspect its risk dossier, GNN neighborhood attribution,
              and related transaction signals.
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontSize: 18, color: '#fff' }} className="mono">
                    {selectedAccount.id}
                  </h3>
                  <span style={{ fontSize: 12, color: '#96adcc' }}>
                    Type: {selectedAccount.account_type || 'Retail/Commercial'}
                  </span>
                </div>
                <Badge level={selectedAccount.risk_level} />
              </div>

              {/* Risk Attribution Summary */}
              <div className="grid-3" style={{ marginBottom: 16 }}>
                <div className="stat-card" style={{ padding: 12 }}>
                  <span className="stat-label">GNN Probability</span>
                  <span className="stat-value" style={{ fontSize: 18, color: '#00c2b2' }}>
                    {(selectedAccount.gnn_probability * 100).toFixed(1)}%
                  </span>
                  <span className="stat-subtext">Weight factor: 70%</span>
                </div>
                <div className="stat-card" style={{ padding: 12 }}>
                  <span className="stat-label">Rule Score</span>
                  <span className="stat-value" style={{ fontSize: 18, color: '#f59e0b' }}>
                    {selectedAccount.rule_score} / 100
                  </span>
                  <span className="stat-subtext">Weight factor: 30%</span>
                </div>
                <div className="stat-card" style={{ padding: 12 }}>
                  <span className="stat-label">Calibrated Risk</span>
                  <span className="stat-value" style={{ fontSize: 18, color: '#ef4444' }}>
                    {Number(selectedAccount.final_risk).toFixed(1)}
                  </span>
                  <span className="stat-subtext">Composite score</span>
                </div>
              </div>

              {/* Explainable AI Signals */}
              {explaining ? (
                <Loading message="Synthesizing explainability attribution…" />
              ) : explanation ? (
                <div>
                  <h4 style={{ fontSize: 13, marginBottom: 10, color: '#e6f0fd' }}>
                    Explainable AI (XAI) Attribution Breakdown
                  </h4>

                  {/* Rule Evidence */}
                  {(explanation.rule_evidence || []).map((rule, idx) => (
                    <div key={idx} className="explain-card" style={{ borderLeft: '3px solid #ef4444' }}>
                      <div className="explain-title">
                        <span style={{ color: '#fca5a5' }}>Typology Rule: {rule.typology}</span>
                        <Badge level={rule.risk_level} />
                      </div>
                      <p style={{ fontSize: 12, color: '#cbd5e1' }}>{rule.explanation}</p>
                      <div className="explain-caveat">
                        Involves {rule.transaction_count} transactions totalling {moneyINR(rule.amount)}
                      </div>
                    </div>
                  ))}

                  {/* Correlated Features */}
                  {(explanation.correlated_features || []).map((feat, idx) => (
                    <div key={idx} className="explain-card" style={{ borderLeft: '3px solid #00c2b2' }}>
                      <div className="explain-title">
                        <span>Topological Signal: {feat.feature.replaceAll('_', ' ').toUpperCase()}</span>
                        <span style={{ fontSize: 11, color: '#00c2b2' }}>{feat.weight}</span>
                      </div>
                      <p style={{ fontSize: 12, color: '#cbd5e1' }}>{feat.observation}</p>
                      <div className="explain-caveat">{feat.caveat}</div>
                    </div>
                  ))}

                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 12, fontStyle: 'italic' }}>
                    {explanation.methodology_disclaimer}
                  </div>
                </div>
              ) : null}

              {/* Transaction Activity */}
              <div style={{ marginTop: 24 }}>
                <h4 style={{ fontSize: 13, marginBottom: 10, color: '#e6f0fd' }}>
                  Associated Transactions ({accountTx.length})
                </h4>
                <div className="table-container" style={{ maxHeight: 220 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Tx ID</th>
                        <th>Direction</th>
                        <th>Amount</th>
                        <th>Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {accountTx.map((tx) => (
                        <tr key={tx.id}>
                          <td className="mono">{tx.id}</td>
                          <td className="mono">
                            {tx.source_id === selectedAccount.id
                              ? `Out → ${tx.target_id}`
                              : `In ← ${tx.source_id}`}
                          </td>
                          <td className="mono">{moneyINR(tx.amount)}</td>
                          <td>{tx.scenario || tx.transaction_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
