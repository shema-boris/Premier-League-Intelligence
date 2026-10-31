import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { LearnedMetricsResponse } from '../types';

export const ModelPerformance: React.FC = () => {
  const [metrics, setMetrics] = useState<LearnedMetricsResponse | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await api.learnedMetrics();
        if (active) { setMetrics(data); setFailed(false); }
      } catch {
        if (active) setFailed(true);
      }
    };
    load();
    const timer = window.setInterval(load, 60 * 1000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return <section className="px-4 py-3 border-b border-pl-border bg-pl-card" aria-label="Live prediction performance">
    <h2 className="text-sm font-semibold text-pl-text-bright">Live prediction tracking</h2>
    {failed ? <p className="text-xs text-pl-text-dim mt-1">Performance data unavailable. No current metrics are confirmed.</p>
      : !metrics ? <p className="text-xs text-pl-text-dim mt-1">Loading performance data…</p>
      : <>
        <p className="text-xs text-pl-text-dim mt-1">{metrics.total} recorded · {metrics.settled} settled · {metrics.pending} pending</p>
        {!metrics.settled && <p className="text-xs text-pl-text-dim mt-1">No settled predictions yet. Results will appear after recorded matches finish and results are refreshed.</p>}
        {metrics.versions.filter(version => version.model).map(version => <div key={version.model_version} className="text-xs text-pl-text-dim mt-2">
          <p>{version.model_version}: {(version.model!.accuracy * 100).toFixed(1)}% accuracy across {version.model!.matches} scored matches.</p>
          <p>Log loss {version.model!.log_loss.toFixed(3)} · Brier {version.model!.brier_multiclass_sum.toFixed(3)} (lower is better).</p>
          {version.market_comparison.paired_matches > 0 && <p>
            Same {version.market_comparison.paired_matches} fixtures: model log loss {version.market_comparison.model!.log_loss.toFixed(3)}, market {version.market_comparison.market!.log_loss.toFixed(3)}.
          </p>}
        </div>)}
      </>}
    <p className="text-xs text-pl-text-dim mt-1">First pre-kickoff predictions, grouped by model version. Separate from historical test results.</p>
  </section>;
};
