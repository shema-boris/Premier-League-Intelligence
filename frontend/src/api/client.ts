import type {
  AnalysisResponse,
  HealthResponse,
  MetricsResponse,
  PredictionResponse,
} from '../types';

const API_BASE = 'http://localhost:8000';

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
};
