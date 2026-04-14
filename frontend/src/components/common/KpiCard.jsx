import React, { useState } from 'react';
import './KpiCard.css';

export default function KpiCard({ label, value, icon, variant = '', subtext, tooltip }) {
  const [showTip, setShowTip] = useState(false);
  const cardClass = `kpi-card${variant ? ` kpi-card--${variant}` : ''}`;
  const valueClass = `kpi-card__value${variant ? ` kpi-card__value--${variant}` : ''}`;

  return (
    <div className={cardClass}>
      {icon && <div className="kpi-card__icon-wrap">{icon}</div>}
      <div className="kpi-card__label-row">
        <span className="kpi-card__label">{label}</span>
        {tooltip && (
          <span
            className="kpi-card__info"
            onMouseEnter={() => setShowTip(true)}
            onMouseLeave={() => setShowTip(false)}
          >
            i
            {showTip && <div className="kpi-card__tooltip">{tooltip}</div>}
          </span>
        )}
      </div>
      <span className={valueClass}>{value ?? '—'}</span>
      {subtext && <span className="kpi-card__subtext">{subtext}</span>}
    </div>
  );
}
