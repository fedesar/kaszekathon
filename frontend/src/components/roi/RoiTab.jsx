import React, { useState, useEffect } from 'react';
import './RoiTab.css';
import { fetchRoi } from '../../api/dashboardApi.js';
import KpiCard from '../common/KpiCard.jsx';
import LoadingSpinner from '../common/LoadingSpinner.jsx';
import EmptyState from '../common/EmptyState.jsx';
import ToolInvestmentCard from './ToolInvestmentCard.jsx';
import AdoptionDonutChart from './AdoptionDonutChart.jsx';
import DeliveryOutputChart from './DeliveryOutputChart.jsx';
import WeeklyActiveUsersChart from './WeeklyActiveUsersChart.jsx';

function formatCurrency(n) {
  if (n == null) return '—';
  return `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function RoiTab({ orgId, startDate, endDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchRoi(orgId, startDate, endDate, controller.signal)
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setError(err?.response?.data?.error || 'Failed to load ROI data.');
        setLoading(false);
      });
    return () => controller.abort();
  }, [orgId, startDate, endDate, retryCount]);

  if (loading) return <LoadingSpinner message="Loading ROI data..." />;
  if (error) return <EmptyState icon="⚠️" title="Error" description={error} variant="error" onRetry={() => setRetryCount((c) => c + 1)} />;
  if (!data) return <EmptyState icon="📭" title="No data" description="No ROI data found for this period." />;

  const {
    roi_summary = {},
    seats_summary = [],
    adoption_segments = {},
    cost_vs_delivery = [],
    weekly_active_users = [],
  } = data;

  return (
    <div className="roi-tab">
      <div className="roi-tab__kpi-grid">
        <KpiCard
          label="Total Investment"
          value={formatCurrency(roi_summary.total_investment_usd)}
          icon="💳"
          variant="highlight"
        />
        <KpiCard
          label="Cost per PR"
          value={formatCurrency(roi_summary.cost_per_pr)}
          icon="🔀"
        />
        <KpiCard
          label="ROI"
          value={roi_summary.roi_pct != null ? `${roi_summary.roi_pct}%` : '—'}
          icon="📈"
          variant="success"
        />
      </div>

      <div className="roi-tab__tools-row">
        {seats_summary.map((tool) => (
          <ToolInvestmentCard key={tool.tool} {...tool} />
        ))}
      </div>

      <div className="roi-tab__analytics-row">
        <AdoptionDonutChart segments={adoption_segments} />
        <DeliveryOutputChart data={cost_vs_delivery} costPerPr={roi_summary.cost_per_pr} />
      </div>

      <div className="roi-tab__wau-row">
        <WeeklyActiveUsersChart data={weekly_active_users} />
      </div>
    </div>
  );
}
