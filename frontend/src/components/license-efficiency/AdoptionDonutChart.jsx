import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

const SEGMENT_COLORS = {
  power_users:  '#419FFF',
  casual_users: '#40D390',
  idle_users:   '#ECB22E',
  new_users:    '#C91EEB',
};

const SEGMENT_LABELS = {
  power_users:  'Power Users',
  casual_users: 'Casual',
  idle_users:   'Idle',
  new_users:    'New',
};

export default function AdoptionDonutChart({ segments }) {
  const data = Object.entries(segments || {})
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: SEGMENT_LABELS[key] || key,
      value,
      color: SEGMENT_COLORS[key] || '#999',
    }));

  return (
    <ChartCard title="Adoption Segments" subtitle="User activity segmentation">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            dataKey="value"
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(value, name) => [value, name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
