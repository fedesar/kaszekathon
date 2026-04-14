import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function UsageTrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <ChartCard title="Daily Usage Trend">
        <p style={{ color: 'var(--lm-medium-grey)', textAlign: 'center', padding: '40px 0' }}>
          No trend data available for this period.
        </p>
      </ChartCard>
    );
  }

  const formatted = data.map((d) => ({ ...d, dateLabel: formatDate(d.date) }));

  return (
    <ChartCard title="Daily Usage Trend" subtitle="Sessions and active users over the selected period">
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={formatted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gradSessions" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#419FFF" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#419FFF" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradUsers" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#40D390" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#40D390" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fill: '#999' }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11, fill: '#999' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(value, name) => [value, name === 'sessions' ? 'Sessions' : 'Active Users']}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend
            formatter={(value) => (value === 'sessions' ? 'Sessions' : 'Active Users')}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Area
            type="monotone"
            dataKey="sessions"
            stroke="#419FFF"
            strokeWidth={2}
            fill="url(#gradSessions)"
          />
          <Area
            type="monotone"
            dataKey="active_users"
            stroke="#40D390"
            strokeWidth={2}
            fill="url(#gradUsers)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
