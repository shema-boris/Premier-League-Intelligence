"""FastAPI backend for Premier League Market Intelligence."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crew.crew_config import run_offline_pipeline
from data_sources import OddsAPIClient
from data_sources.football_api import FootballAPIClient
from dotenv import load_dotenv
from schemas.match import Match
from schemas.odds import RawOdds
from schemas.team_news import MatchTeamNews, TeamNews
from validation.database import PredictionDB, ValidationMetrics

load_dotenv()


# --- Response Models ---

class MatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    home_team: str
    away_team: str
    kickoff_utc: str
    home_odds: float
    draw_odds: float
    away_odds: float


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    match_id: str
    home_team: str
    away_team: str
    match_date: str
    market_favorite: str
    market_favorite_prob: float
    model_favorite: str
    model_favorite_prob: float
    home_odds: float
    draw_odds: float
    away_odds: float
    actual_result: str | None
    home_goals: int | None
    away_goals: int | None
    is_validated: bool


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    home_team: str
    away_team: str
    kickoff_utc: str
    market_favorite: str
    market_favorite_prob: float
    model_favorite: str
    model_favorite_prob: float
    discrepancies: list[dict[str, Any]]
    conclusion: str


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    total: int
    validated: int
    pending: int
    market_correct: int
    model_correct: int
    market_accuracy: float
    model_accuracy: float
    disagreements: int
    model_wins_when_disagreed: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    predictions_count: int


class TeamFormResponse(BaseModel):
    """Team's last 5 matches form."""
    model_config = ConfigDict(extra="forbid")
    
    team_name: str
    matches: list[dict[str, Any]]  # List of recent match results
    form_string: str  # e.g., "W-W-D-L-W"
    goals_scored: int
    goals_conceded: int
    wins: int
    draws: int
    losses: int


class LineupResponse(BaseModel):
    """Predicted lineup for a team."""
    model_config = ConfigDict(extra="forbid")
    
    team_name: str
    formation: str
    start_xi: list[dict[str, Any]]
    substitutes: list[dict[str, Any]]


class HeadToHeadResponse(BaseModel):
    """Head-to-head stats between two teams."""
    model_config = ConfigDict(extra="forbid")
    
    team1: str
    team2: str
    matches: list[dict[str, Any]]  # Last N H2H matches
    team1_wins: int
    team2_wins: int
    draws: int


class TeamLogoResponse(BaseModel):
    """Team logo URL."""
    model_config = ConfigDict(extra="forbid")
    
    team_name: str
    logo_url: str | None


class EnhancedAnalysisResponse(BaseModel):
    """Analysis with matchweek and date info."""
    model_config = ConfigDict(extra="forbid")
    
    home_team: str
    away_team: str
    kickoff_utc: str
    kickoff_date: str  # e.g., "2024-02-03"
    matchweek: str | None  # e.g., "Regular Season - 23"
    market_favorite: str
    market_favorite_prob: float
    model_favorite: str
    model_favorite_prob: float
    discrepancies: list[dict[str, Any]]
    conclusion: str


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = PredictionDB()
    app.state.logo_cache = {}  # Initialize logo cache
    yield
    # Shutdown (nothing to clean up for SQLite)


app = FastAPI(
    title="Premier League Market Intelligence API",
    description="REST API for football match analysis and predictions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\\.0\\.0\\.1)(:\\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db: PredictionDB = app.state.db
    predictions = db.get_all()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        predictions_count=len(predictions),
    )


