import React from 'react';
import type { LearnedPrediction } from '../types';

export function predictionReady(prediction?: LearnedPrediction | null): boolean {
  return prediction?.status === 'ready' && !!prediction.probabilities &&
    new Date(prediction.kickoff_utc).getTime() > Date.now() &&
    Date.now() - new Date(prediction.generated_at).getTime() < 12 * 60 * 60 * 1000;
}

export const PredictionComparison: React.FC<{ prediction?: LearnedPrediction | null }> = ({ prediction }) => {
  const ready = predictionReady(prediction);
  return (
    <section className="bg-pl-dark rounded-lg p-4" aria-label="Historical model prediction">
      <h3 className="text-sm font-semibold text-pl-text-bright mb-3">Match prediction</h3>
      {!ready ? (
        <p className="text-sm text-pl-text-dim" role="status">
          {prediction?.status === 'ready'
            ? 'This prediction has expired or kickoff has passed. Refresh for current data.'
            : prediction?.message || 'A trained prediction is not available for this cached or sample match.'}
        </p>
      ) : (
        <>
          <table className="w-full text-sm text-left">
            <caption className="sr-only">Model and market outcome probabilities</caption>
            <thead className="text-pl-text-dim"><tr><th>Outcome</th><th>Model</th><th>Market</th><th>Difference</th></tr></thead>
            <tbody>
              {(['home', 'draw', 'away'] as const).map(outcome => {
                const model = prediction!.probabilities![outcome];
                const market = prediction!.market_probabilities?.[outcome];
                const delta = market == null ? null : (model - market) * 100;
                return <tr key={outcome} className="border-t border-pl-border">
                  <th className="py-2 capitalize">{outcome}</th>
                  <td>{(model * 100).toFixed(1)}%</td>
                  <td>{market == null ? 'Unavailable' : `${(market * 100).toFixed(1)}%`}</td>
                  <td>{delta == null ? '—' : `${delta >= 0 ? '+' : ''}${delta.toFixed(1)} pp`}</td>
                </tr>;
              })}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-pl-text-dim">Based on team strength, recent form, goals and rest. These are estimates.</p>
          <p className="mt-2 text-xs text-pl-text-dim">
            Results through {prediction!.history_last_date}. Team results: home {prediction!.team_history_dates.home}, away {prediction!.team_history_dates.away}.
          </p>
          <p className="mt-1 text-xs text-pl-text-dim">
            Model {prediction!.model_version} · Trained through {prediction!.training_last_date}
          </p>
          {!prediction!.snapshot_saved && <p className="mt-2 text-xs text-pl-accent-orange">Prediction could not be recorded for future evaluation.</p>}
        </>
      )}
    </section>
  );
};
