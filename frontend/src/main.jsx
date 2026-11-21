import React, { Suspense, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Loading } from './components/Loading';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ResearchProvider, useResearch } from './context/ResearchContext';
import { DatasetSelector } from './components/DatasetSelector';
import { getSessionToken } from './api';
import './style.css';

// Lazy-loaded routes for code splitting and fast bundle loading
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Accounts = React.lazy(() => import('./pages/Accounts'));
const Transactions = React.lazy(() => import('./pages/Transactions'));
const GraphExplorer = React.lazy(() => import('./pages/GraphExplorer'));
const Alerts = React.lazy(() => import('./pages/Alerts'));
const Performance = React.lazy(() => import('./pages/Performance'));
const Management = React.lazy(() => import('./pages/Management'));
const Research = React.lazy(() => import('./pages/Research'));
const Biometrics = React.lazy(() => import('./pages/Biometrics'));

function TopHeader() {
  const location = useLocation();
  const sessionToken = getSessionToken();
  const { selectedTier, timezone, setTimezone, TIMEZONES } = useResearch();
  const [clockStr, setClockStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      try {
        const d = new Date();
        const formatted = new Intl.DateTimeFormat('en-IN', {
          timeZone: timezone,
          month: 'short',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        }).format(d);
        setClockStr(formatted);
      } catch {
        setClockStr(new Date().toUTCString());
      }
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, [timezone]);

  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path === '/') return 'Overview';
    if (path.startsWith('/accounts')) return 'Accounts';
    if (path.startsWith('/transactions')) return 'Transactions';
    if (path.startsWith('/graph')) return 'Graph Explorer';
    if (path.startsWith('/alerts')) return 'Suspicious Activity';
    if (path.startsWith('/performance')) return 'Model Performance';
    if (path.startsWith('/management')) return 'Model Operations';
    if (path.startsWith('/research')) return 'Model Library';
    if (path.startsWith('/biometrics')) return 'Security';
    return 'Workstation';
  };

  return (
    <header className="top-header">
      <div className="header-left">
        <div className="breadcrumbs">
          AMLNet 2.0 / <span>{getBreadcrumb()}</span>
        </div>
        <div style={{ marginLeft: 16 }}>
          <DatasetSelector compact={true} />
        </div>
      </div>
      <div className="header-right">
        <div className="timezone-selector-wrap" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <label htmlFor="tz-select" style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>TZ:</label>
          <select
            id="tz-select"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            style={{
              background: '#0e1726',
              border: '1px solid #1e293b',
              color: '#94a3b8',
              fontSize: 11,
              borderRadius: 4,
              padding: '3px 8px',
              fontFamily: 'var(--font-mono)'
            }}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz.value} value={tz.value}>
                {tz.label}
              </option>
            ))}
          </select>
        </div>
        {sessionToken ? (
          <div className="auth-badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
            <span>Passkey Session Active</span>
          </div>
        ) : null}
        <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'var(--font-mono)', minWidth: 140, textAlign: 'right' }}>
          {clockStr}
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <ResearchProvider>
          <div className="app-container">
            <Navbar />
            <div className="main-wrapper">
              <TopHeader />
              <main className="content-area">
                <Suspense fallback={<Loading message="Assembling intelligence workstation…" />}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/accounts" element={<Accounts />} />
                    <Route path="/transactions" element={<Transactions />} />
                    <Route path="/graph" element={<GraphExplorer />} />
                    <Route path="/alerts" element={<Alerts />} />
                    <Route path="/performance" element={<Performance />} />
                    <Route path="/management" element={<Management />} />
                    <Route path="/research" element={<Research />} />
                    <Route path="/biometrics" element={<Biometrics />} />
                  </Routes>
                </Suspense>
              </main>
            </div>
          </div>
        </ResearchProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')).render(<App />);
