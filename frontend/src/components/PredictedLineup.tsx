import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { LineupResponse } from '../types';

interface PredictedLineupProps {
  teamName: string;
}

export const PredictedLineup: React.FC<PredictedLineupProps> = ({ teamName }) => {
  const [lineup, setLineup] = useState<LineupResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLineup();
  }, [teamName]);

  const loadLineup = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLineup(teamName);
      setLineup(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lineup');
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

  if (error || !lineup) {
    return (
      <div className="text-center py-4">
        <p className="text-xs text-pl-text-dim italic">Lineup data unavailable</p>
        <p className="text-xs text-pl-text-dim mt-1">Based on recent matches (off-season)</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Formation */}
      <div className="text-center">
        <span className="inline-block px-3 py-1 bg-pl-accent/20 text-pl-accent rounded text-sm font-medium">
          {lineup.formation}
        </span>
      </div>

      {/* Starting XI */}
      <div>
        <h4 className="text-xs text-pl-text-dim uppercase font-medium mb-2">Starting XI</h4>
        {lineup.start_xi.length > 0 ? (
          <div className="grid grid-cols-2 gap-2">
            {lineup.start_xi.slice(0, 11).map((player, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-pl-border/20 rounded px-2 py-1">
                <span className="text-xs font-bold text-pl-accent w-5">
                  {player.player?.number || idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white truncate">{player.player?.name || 'Unknown'}</p>
                  <p className="text-xs text-pl-text-dim">{player.player?.pos || 'N/A'}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-pl-text-dim italic">No lineup data available</p>
        )}
      </div>

      {/* Substitutes */}
      {lineup.substitutes.length > 0 && (
        <div>
          <h4 className="text-xs text-pl-text-dim uppercase font-medium mb-2">Substitutes</h4>
          <div className="flex flex-wrap gap-1">
            {lineup.substitutes.slice(0, 7).map((player, idx) => (
              <span key={idx} className="text-xs bg-pl-border/20 rounded px-2 py-1 text-pl-text">
                {player.player?.number || '?'}. {player.player?.name || 'Unknown'}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
