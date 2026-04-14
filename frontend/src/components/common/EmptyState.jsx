import React from 'react';
import './EmptyState.css';

export default function EmptyState({ icon = '📭', title, description, variant = '', onRetry }) {
  const cls = `empty-state${variant ? ` empty-state--${variant}` : ''}`;
  return (
    <div className={cls}>
      <span className="empty-state__icon">{icon}</span>
      {title && <span className="empty-state__title">{title}</span>}
      {description && <span className="empty-state__description">{description}</span>}
      {onRetry && (
        <button className="empty-state__retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