@app.get("/matches", response_model=list[MatchResponse])
async def get_upcoming_matches():
    """Get all upcoming Premier League matches with odds."""
    try:
        odds_client = OddsAPIClient.from_env()
        matches = odds_client.get_all_upcoming_matches()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch matches: {e}")

    return [
        MatchResponse(
            home_team=m["home_team"],
            away_team=m["away_team"],
            kickoff_utc=m.get("kickoff_utc", ""),
            home_odds=m["odds"].home_win,
            draw_odds=m["odds"].draw,
            away_odds=m["odds"].away_win,
        )
        for m in matches
    ]


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_match(home_team: str, away_team: str):
    """Analyze a specific match and return predictions."""
    try:
        odds_client = OddsAPIClient.from_env()
        matches = odds_client.get_all_upcoming_matches()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch matches: {e}")

    # Find the requested match
    target = None
    for m in matches:
        if m["home_team"].lower() == home_team.lower() and m["away_team"].lower() == away_team.lower():
            target = m
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Match not found: {home_team} vs {away_team}")

    # Build schemas
    kickoff_str = target.get("kickoff_utc", "")
    if kickoff_str:
        kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
    else:
        kickoff = datetime.now(timezone.utc)

    match = Match(
        league="Premier League",
        home_team=target["home_team"],
        away_team=target["away_team"],
        kickoff_utc=kickoff,
    )
    raw_odds = target["odds"]
    team_news = MatchTeamNews(home=TeamNews(absences=[]), away=TeamNews(absences=[]))

    # Run pipeline
    report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news, verbose=False)

    # Save prediction
    db: PredictionDB = app.state.db
    db.save_prediction(
        home_team=match.home_team,
        away_team=match.away_team,
        match_date=match.kickoff_utc.isoformat(),
        market_favorite=report.market_favorite.label,
        market_favorite_prob=report.market_favorite.probability,
        model_favorite=report.model_favorite.label,
        model_favorite_prob=report.model_favorite.probability,
        home_prob=report.discrepancies[0].model_probability if report.discrepancies else 0,
        draw_prob=report.discrepancies[1].model_probability if len(report.discrepancies) > 1 else 0,
        away_prob=report.discrepancies[2].model_probability if len(report.discrepancies) > 2 else 0,
        home_odds=raw_odds.home_win,
        draw_odds=raw_odds.draw,
        away_odds=raw_odds.away_win,
    )

    return AnalysisResponse(
        home_team=match.home_team,
        away_team=match.away_team,
        kickoff_utc=match.kickoff_utc.isoformat(),
        market_favorite=report.market_favorite.label,
        market_favorite_prob=report.market_favorite.probability,
        model_favorite=report.model_favorite.label,
        model_favorite_prob=report.model_favorite.probability,
        discrepancies=[
            {
                "outcome": d.outcome,
                "market_probability": d.market_probability,
                "model_probability": d.model_probability,
                "delta": d.delta,
            }
            for d in report.discrepancies
        ],
        conclusion=report.conclusion,
    )


@app.post("/analyze-all", response_model=list[AnalysisResponse])
async def analyze_all_matches():
    """Analyze all upcoming matches."""
    try:
        odds_client = OddsAPIClient.from_env()
        matches = odds_client.get_all_upcoming_matches()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch matches: {e}")

    if not matches:
        return []

    db: PredictionDB = app.state.db
    results = []

    for m in matches:
        kickoff_str = m.get("kickoff_utc", "")
        if kickoff_str:
            kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
        else:
            kickoff = datetime.now(timezone.utc)

        match = Match(
            league="Premier League",
            home_team=m["home_team"],
            away_team=m["away_team"],
            kickoff_utc=kickoff,
        )
        raw_odds = m["odds"]
        team_news = MatchTeamNews(home=TeamNews(absences=[]), away=TeamNews(absences=[]))

        report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news, verbose=False)

        # Save prediction
        db.save_prediction(
            home_team=match.home_team,
            away_team=match.away_team,
            match_date=match.kickoff_utc.isoformat(),
            market_favorite=report.market_favorite.label,
            market_favorite_prob=report.market_favorite.probability,
            model_favorite=report.model_favorite.label,
            model_favorite_prob=report.model_favorite.probability,
            home_prob=report.discrepancies[0].model_probability if report.discrepancies else 0,
            draw_prob=report.discrepancies[1].model_probability if len(report.discrepancies) > 1 else 0,
            away_prob=report.discrepancies[2].model_probability if len(report.discrepancies) > 2 else 0,
            home_odds=raw_odds.home_win,
            draw_odds=raw_odds.draw,
            away_odds=raw_odds.away_win,
        )

        results.append(AnalysisResponse(
            home_team=match.home_team,
            away_team=match.away_team,
            kickoff_utc=match.kickoff_utc.isoformat(),
            market_favorite=report.market_favorite.label,
            market_favorite_prob=report.market_favorite.probability,
            model_favorite=report.model_favorite.label,
            model_favorite_prob=report.model_favorite.probability,
            discrepancies=[
                {
                    "outcome": d.outcome,
                    "market_probability": d.market_probability,
                    "model_probability": d.model_probability,
                    "delta": d.delta,
                }
                for d in report.discrepancies
            ],
            conclusion=report.conclusion,
        ))

    return results


