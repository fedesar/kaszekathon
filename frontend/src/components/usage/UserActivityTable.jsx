import React, { useState } from 'react';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';
import ChartCard from '../common/ChartCard.jsx';

const COLUMNS = [
  { id: 'email', label: 'User', numeric: false },
  { id: 'active_days', label: 'Active Days', numeric: true },
  { id: 'sessions', label: 'Sessions', numeric: true },
  { id: 'tokens_consumed', label: 'Tokens', numeric: true },
  { id: 'loc_added', label: 'LOC Added', numeric: true },
  { id: 'prs', label: 'AI PRs', numeric: true },
  { id: 'commits', label: 'AI Commits', numeric: true },
  { id: 'tool_acceptance_rate', label: 'Acceptance Rate', numeric: true },
];

function stableSort(arr, comparator) {
  return [...arr].sort(comparator);
}

function getComparator(order, orderBy) {
  return order === 'desc'
    ? (a, b) => (b[orderBy] < a[orderBy] ? -1 : b[orderBy] > a[orderBy] ? 1 : 0)
    : (a, b) => (a[orderBy] < b[orderBy] ? -1 : a[orderBy] > b[orderBy] ? 1 : 0);
}

function AcceptanceBar({ rate }) {
  const pct = Math.round(rate * 100);
  return (
    <span className="acceptance-bar-wrap">
      {pct}%
    </span>
  );
}

export default function UserActivityTable({ data }) {
  const [order, setOrder] = useState('desc');
  const [orderBy, setOrderBy] = useState('loc_added');

  const handleSort = (col) => {
    if (orderBy === col) {
      setOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setOrderBy(col);
      setOrder('desc');
    }
  };

  const sorted = stableSort(data || [], getComparator(order, orderBy));

  return (
    <ChartCard title="User Activity" subtitle="Per-user breakdown for the selected period" noPadding>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ background: '#F9F9F9' }}>
              {COLUMNS.map((col) => (
                <TableCell
                  key={col.id}
                  align={col.numeric ? 'right' : 'left'}
                  sx={{ fontWeight: 600, fontSize: '12px', color: '#666', whiteSpace: 'nowrap' }}
                >
                  <TableSortLabel
                    active={orderBy === col.id}
                    direction={orderBy === col.id ? order : 'asc'}
                    onClick={() => handleSort(col.id)}
                  >
                    {col.label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.length === 0 ? (
              <TableRow>
                <TableCell colSpan={COLUMNS.length} align="center" sx={{ color: '#999', py: 4 }}>
                  No user activity data for this period.
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((row, i) => (
                <TableRow key={row.email || i} hover>
                  <TableCell sx={{ fontWeight: 500, fontSize: '13px' }}>{row.email || '—'}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.active_days}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.sessions?.toLocaleString()}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.tokens_consumed?.toLocaleString()}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.loc_added?.toLocaleString()}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.prs}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>{row.commits}</TableCell>
                  <TableCell align="right" sx={{ fontSize: '13px' }}>
                    <AcceptanceBar rate={row.tool_acceptance_rate} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </ChartCard>
  );
}
