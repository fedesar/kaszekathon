import React, { useState } from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import './AIDashboard.css';
import UsageTab from '../usage/UsageTab.jsx';
import ImpactTab from '../impact/ImpactTab.jsx';
import LicenseEfficiencyTab from '../license-efficiency/LicenseEfficiencyTab.jsx';
import AgentsTab from '../agents/AgentsTab.jsx';

const TABS = ['AI Usage', 'AI Impact', 'License Efficiency', 'AI Agents'];

export default function AIDashboard({ orgId, startDate, endDate }) {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (_e, newValue) => {
    setActiveTab(newValue);
  };

  return (
    <div className="ai-dashboard">
      <div className="ai-dashboard__tab-bar">
        <Tabs value={activeTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          {TABS.map((label) => (
            <Tab key={label} label={label} disableRipple />
          ))}
        </Tabs>
      </div>

      <div className="ai-dashboard__tab-panel" role="tabpanel">
        {activeTab === 0 && (
          <UsageTab orgId={orgId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === 1 && (
          <ImpactTab orgId={orgId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === 2 && (
          <LicenseEfficiencyTab orgId={orgId} startDate={startDate} endDate={endDate} />
        )}
        {activeTab === 3 && <AgentsTab />}
      </div>
    </div>
  );
}
