import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

const STAGE_KEYS = {
  lead_time:          { ai: 'ai_lead_time',          nonAi: 'non_ai_lead_time' },
  coding:             { ai: 'ai_coding',             nonAi: 'non_ai_coding' },
  waiting_for_review: { ai: 'ai_waiting_for_review', nonAi: 'non_ai_waiting_for_review' },
  in_review:          { ai: 'ai_in_review',          nonAi: 'non_ai_in_review' },
  ready_to_deploy:    { ai: 'ai_ready_to_deploy',    nonAi: 'non_ai_ready_to_deploy' },
};

const STAGE_LABELS = {
  lead_time: 'Lead Time',
  coding: 'Coding',
  waiting_for_review: 'Waiting for Review',
  in_review: 'In Review',
  ready_to_deploy: 'Ready to Deploy',
};

export default function LeadTimeChart({ data, activeStage }) {
  const keys = STAGE_KEYS[activeStage] || STAGE_KEYS.lead_time;
  const stageLabel = STAGE_LABELS[activeStage] || 'Lead Time';

  if (!data || data.length === 0) {
    return (
      <ChartCard title={`${stageLabel} — AI vs Non-AI`}>
        <p style={{ color: 'var(--lm-medium-grey)', textAlign: 'center', padding: '40px 0' }}>
          No lead time data available.
        </p>
      </ChartCard>
    );
  }

  return (
    <ChartCard
      title={`${stageLabel} — AI vs Non-AI`}
      subtitle="Average days per week"
    >
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#999' }} interval="preserveStartEnd" />
          <YAxis
            tick={{ fontSize: 11, fill: '#999' }}
            label={{ value: 'Days', angle: -90, position: 'insideLeft', offset: 8, style: { fontSize: 11, fill: '#999' } }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(value, name) => [`${Number(value).toFixed(1)} days`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey={keys.ai}
            name="AI-Assisted PRs"
            stroke="#419FFF"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey={keys.nonAi}
            name="Non-AI PRs"
            stroke="#ECB22E"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5 }}
            strokeDasharray="5 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
