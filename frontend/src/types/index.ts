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
