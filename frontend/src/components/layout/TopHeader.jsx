import React from 'react';
import './TopHeader.css';

export default function TopHeader({ startDate, endDate, onStartDateChange, onEndDateChange }) {
  return (
    <header className="top-header">
      <div className="top-header__title-block">
        <h1 className="top-header__title">AI Governance</h1>
        <span className="top-header__subtitle">Monitor AI tool usage, impact, and ROI across your team</span>
      </div>

      <div className="top-header__controls">
        <span className="top-header__date-label">From</span>
        <input
          type="date"
          className="top-header__date-input"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          max={endDate}
        />
        <span className="top-header__date-separator">–</span>
        <input
          type="date"
          className="top-header__date-input"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          min={startDate}
        />
      </div>
    </header>
  );
}
