import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, LineChart, Line } from 'recharts';
import { api } from '../api';
import { useResearch } from '../context/ResearchContext';
import { DatasetSelector } from '../components/DatasetSelector';
import { Loading, ErrorBanner } from '../components/Loading';

export default function Performance() {
  const { selectedTier, tierExperiments, chartData, bestModel, activeTierMeta, loading: researchLoading } = useResearch();

  const [activeView, setActiveView] = useState('research'); // 'research' | 'operational'
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulatedThreshold, setSimulatedThreshold] = useState(0.5);

  const loadMetrics = () => {
    setLoading(true);
    api('/model/metrics')
      .then((res) => {
        setMetrics(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading && !metrics) return <Loading message="Evaluating model performance benchmarks…" />;
  if (error && !metrics) return <ErrorBanner error={error} retry={loadMetrics} />;

  const gcn = metrics?.gcn || {};
  const baseline = metrics?.logistic_regression || {};
  const history = metrics?.training_history || [];

  const operationalComparison = [
    { metric: 'Accuracy', GCN: gcn.accuracy, LogisticRegression: baseline.accuracy },
    { metric: 'Precision', GCN: gcn.precision, LogisticRegression: baseline.precision },
    { metric: 'Recall', GCN: gcn.recall, LogisticRegression: baseline.recall },
    { metric: 'F1-Score', GCN: gcn.f1, LogisticRegression: baseline.f1 },
  ];

  const cm = gcn.confusion_matrix || [[0, 0], [0, 0]];
  const tn = cm[0] ? cm[0][0] : 0;
  const fp = cm[0] ? cm[0][1] : 0;
  const fn = cm[1] ? cm[1][0] : 0;
  const tp = cm[1] ? cm[1][1] : 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">
            Model Performance &amp; Evaluation
          </h1>
          <p className="page-desc">
            Rigorous held-out test evaluation comparing Graph Neural Networks against non-graph baselines
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className={activeView === 'research' ? 'primary' : 'secondary'}
            onClick={() => setActiveView('research')}
          >
            Multi-Tier Benchmarks ({selectedTier})
          </button>
          <button
            className={activeView === 'operational' ? 'primary' : 'secondary'}
            onClick={() => setActiveView('operational')}
          >
            Active Model Checkpoint
          </button>
        </div>
      </div>

      {/* VIEW 1: RESEARCH BENCHMARKS (DATASET-AWARE) */}
      {activeView === 'research' && (
        <div>
          {/* Quick dataset selector */}
          <div style={{ marginBottom: 20 }}>
            <DatasetSelector compact={false} />
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Top Architecture ({selectedTier})</span>
              <span className="stat-value text-highlight" style={{ fontSize: 20 }}>
                {bestModel?.model_name ? bestModel.model_name.replace(/_/g, ' ').toUpperCase() : 'N/A'}
              </span>
              <span className="stat-subtext">Optimal Validation Calibrated</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Best Test F1-Score</span>
              <span className="stat-value" style={{ color: '#00c2b2' }}>
                {bestModel?.metrics?.f1 ? Number(bestModel.metrics.f1).toFixed(4) : 'N/A'}
              </span>
              <span className="stat-subtext">Stratified held-out test split (20%)</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">High-Recall Sensitivity</span>
              <span className="stat-value" style={{ color: '#10b981' }}>
                {bestModel?.metrics?.recall ? Number(bestModel.metrics.recall).toFixed(4) : 'N/A'}
              </span>
              <span className="stat-subtext">True SAR capture rate</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Training Duration &amp; RAM</span>
              <span className="stat-value" style={{ fontSize: 20 }}>
                {bestModel?.training_duration_seconds ? `${bestModel.training_duration_seconds.toFixed(2)}s` : 'N/A'}
              </span>
              <span className="stat-subtext">Peak RAM: {bestModel?.peak_rss_mb?.toFixed(1) || 'N/A'} MB</span>
            </div>
          </div>

          {/* Research Architecture Comparison Chart */}
          <div className="grid-2" style={{ marginTop: 20 }}>
            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">F1-Score &amp; Recall on {selectedTier}</h2>
                <span className="panel-subtitle">All 6 Evaluated Architectures</span>
              </div>
              <div className="chart-container" style={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 25 }}>
                    <XAxis dataKey="name" stroke="#94a9c9" fontSize={11} angle={-15} textAnchor="end" />
                    <YAxis domain={[0, 1]} stroke="#94a9c9" />
                    <Tooltip contentStyle={{ background: '#091526', borderColor: '#173256', color: '#fff' }} />
                    <Legend verticalAlign="top" wrapperStyle={{ paddingBottom: 10 }} />
                    <Bar dataKey="F1" fill="#00c2b2" name="F1-Score" />
                    <Bar dataKey="Recall" fill="#10b981" name="Recall" />
                    <Bar dataKey="Precision" fill="#f59e0b" name="Precision" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">PR-AUC &amp; ROC-AUC Curves</h2>
                <span className="panel-subtitle">Area Under Precision-Recall vs ROC</span>
              </div>
              <div className="chart-container" style={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 25 }}>
                    <XAxis dataKey="name" stroke="#94a9c9" fontSize={11} angle={-15} textAnchor="end" />
                    <YAxis domain={[0, 1]} stroke="#94a9c9" />
                    <Tooltip contentStyle={{ background: '#091526', borderColor: '#173256', color: '#fff' }} />
                    <Legend verticalAlign="top" wrapperStyle={{ paddingBottom: 10 }} />
                    <Bar dataKey="PR_AUC" fill="#f43f5e" name="PR-AUC" />
                    <Bar dataKey="ROC_AUC" fill="#8b5cf6" name="ROC-AUC" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Research Results Table */}
          <div className="panel" style={{ marginTop: 20 }}>
            <div className="panel-header">
              <h2 className="panel-title">6-Architecture Benchmark Leaderboard ({selectedTier})</h2>
              <span className="panel-subtitle">Empirical benchmark on holdout test splits under memory-bounded resource targets</span>
            </div>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Architecture</th>
                    <th>Accuracy</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1-Score</th>
                    <th>PR-AUC</th>
                    <th>ROC-AUC</th>
                    <th>Optimal Threshold</th>
                    <th>Duration</th>
                    <th>RAM</th>
                  </tr>
                </thead>
                <tbody>
                  {(tierExperiments || []).map((exp) => {
                    const m = exp?.metrics || {};
                    const isTop = bestModel?.id === exp.id;
                    const modelTitle = typeof exp?.model_name === 'string'
                      ? exp.model_name.replace(/_/g, ' ').toUpperCase()
                      : 'MODEL';
                    return (
                      <tr key={exp.id} className={isTop ? 'best-row' : ''}>
                        <td>
                          <strong>{modelTitle}</strong>
                          {isTop && <span className="mini-badge-top">BEST</span>}
                        </td>
                        <td>{m.accuracy !== undefined ? Number(m.accuracy).toFixed(4) : 'N/A'}</td>
                        <td>{m.precision !== undefined ? Number(m.precision).toFixed(4) : 'N/A'}</td>
                        <td>
                          <strong className={Number(m.recall) > 0.6 ? 'text-success' : ''}>
                            {m.recall !== undefined ? Number(m.recall).toFixed(4) : 'N/A'}
                          </strong>
                        </td>
                        <td>
                          <strong className="text-highlight">
                            {m.f1 !== undefined ? Number(m.f1).toFixed(4) : 'N/A'}
                          </strong>
                        </td>
                        <td>{m.pr_auc !== undefined ? Number(m.pr_auc).toFixed(4) : 'N/A'}</td>
                        <td>{m.roc_auc !== undefined ? Number(m.roc_auc).toFixed(4) : 'N/A'}</td>
                        <td className="font-mono">{m.threshold !== undefined ? Number(m.threshold).toFixed(4) : '0.5000'}</td>
                        <td>{exp.training_duration_seconds ? `${exp.training_duration_seconds.toFixed(2)}s` : 'N/A'}</td>
                        <td>{exp.peak_rss_mb ? `${exp.peak_rss_mb.toFixed(1)} MB` : 'N/A'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: OPERATIONAL ACTIVE MODEL (100 ACCOUNTS) */}
      {activeView === 'operational' && (
        <div>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">GCN Test F1-Score</span>
              <span className="stat-value" style={{ color: '#00c2b2' }}>
                {Number(gcn.f1 || 0).toFixed(4)}
              </span>
              <span className="stat-subtext">Harmonic mean of precision &amp; recall</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">GCN Test Recall</span>
              <span className="stat-value" style={{ color: '#10b981' }}>
                {Number(gcn.recall || 0).toFixed(4)}
              </span>
              <span className="stat-subtext">True positive SAR capture rate</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">GCN Test Precision</span>
              <span className="stat-value" style={{ color: '#f59e0b' }}>
                {Number(gcn.precision || 0).toFixed(4)}
              </span>
              <span className="stat-subtext">Positive predictive value</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Test Split Size</span>
              <span className="stat-value" style={{ fontSize: 20 }}>
                {metrics.split ? `${metrics.split.test} accounts` : 'Held-out'}
              </span>
              <span className="stat-subtext">Train: {metrics.split?.train} · Val: {metrics.split?.validation}</span>
            </div>
          </div>

          <div className="grid-2" style={{ marginTop: 20 }}>
            {/* Model Comparison Bar Chart */}
            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">GCN vs Baseline Logistic Regression</h2>
                <span className="panel-subtitle">Held-out validation test split</span>
              </div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={operationalComparison}>
                    <XAxis dataKey="metric" stroke="#94a9c9" />
                    <YAxis domain={[0, 1]} stroke="#94a9c9" />
                    <Tooltip contentStyle={{ background: '#091526', borderColor: '#173256', color: '#fff' }} />
                    <Legend />
                    <Bar dataKey="GCN" fill="#00c2b2" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="LogisticRegression" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Confusion Matrix */}
            <div className="panel">
              <div className="panel-header">
                <h2 className="panel-title">GCN Confusion Matrix</h2>
                <span className="panel-subtitle">Classification Breakdown</span>
              </div>
              <div style={{ padding: '16px 0' }}>
                <table className="confusion-matrix-table">
                  <thead>
                    <tr>
                      <th>Actual \ Pred</th>
                      <th>Predicted Normal</th>
                      <th>Predicted SAR</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <th>Actual Normal</th>
                      <td className="cm-cell-green">
                        <span className="cm-num">{tn}</span>
                        <span className="cm-lbl">True Negative</span>
                      </td>
                      <td className="cm-cell-red">
                        <span className="cm-num">{fp}</span>
                        <span className="cm-lbl">False Positive</span>
                      </td>
                    </tr>
                    <tr>
                      <th>Actual SAR</th>
                      <td className="cm-cell-red">
                        <span className="cm-num">{fn}</span>
                        <span className="cm-lbl">False Negative</span>
                      </td>
                      <td className="cm-cell-green">
                        <span className="cm-num">{tp}</span>
                        <span className="cm-lbl">True Positive</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Interactive Threshold Simulation */}
          <div className="panel" style={{ marginTop: 20 }}>
            <div className="panel-header">
              <h2 className="panel-title">Threshold Tuning Simulation</h2>
              <span className="panel-subtitle">Tradeoff between Investigator Alert Burden &amp; SAR Capture</span>
            </div>
            <div style={{ padding: '10px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 15 }}>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={simulatedThreshold}
                  onChange={(e) => setSimulatedThreshold(parseFloat(e.target.value))}
                  style={{ flex: 1, accentColor: '#00c2b2' }}
                />
                <span style={{ fontSize: 18, fontFamily: 'var(--font-mono)', minWidth: 60, color: '#00c2b2' }}>
                  {simulatedThreshold.toFixed(2)}
                </span>
              </div>
              <p style={{ fontSize: 13, color: '#94a9c9' }}>
                Simulating decision threshold at <strong>{simulatedThreshold.toFixed(2)}</strong>. Lowering the threshold
                increases SAR recall while increasing investigator triage workload.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
