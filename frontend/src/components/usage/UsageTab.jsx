import React, { useState, useEffect } from 'react';
import './UsageTab.css';
import { fetchUsage } from '../../api/dashboardApi.js';
import KpiCard from '../common/KpiCard.jsx';
import LoadingSpinner from '../common/LoadingSpinner.jsx';
import EmptyState from '../common/EmptyState.jsx';
import UsageTrendChart from './UsageTrendChart.jsx';
import UserActivityTable from './UserActivityTable.jsx';

function formatNumber(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString();
}

export default function UsageTab({ orgId, startDate, endDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchUsage(orgId, startDate, endDate, controller.signal)
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setError(err?.response?.data?.error || 'Failed to load usage data.');
        setLoading(false);
      });
    return () => controller.abort();
  }, [orgId, startDate, endDate, retryCount]);

  if (loading) return <LoadingSpinner message="Loading usage data..." />;
  if (error) return <EmptyState icon="⚠️" title="Error" description={error} variant="error" onRetry={() => setRetryCount((c) => c + 1)} />;
  if (!data) return <EmptyState icon="📭" title="No data" description="No usage data found for this period." />;

  const { kpis = {}, daily_trend = [], user_list = [] } = data;

  return (
    <div className="usage-tab">
      <div className="usage-tab__kpi-grid">
        <KpiCard label="Total Sessions" value={formatNumber(kpis.total_sessions)} icon="💻" variant="highlight" />
        <KpiCard label="Active Users" value={formatNumber(kpis.active_users)} icon="👥" />
        <KpiCard label="LOC Added" value={formatNumber(kpis.loc_added)} icon="📝" variant="success" />
        <KpiCard label="PRs by AI" value={formatNumber(kpis.prs_by_ai)} icon="🔀" />
        <KpiCard label="AI Commits" value={formatNumber(kpis.ai_commits)} icon="✅" />
      </div>

      <div className="usage-tab__charts-row">
        <UsageTrendChart data={daily_trend} />
      </div>

      <div className="usage-tab__table-section">
        <UserActivityTable data={user_list} />
      </div>
    </div>
  );
}
