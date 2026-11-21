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
  const [now, setNow] = useState(new Date().toUTCString());
  const { selectedTier } = useResearch();

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date().toUTCString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path === '/') return 'Dashboard';
    if (path.startsWith('/accounts')) return 'Account Investigation';
    if (path.startsWith('/transactions')) return 'Transaction Explorer';
    if (path.startsWith('/graph')) return 'Graph Explorer 2.0';
    if (path.startsWith('/alerts')) return 'Suspicious Signals';
    if (path.startsWith('/performance')) return 'Model Benchmarks';
    if (path.startsWith('/management')) return 'Model Operations';
    if (path.startsWith('/research')) return 'Research Lab';
    if (path.startsWith('/biometrics')) return 'Biometric Passkeys';
    return 'AMLNet';
  };

  const isResearchRoute = location.pathname.startsWith('/research') || location.pathname.startsWith('/performance');

  return (
    <header className="top-header">
      <div className="header-left">
        <div className="breadcrumbs">
          AMLNet 2.0 / <span>{getBreadcrumb()}</span>
        </div>
        {isResearchRoute ? (
          <div style={{ marginLeft: 16 }}>
            <DatasetSelector compact={true} />
          </div>
        ) : (
          <div style={{ marginLeft: 16 }}>
            <span className="scope-tag demo-tag">💼 Scope: Operational Demo (100 Accounts)</span>
          </div>
        )}
      </div>
      <div className="header-right">
        {sessionToken ? (
          <div className="auth-badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
            <span>🛡️</span>
            <span>Passkey Session Active</span>
          </div>
        ) : (
          <div className="auth-badge">
            <span>🔒</span>
            <span>Standard Access</span>
          </div>
        )}
        <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'var(--font-mono)' }}>
          {now}
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
