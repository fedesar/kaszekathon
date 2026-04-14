import React from 'react';
import './Sidebar.css';

const NAV_ITEMS = [
  { icon: '📊', label: 'Performance', active: false },
  { icon: '🤖', label: 'AI Governance', active: true },
  { icon: '💰', label: 'Project Investment', active: false },
  { icon: '🔍', label: 'Bottleneck Insights', active: false },
  { icon: '🎯', label: 'Strategic Overview', active: false },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__logo-area">
        <img
          src="/leanmote-logo-white.png"
          alt="Leanmote"
          className="sidebar__logo"
        />
      </div>

      <nav className="sidebar__nav">
        <span className="sidebar__section-label">Dashboards</span>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.label}
            className={`sidebar__nav-item${item.active ? ' sidebar__nav-item--active' : ''}`}
          >
            <span className="sidebar__nav-icon">{item.icon}</span>
            <span className="sidebar__nav-label">{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar__footer">
        <span className="sidebar__version">Leanmote v1.0</span>
      </div>
    </aside>
  );
}
