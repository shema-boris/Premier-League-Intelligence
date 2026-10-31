import React from 'react';
import { render, screen } from '@testing-library/react';
import { PredictionComparison } from './PredictionComparison';
import type { LearnedPrediction } from '../types';

const prediction: LearnedPrediction = {
  status: 'ready', message: 'Ready', home_team: 'Arsenal', away_team: 'Chelsea',
  kickoff_utc: new Date(Date.now() + 86400000).toISOString(), generated_at: new Date().toISOString(),
  probabilities: { home: .5, draw: .3, away: .2 },
  market_probabilities: { home: .4, draw: .3, away: .3 },
  model_version: 'logistic-v1-test', training_last_date: '2023-05-28',
  history_last_date: '2026-10-25', team_history_dates: { home: '2026-10-25', away: '2026-10-24' },
  features: {}, history_version: 'test', snapshot_saved: true,
};

test('compares learned probabilities with market probabilities', () => {
  render(<PredictionComparison prediction={prediction} />);
  expect(screen.getByText('50.0%')).toBeInTheDocument();
  expect(screen.getByText('+10.0 pp')).toBeInTheDocument();
  expect(screen.getByText(/logistic-v1-test/)).toBeInTheDocument();
});

test('sample matches do not show invented probabilities', () => {
  render(<PredictionComparison />);
  expect(screen.getByRole('status')).toHaveTextContent(/cached or sample/);
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('withholds stale history predictions', () => {
  render(<PredictionComparison prediction={{ ...prediction, status: 'stale', probabilities: null, message: 'Recent results are missing.' }} />);
  expect(screen.getByRole('status')).toHaveTextContent('Recent results are missing.');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('hides cached predictions after kickoff', () => {
  render(<PredictionComparison prediction={{ ...prediction, kickoff_utc: new Date(Date.now() - 1000).toISOString() }} />);
  expect(screen.getByRole('status')).toHaveTextContent(/kickoff has passed/);
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