@app.get("/predictions", response_model=list[PredictionResponse])
async def get_predictions(validated_only: bool = False, pending_only: bool = False):
    """Get stored predictions."""
    db: PredictionDB = app.state.db

    if validated_only:
        predictions = db.get_validated()
    elif pending_only:
        predictions = db.get_pending()
    else:
        predictions = db.get_all()

    return [
        PredictionResponse(
            match_id=p.match_id,
            home_team=p.home_team,
            away_team=p.away_team,
            match_date=p.match_date,
            market_favorite=p.market_favorite,
            market_favorite_prob=p.market_favorite_prob,
            model_favorite=p.model_favorite,
            model_favorite_prob=p.model_favorite_prob,
            home_odds=p.home_odds,
            draw_odds=p.draw_odds,
            away_odds=p.away_odds,
            actual_result=p.actual_result,
            home_goals=p.home_goals,
            away_goals=p.away_goals,
            is_validated=p.actual_result is not None,
        )
        for p in predictions
    ]


@app.get("/metrics", response_model=MetricsResponse)
async def get_validation_metrics():
    """Get prediction accuracy metrics."""
    db: PredictionDB = app.state.db
    metrics = db.get_metrics()

    return MetricsResponse(
        total=metrics.total,
        validated=metrics.validated,
        pending=metrics.pending,
        market_correct=metrics.market_correct,
        model_correct=metrics.model_correct,
        market_accuracy=metrics.market_accuracy,
        model_accuracy=metrics.model_accuracy,
        disagreements=metrics.disagreements,
        model_wins_when_disagreed=metrics.model_wins_when_disagreed,
    )


@app.post("/validate")
async def run_validation():
    """Validate pending predictions against actual results."""
    from validation.backtest import BacktestRunner

    db: PredictionDB = app.state.db
    runner = BacktestRunner(db)
    results = runner.validate_pending()

    return {
        "updated": results["updated"],
        "still_pending": results["still_pending"],
        "metrics": db.get_metrics().__dict__,
    }


