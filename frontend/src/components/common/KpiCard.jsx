import React from 'react';
import './KpiCard.css';

export default function KpiCard({ label, value, icon, variant = '', subtext }) {
  const valueClass = `kpi-card__value${variant ? ` kpi-card__value--${variant}` : ''}`;

  return (
    <div className="kpi-card">
      {icon && <span className="kpi-card__icon">{icon}</span>}
      <span className="kpi-card__label">{label}</span>
      <span className={valueClass}>{value ?? '—'}</span>
      {subtext && <span className="kpi-card__subtext">{subtext}</span>}
    </div>
  );
}
