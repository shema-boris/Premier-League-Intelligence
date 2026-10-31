import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
import { api } from './api/client';

jest.mock('./api/client', () => ({ api: { analyzeAll: jest.fn(), learnedMetrics: jest.fn() } }));

test('renders dashboard and withholds predictions for sample matches when API fails', async () => {
  (api.analyzeAll as jest.Mock).mockRejectedValue(new Error('Offline'));
  (api.learnedMetrics as jest.Mock).mockRejectedValue(new Error('Offline'));
  localStorage.clear();
  render(<App />);
  expect(screen.getByText('PL MARKET INTELLIGENCE')).toBeInTheDocument();
  expect(await screen.findByRole('status')).toHaveTextContent(/cached or sample/);
});
