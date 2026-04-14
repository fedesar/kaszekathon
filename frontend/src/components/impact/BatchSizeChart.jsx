import React from 'react';
import ChartCard from '../common/ChartCard.jsx';

function BarRow({ label, value, maxValue, color }) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
      <span style={{ width: 90, fontSize: 13, fontWeight: 500, color: '#444', flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, background: '#F0F0F0', borderRadius: 6, height: 28, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.max(pct, 2)}%`,
            height: '100%',
            background: color,
            borderRadius: 6,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <span style={{ width: 80, fontSize: 14, fontWeight: 600, color: '#333', textAlign: 'right', flexShrink: 0 }}>
        {(value || 0).toLocaleString()} LOC
      </span>
    </div>
  );
}

export default function BatchSizeChart({ aiAvg, nonAiAvg }) {
  const ai = aiAvg || 0;
  const nonAi = nonAiAvg || 0;
  const maxVal = Math.max(ai, nonAi, 1);
  const diff = nonAi > 0 ? Math.round(((ai - nonAi) / nonAi) * 100) : 0;
  const diffLabel = diff > 0 ? `${diff}% smaller` : diff < 0 ? `${Math.abs(diff)}% larger` : '';

  return (
    <ChartCard title="Batch Size" subtitle="Average lines of code per pull request">
      <div style={{ padding: '16px 0' }}>
        <BarRow label="AI-Assisted" value={ai} maxValue={maxVal} color="#419FFF" />
        <BarRow label="Non-AI" value={nonAi} maxValue={maxVal} color="#ECB22E" />
        {diffLabel && (
          <p style={{ fontSize: 12, color: '#999', margin: '8px 0 0 102px' }}>
            AI PRs are {diffLabel} on average
          </p>
        )}
      </div>
    </ChartCard>
  );
}