@app.get("/team-form/{team_name}", response_model=TeamFormResponse)
async def get_team_form(team_name: str):
    """Get last 5 matches for a team."""
    try:
        football_client = FootballAPIClient.from_env()
        
        # Get team ID
        team_id = football_client.get_team_id_by_name(team_name)
        if not team_id:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_name}")
        
        # Get last 5 fixtures
        fixtures = football_client.get_team_last_n_fixtures(team_id, n=5)
        
        if not fixtures:
            return TeamFormResponse(
                team_name=team_name,
                matches=[],
                form_string="",
                goals_scored=0,
                goals_conceded=0,
                wins=0,
                draws=0,
                losses=0,
            )
        
        # Process fixtures
        matches = []
        form_chars = []
        total_scored = 0
        total_conceded = 0
        wins = 0
        draws = 0
        losses = 0
        
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_goals = goals.get("home", 0)
            away_goals = goals.get("away", 0)
            
            # Determine if team was home or away
            is_home = teams.get("home", {}).get("id") == team_id
            team_goals = home_goals if is_home else away_goals
            opponent_goals = away_goals if is_home else home_goals
            opponent_name = teams.get("away" if is_home else "home", {}).get("name", "Unknown")
            
            total_scored += team_goals
            total_conceded += opponent_goals
            
            # Determine result
            if team_goals > opponent_goals:
                result = "W"
                wins += 1
            elif team_goals < opponent_goals:
                result = "L"
                losses += 1
            else:
                result = "D"
                draws += 1
            
            form_chars.append(result)
            
            matches.append({
                "opponent": opponent_name,
                "result": result,
                "score": f"{team_goals}-{opponent_goals}",
                "home": is_home,
                "date": fixture.get("fixture", {}).get("date", ""),
            })
        
        return TeamFormResponse(
            team_name=team_name,
            matches=matches,
            form_string="-".join(form_chars),
            goals_scored=total_scored,
            goals_conceded=total_conceded,
            wins=wins,
            draws=draws,
            losses=losses,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch team form: {e}")


@app.get("/lineup/{team_name}", response_model=LineupResponse)
async def get_predicted_lineup(team_name: str):
    """Get predicted lineup for a team based on recent matches."""
    try:
        football_client = FootballAPIClient.from_env()
        
        # Get team ID
        team_id = football_client.get_team_id_by_name(team_name)
        if not team_id:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_name}")
        
        # Get predicted lineup
        lineup_data = football_client.get_predicted_lineup(team_id)
        
        return LineupResponse(
            team_name=team_name,
            formation=lineup_data.get("formation", "4-3-3"),
            start_xi=lineup_data.get("start_xi", []),
            substitutes=lineup_data.get("substitutes", []),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch lineup: {e}")


@app.get("/team-logo/{team_name}", response_model=TeamLogoResponse)
async def get_team_logo(team_name: str):
    """Get team logo URL with aggressive caching (7 days)."""
    try:
        football_client = FootballAPIClient.from_env()
        
        # Check cache first (logos rarely change)
        cache_key = f"logo_{team_name.lower().replace(' ', '_')}"
        
        # Simple in-memory cache for this session
        if not hasattr(app.state, 'logo_cache'):
            app.state.logo_cache = {}
        
        if cache_key in app.state.logo_cache:
            return TeamLogoResponse(
                team_name=team_name,
                logo_url=app.state.logo_cache[cache_key]
            )
        
        # Fetch from API
        logo_url = football_client.get_team_logo(team_name)
        
        # Cache the result
        if logo_url:
            app.state.logo_cache[cache_key] = logo_url
        
        return TeamLogoResponse(
            team_name=team_name,
            logo_url=logo_url
        )
    except Exception as e:
        # Return None logo on error - frontend will show fallback
        return TeamLogoResponse(
            team_name=team_name,
            logo_url=None
        )


@app.get("/head-to-head/{team1}/{team2}", response_model=HeadToHeadResponse)
async def get_head_to_head(team1: str, team2: str):
    """Get head-to-head stats between two teams."""
    try:
        football_client = FootballAPIClient.from_env()
        
        # Get team IDs
        team1_id = football_client.get_team_id_by_name(team1)
        team2_id = football_client.get_team_id_by_name(team2)
        
        if not team1_id or not team2_id:
            raise HTTPException(status_code=404, detail="One or both teams not found")
        
        # Get H2H fixtures
        fixtures = football_client.get_head_to_head(team1_id, team2_id, last_n=5)
        
        if not fixtures:
            return HeadToHeadResponse(
                team1=team1,
                team2=team2,
                matches=[],
                team1_wins=0,
                team2_wins=0,
                draws=0,
            )
        
        # Process fixtures
        matches = []
        team1_wins = 0
        team2_wins = 0
        draws = 0
        
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            goals = fixture.get("goals", {})
            home_goals = goals.get("home", 0)
            away_goals = goals.get("away", 0)
            
            home_team_id = teams.get("home", {}).get("id")
            home_team_name = teams.get("home", {}).get("name", "")
            away_team_name = teams.get("away", {}).get("name", "")
            
            # Determine winner
            if home_goals > away_goals:
                winner = home_team_name
                if home_team_id == team1_id:
                    team1_wins += 1
                else:
                    team2_wins += 1
            elif away_goals > home_goals:
                winner = away_team_name
                if home_team_id == team1_id:
                    team2_wins += 1
                else:
                    team1_wins += 1
            else:
                winner = "Draw"
                draws += 1
            
            matches.append({
                "home_team": home_team_name,
                "away_team": away_team_name,
                "score": f"{home_goals}-{away_goals}",
                "winner": winner,
                "date": fixture.get("fixture", {}).get("date", ""),
            })
        
        return HeadToHeadResponse(
            team1=team1,
            team2=team2,
            matches=matches,
            team1_wins=team1_wins,
            team2_wins=team2_wins,
            draws=draws,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch head-to-head: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
