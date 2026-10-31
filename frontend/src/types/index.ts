export interface MatchResponse {
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
}

export interface Discrepancy {
  outcome: string;
  market_probability: number;
  model_probability: number;
  delta: number;
}

export interface AnalysisResponse {
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  market_favorite: string;
  market_favorite_prob: number;
  model_favorite: string;
  model_favorite_prob: number;
  discrepancies: Discrepancy[];
  conclusion: string;
  learned_prediction?: LearnedPrediction | null;
}

export interface LearnedPrediction {
  status: 'ready' | 'unavailable' | 'stale' | 'started';
  message: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  generated_at: string;
  probabilities: Record<'home' | 'draw' | 'away', number> | null;
  market_probabilities: Record<'home' | 'draw' | 'away', number> | null;
  model_version: string | null;
  training_last_date: string | null;
  history_last_date: string | null;
  team_history_dates: Partial<Record<'home' | 'away', string>>;
  features: Record<string, number>;
  history_version: string | null;
  snapshot_saved: boolean;
}

export interface ProbabilityMetrics {
  matches: number;
  accuracy: number;
  log_loss: number;
  brier_multiclass_sum: number;
}

export interface LearnedMetricsResponse {
  total: number;
  settled: number;
  pending: number;
  protocol: string;
  versions: Array<{
    model_version: string;
    total: number;
    settled: number;
    pending: number;
    invalid_probabilities: number;
    model: ProbabilityMetrics | null;
    market_comparison: {
      paired_matches: number;
      model: ProbabilityMetrics | null;
      market: ProbabilityMetrics | null;
    };
  }>;
}

export interface PredictionResponse {
  match_id: string;
  home_team: string;
  away_team: string;
  match_date: string;
  market_favorite: string;
  market_favorite_prob: number;
  model_favorite: string;
  model_favorite_prob: number;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
  actual_result: string | null;
  home_goals: number | null;
  away_goals: number | null;
  is_validated: boolean;
}

export interface MetricsResponse {
  total: number;
  validated: number;
  pending: number;
  market_correct: number;
  model_correct: number;
  market_accuracy: number;
  model_accuracy: number;
  disagreements: number;
  model_wins_when_disagreed: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  predictions_count: number;
}

export interface TeamFormMatch {
  opponent: string;
  result: string;
  score: string;
  home: boolean;
  date: string;
}

export interface TeamFormResponse {
  team_name: string;
  matches: TeamFormMatch[];
  form_string: string;
  goals_scored: number;
  goals_conceded: number;
  wins: number;
  draws: number;
  losses: number;
}

export interface LineupPlayer {
  player: {
    id: number;
    name: string;
    number: number;
    pos: string;
  };
}

export interface LineupResponse {
  team_name: string;
  formation: string;
  start_xi: LineupPlayer[];
  substitutes: LineupPlayer[];
}

export interface HeadToHeadMatch {
  home_team: string;
  away_team: string;
  score: string;
  winner: string;
  date: string;
}

export interface HeadToHeadResponse {
  team1: string;
  team2: string;
  matches: HeadToHeadMatch[];
  team1_wins: number;
  team2_wins: number;
  draws: number;
}

export interface TeamLogoResponse {
  team_name: string;
  logo_url: string | null;
}
