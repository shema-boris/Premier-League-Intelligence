import React from 'react';
import { render, screen } from '@testing-library/react';
import { ModelPerformance } from './ModelPerformance';
import { api } from '../api/client';

jest.mock('../api/client', () => ({ api: { learnedMetrics: jest.fn() } }));

test('shows an honest empty prospective sample', async () => {
  (api.learnedMetrics as jest.Mock).mockResolvedValue({ total: 2, settled: 0, pending: 2, versions: [] });
  render(<ModelPerformance />);
  expect(await screen.findByText(/2 recorded · 0 settled · 2 pending/)).toBeInTheDocument();
  expect(screen.getByText(/No settled predictions yet/)).toBeInTheDocument();
  expect(screen.queryByText(/% accuracy/)).not.toBeInTheDocument();
});

test('shows settled performance and a paired market comparison', async () => {
  const metrics = { matches: 10, accuracy: .6, log_loss: .9, brier_multiclass_sum: .5 };
  (api.learnedMetrics as jest.Mock).mockResolvedValue({ total: 12, settled: 10, pending: 2,
    versions: [{ model_version: 'v1', model: metrics,
      market_comparison: { paired_matches: 10, model: metrics, market: { ...metrics, log_loss: 1.0 } } }] });
  render(<ModelPerformance />);
  expect(await screen.findByText(/60.0% accuracy across 10 scored matches/)).toBeInTheDocument();
  expect(screen.getByText(/Same 10 fixtures: model log loss 0.900, market 1.000/)).toBeInTheDocument();
});

test('reports metrics failure without displaying zero accuracy', async () => {
  (api.learnedMetrics as jest.Mock).mockRejectedValue(new Error('Offline'));
  render(<ModelPerformance />);
  expect(await screen.findByText(/Performance data unavailable/)).toBeInTheDocument();
  expect(screen.queryByText(/% accuracy/)).not.toBeInTheDocument();
});
