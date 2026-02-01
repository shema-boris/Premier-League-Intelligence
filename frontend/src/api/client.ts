import type {
  AnalysisResponse,
  HealthResponse,
  MetricsResponse,
  PredictionResponse,
  TeamFormResponse,
  LineupResponse,
  HeadToHeadResponse,
  TeamLogoResponse,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  health: () => fetchJson<HealthResponse>(`${API_BASE}/health`),

  analyzeAll: () =>
    fetchJson<AnalysisResponse[]>(`${API_BASE}/analyze-all`, {
      method: 'POST',
    }),

  analyze: (homeTeam: string, awayTeam: string) =>
    fetchJson<AnalysisResponse>(
      `${API_BASE}/analyze?home_team=${encodeURIComponent(homeTeam)}&away_team=${encodeURIComponent(awayTeam)}`,
      { method: 'POST' }
    ),

  getPredictions: (validatedOnly = false, pendingOnly = false) => {
    const params = new URLSearchParams();
    if (validatedOnly) params.set('validated_only', 'true');
    if (pendingOnly) params.set('pending_only', 'true');
    return fetchJson<PredictionResponse[]>(`${API_BASE}/predictions?${params}`);
  },

  getMetrics: () => fetchJson<MetricsResponse>(`${API_BASE}/metrics`),

  runValidation: () =>
    fetchJson<{ updated: number; still_pending: number; metrics: MetricsResponse }>(
      `${API_BASE}/validate`,
      { method: 'POST' }
    ),

  getTeamForm: (teamName: string) =>
    fetchJson<TeamFormResponse>(`${API_BASE}/team-form/${encodeURIComponent(teamName)}`),

  getLineup: (teamName: string) =>
    fetchJson<LineupResponse>(`${API_BASE}/lineup/${encodeURIComponent(teamName)}`),

  getHeadToHead: (team1: string, team2: string) =>
    fetchJson<HeadToHeadResponse>(
      `${API_BASE}/head-to-head/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}`
    ),

  getTeamLogo: (teamName: string) =>
    fetchJson<TeamLogoResponse>(`${API_BASE}/team-logo/${encodeURIComponent(teamName)}`),
};
