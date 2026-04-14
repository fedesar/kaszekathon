import React from 'react';
import './EmptyState.css';

export default function EmptyState({ icon = '📭', title, description, variant = '' }) {
  const cls = `empty-state${variant ? ` empty-state--${variant}` : ''}`;
  return (
    <div className={cls}>
      <span className="empty-state__icon">{icon}</span>
      {title && <span className="empty-state__title">{title}</span>}
      {description && <span className="empty-state__description">{description}</span>}
    </div>
  );
}
