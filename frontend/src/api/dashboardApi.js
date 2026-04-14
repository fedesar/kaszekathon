import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_KEY  = import.meta.env.VITE_API_KEY || '';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'X-Api-Key': API_KEY,
  },
  timeout: 120000,
});

export function fetchUsage(orgId, startDate, endDate, signal) {
  return client.get('/api/v1/usage', {
    params: { org_id: orgId, start_date: startDate, end_date: endDate },
    signal,
  });
}

export function fetchImpact(orgId, startDate, endDate, signal) {
  return client.get('/api/v1/impact', {
    params: { org_id: orgId, start_date: startDate, end_date: endDate },
    signal,
  });
}

export function fetchRoi(orgId, startDate, endDate, signal) {
  return client.get('/api/v1/roi', {
    params: { org_id: orgId, start_date: startDate, end_date: endDate },
    signal,
  });
}
