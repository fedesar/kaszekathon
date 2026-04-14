import React, { useState, useEffect } from 'react';
import './ImpactTab.css';
import { fetchImpact } from '../../api/dashboardApi.js';
import LoadingSpinner from '../common/LoadingSpinner.jsx';
import EmptyState from '../common/EmptyState.jsx';
import LeadTimeChart from './LeadTimeChart.jsx';
import StageSwitcher from './StageSwitcher.jsx';
import ShareDonutChart from './ShareDonutChart.jsx';
import BatchSizeChart from './BatchSizeChart.jsx';
import CorrelationScatterChart from './CorrelationScatterChart.jsx';

export default function ImpactTab({ orgId, startDate, endDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeStage, setActiveStage] = useState('lead_time');
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchImpact(orgId, startDate, endDate, controller.signal)
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.code === 'ERR_CANCELED') return;
        setError(err?.response?.data?.error || 'Failed to load impact data.');
        setLoading(false);
      });
    return () => controller.abort();
  }, [orgId, startDate, endDate, retryCount]);

  if (loading) return <LoadingSpinner message="Loading impact data..." />;
  if (error) return <EmptyState title="Error" description={error} variant="error" onRetry={() => setRetryCount((c) => c + 1)} />;
  if (!data) return <EmptyState title="No data" description="No impact data found for this period." />;

  const {
    lead_time_timeline = [],
    ai_pr_breakdown = {},
    ai_commits_breakdown = {},
    loc_breakdown = {},
    pr_size_comparison = {},
    delivery_correlation = [],
  } = data;

  return (
    <div className="impact-tab">
      <div className="impact-tab__lead-time-section">
        <StageSwitcher activeStage={activeStage} onStageChange={setActiveStage} />
        <LeadTimeChart data={lead_time_timeline} activeStage={activeStage} />
      </div>

      <div className="impact-tab__donuts-row">
        <ShareDonutChart
          title="AI-Assisted PR Share"
          aiCount={ai_pr_breakdown.ai_prs}
          totalCount={ai_pr_breakdown.total_prs}
          aiLabel="AI PRs"
          nonAiLabel="Non-AI PRs"
        />
        <ShareDonutChart
          title="AI Commits Share"
          aiCount={ai_commits_breakdown.ai_commits}
          totalCount={ai_commits_breakdown.total_commits}
          aiLabel="AI Commits"
          nonAiLabel="Non-AI Commits"
        />
        <ShareDonutChart
          title="LOC Share"
          aiCount={loc_breakdown.ai_loc}
          totalCount={loc_breakdown.total_loc}
          aiLabel="AI LOC"
          nonAiLabel="Non-AI LOC"
        />
      </div>

      <div className="impact-tab__bottom-row">
        <BatchSizeChart
          aiAvg={pr_size_comparison.ai_avg_loc_per_pr}
          nonAiAvg={pr_size_comparison.non_ai_avg_loc_per_pr}
        />
      </div>

      <div className="impact-tab__scatter-grid">
        <CorrelationScatterChart
          title="AI Intensity vs Cycle Time"
          data={delivery_correlation}
          xKey="ai_intensity"
          yKey="cycle_time"
          xLabel="AI Intensity"
          yLabel="Cycle Time (days)"
        />
        <CorrelationScatterChart
          title="AI Intensity vs Throughput"
          data={delivery_correlation}
          xKey="ai_intensity"
          yKey="throughput"
          xLabel="AI Intensity"
          yLabel="Throughput (PRs)"
        />
        <CorrelationScatterChart
          title="AI Intensity vs Bug Rate"
          data={delivery_correlation}
          xKey="ai_intensity"
          yKey="bug_pct"
          xLabel="AI Intensity"
          yLabel="Bug %"
        />
      </div>
    </div>
  );
}
