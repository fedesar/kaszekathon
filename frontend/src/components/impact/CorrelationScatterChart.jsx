import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import ChartCard from '../common/ChartCard.jsx';

export default function CorrelationScatterChart({ title, data, xKey, yKey, xLabel, yLabel }) {
  const plotData = (data || []).map((d) => ({
    x: d[xKey] ?? 0,
    y: d[yKey] ?? 0,
  }));

  return (
    <ChartCard title={title} subtitle={`${yLabel} vs ${xLabel}`}>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis
            type="number"
            dataKey="x"
            name={xLabel}
            tick={{ fontSize: 11, fill: '#999' }}
            label={{ value: xLabel, position: 'insideBottom', offset: -4, style: { fontSize: 11, fill: '#999' } }}
            height={40}
          />
          <YAxis
            type="number"
            dataKey="y"
            name={yLabel}
            tick={{ fontSize: 11, fill: '#999' }}
            label={{ value: yLabel, angle: -90, position: 'insideLeft', offset: 8, style: { fontSize: 11, fill: '#999' } }}
          />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #E0E0E0' }}
            formatter={(value, name) => [value, name]}
            cursor={{ strokeDasharray: '3 3' }}
          />
          <Scatter data={plotData} fill="#419FFF" opacity={0.7} />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
