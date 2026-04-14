import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

export default function WeeklyActiveUsersChart({ data }) {
  return (
    <ChartCard title="Weekly Active Users" subtitle="Unique active users per week">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data || []} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#999' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11, fill: '#999' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(v) => [v, 'Active Users']}
          />
          <Line
            type="monotone"
            dataKey="active_users"
            stroke="#419FFF"
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#419FFF' }}
            activeDot={{ r: 6 }}
            name="Active Users"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
