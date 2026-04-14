import React from 'react';
import './ChartCard.css';

export default function ChartCard({ title, subtitle, toolbar, children, noPadding = false }) {
  return (
    <div className="chart-card">
      {(title || toolbar) && (
        <div className="chart-card__header">
          <div>
            {title && <div className="chart-card__title">{title}</div>}
            {subtitle && <div className="chart-card__subtitle">{subtitle}</div>}
          </div>
          {toolbar && <div className="chart-card__toolbar">{toolbar}</div>}
        </div>
      )}
      <div className={`chart-card__body${noPadding ? ' chart-card__body--no-padding' : ''}`}>
        {children}
      </div>
    </div>
  );
}
