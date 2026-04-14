import React, { useState } from 'react';
import './App.css';
import TopHeader from './components/layout/TopHeader.jsx';
import AIDashboard from './components/dashboard/AIDashboard.jsx';

const DEFAULT_ORG_ID = Number(import.meta.env.VITE_DEFAULT_ORG_ID) || 1;

function getDefaultDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 29);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

export default function App() {
  const { start: defaultStart, end: defaultEnd } = getDefaultDates();

  const [orgId] = useState(DEFAULT_ORG_ID);
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);

  return (
    <div className="app-root">
      <TopHeader
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
      />
      <main className="app-content">
        <AIDashboard orgId={orgId} startDate={startDate} endDate={endDate} />
      </main>
    </div>
  );
}
