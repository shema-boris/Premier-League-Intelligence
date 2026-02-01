import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { TeamFormResponse } from '../types';

interface TeamFormProps {
  teamName: string;
}

export const TeamForm: React.FC<TeamFormProps> = ({ teamName }) => {
  const [form, setForm] = useState<TeamFormResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadForm();
  }, [teamName]);

  const loadForm = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTeamForm(teamName);
      setForm(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load form');
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

  if (error || !form) {
    return (
      <div className="text-center py-8 px-4">
        <div className="bg-pl-border/30 rounded-lg p-4 max-w-md mx-auto">
          <svg className="w-8 h-8 text-pl-text-dim mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-pl-text-dim mb-2">Team form data unavailable</p>
          <p className="text-xs text-pl-text-dim/70">
            Backend server needs to be restarted with Football API key configured
          </p>
        </div>
      </div>
    );
  }

  const getResultColor = (result: string) => {
    switch (result) {
      case 'W': return 'bg-green-500';
      case 'D': return 'bg-gray-500';
      case 'L': return 'bg-red-500';
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className="space-y-3">
      {/* Form String */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-pl-text-dim uppercase font-medium">Last 5:</span>
        <div className="flex gap-1">
          {form.form_string.split('-').map((result, idx) => (
            <div
              key={idx}
              className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold text-white ${getResultColor(result)}`}
            >
              {result}
            </div>
          ))}
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-pl-border/30 rounded p-2">
          <p className="text-xs text-pl-text-dim">Goals</p>
          <p className="text-sm font-bold text-white">{form.goals_scored}</p>
        </div>
        <div className="bg-pl-border/30 rounded p-2">
          <p className="text-xs text-pl-text-dim">Conceded</p>
          <p className="text-sm font-bold text-white">{form.goals_conceded}</p>
        </div>
        <div className="bg-pl-border/30 rounded p-2">
          <p className="text-xs text-pl-text-dim">Record</p>
          <p className="text-sm font-bold text-white">
            {form.wins}W-{form.draws}D-{form.losses}L
          </p>
        </div>
      </div>

      {/* Recent Matches */}
      <div className="space-y-1">
        {form.matches.slice(0, 3).map((match, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs bg-pl-border/20 rounded px-2 py-1">
            <span className="text-pl-text-dim">
              {match.home ? 'vs' : '@'} {match.opponent}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-pl-text">{match.score}</span>
              <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold text-white ${getResultColor(match.result)}`}>
                {match.result}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
