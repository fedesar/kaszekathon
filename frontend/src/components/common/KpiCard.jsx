import React from 'react';
import './KpiCard.css';

export default function KpiCard({ label, value, icon, variant = '', subtext }) {
  const cardClass = `kpi-card${variant ? ` kpi-card--${variant}` : ''}`;
  const valueClass = `kpi-card__value${variant ? ` kpi-card__value--${variant}` : ''}`;

  return (
    <div className={cardClass}>
      {icon && <div className="kpi-card__icon-wrap">{icon}</div>}
      <span className="kpi-card__label">{label}</span>
      <span className={valueClass}>{value ?? '—'}</span>
      {subtext && <span className="kpi-card__subtext">{subtext}</span>}
    </div>
  );
}
