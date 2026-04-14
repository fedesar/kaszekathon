import React from 'react';
import './StageSwitcher.css';

const STAGES = [
  { key: 'lead_time', label: 'Lead Time' },
  { key: 'coding', label: 'Coding' },
  { key: 'waiting_for_review', label: 'Waiting for Review' },
  { key: 'in_review', label: 'In Review' },
  { key: 'ready_to_deploy', label: 'Ready to Deploy' },
];

export default function StageSwitcher({ activeStage, onStageChange }) {
  return (
    <div className="stage-switcher">
      {STAGES.map((s) => (
        <button
          key={s.key}
          className={`stage-switcher__btn${activeStage === s.key ? ' stage-switcher__btn--active' : ''}`}
          onClick={() => onStageChange(s.key)}
          type="button"
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
