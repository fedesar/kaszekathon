import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

const COLORS = ['#419FFF', '#E0E0E0'];

function renderCustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

export default function ShareDonutChart({ title, aiCount, totalCount, aiLabel = 'AI', nonAiLabel = 'Non-AI' }) {
  const nonAi = Math.max(0, (totalCount || 0) - (aiCount || 0));
  const pieData = [
    { name: aiLabel,     value: aiCount || 0 },
    { name: nonAiLabel,  value: nonAi },
  ];

  const pct = totalCount > 0 ? Math.round((aiCount / totalCount) * 100) : 0;

  return (
    <ChartCard title={title}>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            dataKey="value"
            labelLine={false}
            label={renderCustomLabel}
          >
            {pieData.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(value, name) => [value.toLocaleString(), name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="share-donut__center-label">
        <span className="share-donut__pct">{pct}%</span>
        <span className="share-donut__sub">{aiLabel}</span>
      </div>
    </ChartCard>
  );
}
