import React, { useState, useEffect } from 'react';
import { api, getAdminKey, setAdminKey, getSessionToken } from '../api';
import { Loading, ErrorBanner } from '../components/Loading';

export default function Management() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [adminKey, setAdminKeyState] = useState(getAdminKey());
  const [actionMessage, setActionMessage] = useState('');
  const [isActionRunning, setIsActionRunning] = useState(false);

  const loadStatus = () => {
    setLoading(true);
    api('/model/status')
      .then((res) => {
        setStatus(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleRetrain = async () => {
    setIsActionRunning(true);
    setActionMessage('Initiating GNN retraining pipeline…');
    try {
      const res = await api('/model/train', { method: 'POST' });
      setActionMessage(`Training started successfully (Run ID: ${res.run_id}). Authenticated as: ${res.authenticated_user || 'Admin'}`);
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setActionMessage(`Error starting training: ${err.message}`);
    } finally {
      setIsActionRunning(false);
    }
  };

  const handlePredict = async () => {
    setIsActionRunning(true);
    setActionMessage('Recalculating risk scores across all network accounts…');
    try {
      const res = await api('/model/predict', { method: 'POST' });
      setActionMessage(`Updated ${res.updated_accounts} accounts with version ${res.model_version}.`);
      setTimeout(loadStatus, 2000);
    } catch (err) {
      setActionMessage(`Error regenerating predictions: ${err.message}`);
    } finally {
      setIsActionRunning(false);
    }
  };

  const handleKeySave = (val) => {
    setAdminKeyState(val);
    setAdminKey(val);
  };

  if (loading) return <Loading message="Loading model status…" />;

  const sessionToken = getSessionToken();

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Management & Operations</h1>
          <p className="page-desc">
            Inspect active model checkpoints, trigger retrain runs, and manage deployment state
          </p>
        </div>
      </div>

      {error && <ErrorBanner error={error} retry={loadStatus} />}

      <div className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Active Model Artifact</h2>
            <button className="secondary" onClick={loadStatus}>Refresh Status</button>
          </div>
          <div className="stat-card" style={{ marginBottom: 14 }}>
            <span className="stat-label">Model Checkpoint Version</span>
            <span className="stat-value mono" style={{ fontSize: 18, color: '#00c2b2' }}>
              {status?.model_version || 'None'}
            </span>
            <span className="stat-subtext">Stored in model_artifacts registry</span>
          </div>
          <div className="stat-card" style={{ marginBottom: 14 }}>
            <span className="stat-label">Operational Status</span>
            <span className="stat-value" style={{ fontSize: 18 }}>
              {status?.running ? 'Training in Progress' : status?.status || 'Active'}
            </span>
            <span className="stat-subtext">
              Last completed: {status?.last_run ? new Date(status.last_run).toLocaleString() : 'N/A'}
            </span>
          </div>
          {status?.error && (
            <div className="error-banner">
              <span>{status.error}</span>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Administrative Operations</h2>
          </div>
          <p style={{ fontSize: 12, color: '#96adcc', marginBottom: 16 }}>
            Model training and risk re-scoring require investigator authorization (either via platform biometric passkey or administrator key).
          </p>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 12, marginBottom: 6, color: '#cbd5e1' }}>
              Administrator Secret Key
            </label>
            <input
              type="password"
              placeholder="Enter Admin API Key (never saved to git)..."
              value={adminKey}
              onChange={(e) => handleKeySave(e.target.value)}
              style={{ width: '100%' }}
            />
            {sessionToken && (
              <div style={{ fontSize: 11, color: '#00c2b2', marginTop: 4 }}>
                ✓ Biometric Passkey session token is active. Admin key is optional.
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button
              onClick={handleRetrain}
              disabled={isActionRunning || status?.running}
            >
              {isActionRunning ? 'Executing…' : 'Train / Retrain Model'}
            </button>
            <button
              className="secondary"
              onClick={handlePredict}
              disabled={isActionRunning || status?.running}
            >
              Regenerate Predictions
            </button>
          </div>

          {actionMessage && (
            <div className="explain-card" style={{ marginTop: 16, borderLeft: '3px solid #00c2b2' }}>
              <div style={{ fontSize: 12, color: '#e2ecfc' }}>{actionMessage}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
