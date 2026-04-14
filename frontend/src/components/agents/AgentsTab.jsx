import React from 'react';
import './AgentsTab.css';

const FAKE_CARDS = [1, 2, 3, 4, 5, 6];

export default function AgentsTab() {
  return (
    <div className="agents-tab">
      <div className="agents-tab__blurred-bg" aria-hidden="true">
        {FAKE_CARDS.map((i) => (
          <div key={i} className="agents-tab__fake-card" />
        ))}
      </div>

      <div className="agents-tab__overlay">
        <div className="agents-tab__coming-soon-card">
          <span className="agents-tab__icon">🤖</span>
          <h2 className="agents-tab__title">AI Agents</h2>
          <p className="agents-tab__subtitle">
            Monitor agentic workflows, track agent runs, success rates, and token
            consumption across your organization.
          </p>

          <div className="agents-tab__tools">
            <span className="agents-tab__tool-badge">
              <img src="/claude-code.svg" alt="Claude" className="agents-tab__tool-logo" />
              Claude Managed Agents
            </span>
          </div>

          <span className="agents-tab__badge">Coming Soon</span>
        </div>
      </div>
    </div>
  );
}
