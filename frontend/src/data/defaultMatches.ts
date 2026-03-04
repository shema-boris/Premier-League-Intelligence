import type { AnalysisResponse } from '../types';

/**
 * Default match data shown to first-time visitors while fresh data loads.
 * This ensures no one ever sees a blank loading screen.
 * Data is representative of typical Premier League match analysis.
 */
export const defaultMatches: AnalysisResponse[] = [
  {
    home_team: "Arsenal",
    away_team: "Chelsea",
    kickoff_utc: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Arsenal",
    market_favorite_prob: 0.52,
    model_favorite: "Arsenal",
    model_favorite_prob: 0.55,
    discrepancies: [
      { outcome: "Home", market_probability: 0.52, model_probability: 0.55, delta: 0.03 },
      { outcome: "Draw", market_probability: 0.24, model_probability: 0.22, delta: -0.02 },
      { outcome: "Away", market_probability: 0.24, model_probability: 0.23, delta: -0.01 },
    ],
    conclusion: "Arsenal hold a slight edge at home with the model reinforcing market sentiment. The market assigns a 52% chance to Arsenal, while the model adjusts this to 55% based on recent form and team news impact.",
  },
  {
    home_team: "Liverpool",
    away_team: "Manchester City",
    kickoff_utc: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Liverpool",
    market_favorite_prob: 0.45,
    model_favorite: "Liverpool",
    model_favorite_prob: 0.48,
    discrepancies: [
      { outcome: "Home", market_probability: 0.45, model_probability: 0.48, delta: 0.03 },
      { outcome: "Draw", market_probability: 0.26, model_probability: 0.25, delta: -0.01 },
      { outcome: "Away", market_probability: 0.29, model_probability: 0.27, delta: -0.02 },
    ],
    conclusion: "A tightly contested fixture at Anfield. Liverpool's home advantage is reflected in both market and model probabilities. The model sees slightly more value in Liverpool given their defensive solidity this season.",
  },
  {
    home_team: "Manchester United",
    away_team: "Tottenham Hotspur",
    kickoff_utc: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Manchester United",
    market_favorite_prob: 0.42,
    model_favorite: "Manchester United",
    model_favorite_prob: 0.44,
    discrepancies: [
      { outcome: "Home", market_probability: 0.42, model_probability: 0.44, delta: 0.02 },
      { outcome: "Draw", market_probability: 0.28, model_probability: 0.27, delta: -0.01 },
      { outcome: "Away", market_probability: 0.30, model_probability: 0.29, delta: -0.01 },
    ],
    conclusion: "Manchester United are marginal favorites at Old Trafford. Both market and model agree on a close contest with United's home form providing a narrow edge over Spurs.",
  },
  {
    home_team: "Newcastle United",
    away_team: "Aston Villa",
    kickoff_utc: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Newcastle United",
    market_favorite_prob: 0.50,
    model_favorite: "Newcastle United",
    model_favorite_prob: 0.53,
    discrepancies: [
      { outcome: "Home", market_probability: 0.50, model_probability: 0.53, delta: 0.03 },
      { outcome: "Draw", market_probability: 0.25, model_probability: 0.23, delta: -0.02 },
      { outcome: "Away", market_probability: 0.25, model_probability: 0.24, delta: -0.01 },
    ],
    conclusion: "Newcastle are strong favorites at St James' Park. The model identifies additional value in Newcastle's home advantage, adjusting their win probability upward from 50% to 53%.",
  },
  {
    home_team: "Brighton",
    away_team: "West Ham United",
    kickoff_utc: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Brighton",
    market_favorite_prob: 0.48,
    model_favorite: "Brighton",
    model_favorite_prob: 0.51,
    discrepancies: [
      { outcome: "Home", market_probability: 0.48, model_probability: 0.51, delta: 0.03 },
      { outcome: "Draw", market_probability: 0.26, model_probability: 0.24, delta: -0.02 },
      { outcome: "Away", market_probability: 0.26, model_probability: 0.25, delta: -0.01 },
    ],
    conclusion: "Brighton favored at the Amex Stadium. The model sees slightly more value in Brighton's progressive style at home, pushing their probability to 51% from the market's 48%.",
  },
  {
    home_team: "Everton",
    away_team: "Wolverhampton Wanderers",
    kickoff_utc: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000 + 3 * 60 * 60 * 1000).toISOString(),
    market_favorite: "Everton",
    market_favorite_prob: 0.40,
    model_favorite: "Wolverhampton Wanderers",
    model_favorite_prob: 0.38,
    discrepancies: [
      { outcome: "Home", market_probability: 0.40, model_probability: 0.34, delta: -0.06 },
      { outcome: "Draw", market_probability: 0.28, model_probability: 0.28, delta: 0.0 },
      { outcome: "Away", market_probability: 0.32, model_probability: 0.38, delta: 0.06 },
    ],
    conclusion: "Significant market-model disagreement detected. While the market favors Everton at 40%, the model sees Wolves as slight favorites at 38% away win probability. This represents the largest discrepancy in the current matchweek.",
  },
];
