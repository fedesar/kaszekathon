import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

export default function BatchSizeChart({ aiAvg, nonAiAvg }) {
  const data = [
    {
      name: 'Avg LOC / PR',
      'AI-Assisted': aiAvg || 0,
      'Non-AI': nonAiAvg || 0,
    },
  ];

  return (
    <ChartCard title="Batch Size" subtitle="Average lines of code per pull request">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }} barSize={40}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#999' }} />
          <YAxis tick={{ fontSize: 11, fill: '#999' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(v, n) => [`${v} LOC`, n]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="AI-Assisted" fill="#419FFF" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Non-AI" fill="#ECB22E" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
