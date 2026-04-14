import React from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import './LoadingSpinner.css';

export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="loading-spinner">
      <CircularProgress size={32} sx={{ color: 'var(--lm-primary-light)' }} />
      <span>{message}</span>
    </div>
  );
}
