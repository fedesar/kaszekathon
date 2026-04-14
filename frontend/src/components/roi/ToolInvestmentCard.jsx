import React from 'react';
import './ToolInvestmentCard.css';

function UtilizationBar({ pct }) {
  const fillClass =
    pct >= 70
      ? 'tool-card__util-bar-fill tool-card__util-bar-fill--high'
      : pct < 40
      ? 'tool-card__util-bar-fill tool-card__util-bar-fill--low'
      : 'tool-card__util-bar-fill';

  return (
    <div className="tool-card__util-bar-wrap">
      <div className="tool-card__util-label">
        <span>Seat utilization</span>
        <span>{pct}%</span>
      </div>
      <div className="tool-card__util-bar-track">
        <div className={fillClass} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

export default function ToolInvestmentCard({ tool, toolLabel, logo, seats, activeUsers, monthlyCost, pricePerSeat, utilizationPct }) {
  return (
    <div className="tool-card">
      <div className="tool-card__header">
        {logo && (
          <img
            src={`/${logo}`}
            alt={toolLabel}
            className="tool-card__logo"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        )}
        <span className="tool-card__name">{toolLabel}</span>
      </div>

      <div className="tool-card__rows">
        <div className="tool-card__row">
          <span>Monthly cost</span>
          <span className="tool-card__row-value">${monthlyCost?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="tool-card__row">
          <span>Price per seat</span>
          <span className="tool-card__row-value">${pricePerSeat}/mo</span>
        </div>
        <div className="tool-card__row">
          <span>Licensed seats</span>
          <span className="tool-card__row-value">{seats}</span>
        </div>
        <div className="tool-card__row">
          <span>Active users</span>
          <span className="tool-card__row-value">{activeUsers}</span>
        </div>
      </div>

      <UtilizationBar pct={utilizationPct ?? 0} />
    </div>
  );
}
