import React from 'react';
import { NavLink } from 'react-router-dom';

export function Navbar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-title">
          AML<span>Net</span>
          <span className="brand-badge">2.0</span>
        </div>
        <div className="brand-subtitle">Financial Intelligence Platform</div>
      </div>

      <nav className="nav-menu">
        <div className="nav-section-title">Investigation</div>
        <NavLink end to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Overview</span>
        </NavLink>
        <NavLink to="/accounts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Accounts</span>
        </NavLink>
        <NavLink to="/transactions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Transactions</span>
        </NavLink>
        <NavLink to="/graph" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Graph Explorer</span>
        </NavLink>
        <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Suspicious Activity</span>
        </NavLink>

        <div className="nav-section-title">Models & Systems</div>
        <NavLink to="/performance" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Model Performance</span>
        </NavLink>
        <NavLink to="/management" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Model Operations</span>
        </NavLink>

        <div className="nav-section-title">Research & Security</div>
        <NavLink to="/research" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Model Library</span>
        </NavLink>
        <NavLink to="/biometrics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <span>Security</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot" />
          <span>Multi-Tier Active</span>
        </div>
      </div>
    </aside>
  );
}
