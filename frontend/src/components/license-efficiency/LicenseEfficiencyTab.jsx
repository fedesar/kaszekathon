import React, { useState, useEffect } from 'react';
import './LicenseEfficiencyTab.css';
import { fetchLicenseEfficiency } from '../../api/dashboardApi.js';
import KpiCard from '../common/KpiCard.jsx';
import Icon from '../common/Icon.jsx';
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

export default function LicenseEfficiencyTab({ orgId, startDate, endDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchLicenseEfficiency(orgId, startDate, endDate, controller.signal)
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setError(err?.response?.data?.error || 'Failed to load License Efficiency data.');
        setLoading(false);
      });
    return () => controller.abort();
  }, [orgId, startDate, endDate, retryCount]);

  if (loading) return <LoadingSpinner message="Loading License Efficiency data..." />;
  if (error) return <EmptyState title="Error" description={error} variant="error" onRetry={() => setRetryCount((c) => c + 1)} />;
  if (!data) return <EmptyState title="No data" description="No License Efficiency data found for this period." />;

  const {
    license_efficiency_summary = {},
    seats_summary = [],
    adoption_segments = {},
    cost_vs_delivery = [],
    weekly_active_users = [],
  } = data;

  return (
    <div className="le-tab">
      <div className="le-tab__kpi-grid">
        <KpiCard
          label="Total Investment"
          value={formatCurrency(license_efficiency_summary.total_investment_usd)}
          icon={<Icon name="creditCard" size={18} />}
          variant="highlight"
          tooltip="Total amount spent on AI coding tool API usage (tokens consumed) in this period."
        />
        <KpiCard
          label="Cost per PR"
          value={formatCurrency(license_efficiency_summary.cost_per_pr)}
          icon={<Icon name="gitPullRequest" size={18} />}
          tooltip="Average API cost per pull request. Lower means more efficient AI usage."
        />
        <KpiCard
          label="License Efficiency"
          value={license_efficiency_summary.license_efficiency_pct != null ? `${license_efficiency_summary.license_efficiency_pct}%` : '—'}
          icon={<Icon name="trendingUp" size={18} />}
          variant="success"
          tooltip="How much of your AI tool investment translates into actual usage. Higher is better."
        />
      </div>

      <div className="le-tab__tools-row">
        {seats_summary.map((tool) => (
          <ToolInvestmentCard key={tool.tool} {...tool} />
        ))}
      </div>

      <div className="le-tab__analytics-row">
        <AdoptionDonutChart segments={adoption_segments} />
        <DeliveryOutputChart data={cost_vs_delivery} costPerPr={license_efficiency_summary.cost_per_pr} />
      </div>

      <div className="le-tab__wau-row">
        <WeeklyActiveUsersChart data={weekly_active_users} />
      </div>
    </div>
  );
}
