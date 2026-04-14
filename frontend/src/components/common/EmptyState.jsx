import React from 'react';
import './EmptyState.css';
import Icon from './Icon.jsx';

export default function EmptyState({ title, description, variant = '', onRetry }) {
  const cls = `empty-state${variant ? ` empty-state--${variant}` : ''}`;
  const iconName = variant === 'error' ? 'alertTriangle' : 'inbox';

  return (
    <div className={cls}>
      <div className="empty-state__icon-wrap">
        <Icon name={iconName} size={28} />
      </div>
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
