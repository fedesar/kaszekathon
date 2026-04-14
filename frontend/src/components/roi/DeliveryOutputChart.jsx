import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function DeliveryOutputChart({ data, costPerPr }) {
  const formatted = (data || []).map((d) => ({ ...d, dateLabel: formatDate(d.date) }));

  const badge = costPerPr > 0
    ? `$${Number(costPerPr).toFixed(2)} / PR`
    : null;

  return (
    <ChartCard
      title="Delivery Output"
      subtitle="AI-assisted pull requests merged per day"
      toolbar={badge && (
        <span className="cost-per-pr-badge">{badge}</span>
      )}
    >
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={formatted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" vertical={false} />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: '#999' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11, fill: '#999' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(v) => [v, 'PRs Merged']}
          />
          <Bar dataKey="prs_merged" fill="#1C2E62" radius={[3, 3, 0, 0]} name="PRs Merged" />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
