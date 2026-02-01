import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { HeadToHeadResponse } from '../types';

interface HeadToHeadProps {
  team1: string;
  team2: string;
}

export const HeadToHead: React.FC<HeadToHeadProps> = ({ team1, team2 }) => {
  const [h2h, setH2h] = useState<HeadToHeadResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadH2H();
  }, [team1, team2]);

  const loadH2H = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHeadToHead(team1, team2);
      setH2h(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load H2H');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="w-6 h-6 border-2 border-pl-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !h2h) {
    return (
      <div className="text-center py-4">
        <p className="text-xs text-red-400">{error || 'No H2H data available'}</p>
      </div>
    );
  }

  const total = h2h.team1_wins + h2h.team2_wins + h2h.draws;

  return (
    <div className="space-y-3">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-pl-accent/20 rounded p-2">
          <p className="text-xs text-pl-text-dim">{team1}</p>
          <p className="text-xl font-bold text-pl-accent">{h2h.team1_wins}</p>
        </div>
        <div className="bg-pl-border/30 rounded p-2">
          <p className="text-xs text-pl-text-dim">Draws</p>
          <p className="text-xl font-bold text-pl-text">{h2h.draws}</p>
        </div>
        <div className="bg-pl-accent-orange/20 rounded p-2">
          <p className="text-xs text-pl-text-dim">{team2}</p>
          <p className="text-xl font-bold text-pl-accent-orange">{h2h.team2_wins}</p>
        </div>
      </div>

      {/* Win Percentage Bars */}
      {total > 0 && (
        <div className="space-y-2">
          <div className="flex gap-1 h-2 rounded-full overflow-hidden">
            <div 
              className="bg-pl-accent"
              style={{ width: `${(h2h.team1_wins / total) * 100}%` }}
            />
            <div 
              className="bg-gray-500"
              style={{ width: `${(h2h.draws / total) * 100}%` }}
            />
            <div 
              className="bg-pl-accent-orange"
              style={{ width: `${(h2h.team2_wins / total) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-pl-text-dim">
            <span>{((h2h.team1_wins / total) * 100).toFixed(0)}%</span>
            <span>{((h2h.draws / total) * 100).toFixed(0)}%</span>
            <span>{((h2h.team2_wins / total) * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* Recent Matches */}
      <div>
        <h4 className="text-xs text-pl-text-dim uppercase font-medium mb-2">
          Last {h2h.matches.length} Meetings (Recent Seasons)
        </h4>
        <div className="space-y-1">
          {h2h.matches.map((match, idx) => {
            const matchDate = new Date(match.date);
            const year = matchDate.getFullYear();
            const month = matchDate.getMonth();
            // Determine season (Aug-July)
            const season = month >= 7 ? `${year}/${year + 1}` : `${year - 1}/${year}`;
            
            return (
              <div key={idx} className="flex items-center justify-between text-xs bg-pl-border/20 rounded px-2 py-1">
                <div className="flex-1">
                  <p className="text-pl-text">
                    {match.home_team} vs {match.away_team}
                  </p>
                  <p className="text-pl-text-dim text-xs">
                    {matchDate.toLocaleDateString()} • {season} season
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">{match.score}</span>
                  <span className={`text-xs font-medium ${
                    match.winner === 'Draw' 
                      ? 'text-gray-400' 
                      : match.winner === team1 
                        ? 'text-pl-accent' 
                        : 'text-pl-accent-orange'
                  }`}>
                    {match.winner === 'Draw' ? 'D' : match.winner === team1 ? 'W' : 'L'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
