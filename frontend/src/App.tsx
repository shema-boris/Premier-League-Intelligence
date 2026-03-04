import React, { useState, useEffect, useCallback } from 'react';
import { TopBar, MatchweekTable, DeepDivePanel } from './components';
import { RefreshBanner } from './components/RefreshBanner';
import { api } from './api/client';
import { defaultMatches } from './data/defaultMatches';
import type { AnalysisResponse } from './types';

const CACHE_KEY = 'pl-intel-matches';
const CACHE_TIME_KEY = 'pl-intel-matches-time';

function getCachedMatches(): AnalysisResponse[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) return JSON.parse(cached);
  } catch { /* ignore parse errors */ }
  return null;
}

function setCachedMatches(data: AnalysisResponse[]) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    localStorage.setItem(CACHE_TIME_KEY, new Date().toISOString());
  } catch { /* ignore storage errors */ }
}

function App() {
  const [isDark, setIsDark] = useState(true);
  const cached = getCachedMatches();
  const initialData = cached || defaultMatches;
  const [matches, setMatches] = useState<AnalysisResponse[]>(initialData);
  const [selectedMatch, setSelectedMatch] = useState<AnalysisResponse | null>(initialData[0] || null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(
    localStorage.getItem(CACHE_TIME_KEY) || null
  );
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [justUpdated, setJustUpdated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'kickoff' | 'discrepancy'>('kickoff');
  const [filterBiggest, setFilterBiggest] = useState(false);

  const loadMatches = useCallback(async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const data = await api.analyzeAll();
      setMatches(data);
      setCachedMatches(data);
      setLastUpdated(new Date().toISOString());
      if (data.length > 0) {
        setSelectedMatch(data[0]);
      }
      setJustUpdated(true);
      setTimeout(() => setJustUpdated(false), 3500);
    } catch (err) {
      if (matches.length === 0) {
        setError(err instanceof Error ? err.message : 'Failed to load matches');
      }
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [matches.length]);

  useEffect(() => {
    loadMatches();
  }, [loadMatches]);

  return (
    <div className={`${isDark ? 'dark' : ''}`}>
      <div className="min-h-screen bg-pl-dark text-pl-text flex flex-col">
        <TopBar
          lastUpdated={lastUpdated}
          isLive={!loading && matches.length > 0}
          isDark={isDark}
          onToggleTheme={() => setIsDark(!isDark)}
        />

        <RefreshBanner isRefreshing={isRefreshing} justUpdated={justUpdated} />

        <main className="flex-1 flex overflow-hidden">
          {loading && matches.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-pl-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-pl-text-dim">Analyzing matches...</p>
              </div>
            </div>
          ) : error && matches.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-red-400 mb-4">{error}</p>
                <button
                  onClick={loadMatches}
                  className="px-4 py-2 bg-pl-accent text-pl-text-bright rounded hover:bg-pl-accent/80 transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Left Panel - Matchweek Overview */}
              <div className="w-1/2 border-r border-pl-border bg-pl-card">
                <MatchweekTable
                  matches={matches}
                  selectedMatch={selectedMatch}
                  onSelectMatch={setSelectedMatch}
                  sortBy={sortBy}
                  onSortChange={setSortBy}
                  filterBiggest={filterBiggest}
                  onFilterChange={setFilterBiggest}
                />
              </div>

              {/* Right Panel - Match Deep Dive */}
              <div className="w-1/2 bg-pl-card">
                <DeepDivePanel
                  match={selectedMatch}
                  onClose={() => setSelectedMatch(null)}
                />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
