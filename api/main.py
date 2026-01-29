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


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = PredictionDB()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
