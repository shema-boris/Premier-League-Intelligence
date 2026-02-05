"""SQLite database for storing predictions and results."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Prediction:
    """A stored prediction record."""

    id: int | None
    match_id: str
    home_team: str
    away_team: str
    match_date: str
    prediction_time: str
    market_favorite: str
    market_favorite_prob: float
    model_favorite: str
    model_favorite_prob: float
    home_prob: float
    draw_prob: float
    away_prob: float
    home_odds: float
    draw_odds: float
    away_odds: float
    actual_result: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None


@dataclass
class ValidationMetrics:
    """Aggregated validation metrics."""

    total: int
    validated: int
    pending: int
    market_correct: int
    model_correct: int
    market_accuracy: float
    model_accuracy: float
    disagreements: int
    model_wins_when_disagreed: int


class PredictionDB:
    """SQLite database manager for predictions."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "predictions.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT UNIQUE NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    match_date TEXT NOT NULL,
                    prediction_time TEXT NOT NULL,
                    market_favorite TEXT NOT NULL,
                    market_favorite_prob REAL NOT NULL,
                    model_favorite TEXT NOT NULL,
                    model_favorite_prob REAL NOT NULL,
                    home_prob REAL NOT NULL,
                    draw_prob REAL NOT NULL,
                    away_prob REAL NOT NULL,
                    home_odds REAL NOT NULL,
                    draw_odds REAL NOT NULL,
                    away_odds REAL NOT NULL,
                    actual_result TEXT,
                    home_goals INTEGER,
                    away_goals INTEGER
                )
            """)
            conn.commit()

    def _make_match_id(self, home: str, away: str, match_date: str) -> str:
        """Create unique match identifier."""
        date_part = match_date[:10].replace("-", "")
        home_clean = home.lower().replace(" ", "_")[:20]
        away_clean = away.lower().replace(" ", "_")[:20]
        return f"{home_clean}_vs_{away_clean}_{date_part}"

    def save_prediction(
        self,
        *,
        home_team: str,
        away_team: str,
        match_date: str,
        market_favorite: str,
        market_favorite_prob: float,
        model_favorite: str,
        model_favorite_prob: float,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Prediction:
        """Save a prediction. Updates if match_id already exists."""
        match_id = self._make_match_id(home_team, away_team, match_date)
        prediction_time = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            row = conn.execute(
                "SELECT id, actual_result, home_goals, away_goals FROM predictions WHERE match_id = ?",
                (match_id,)
            ).fetchone()

            if row:
                # Update prediction but keep result if already validated
                conn.execute("""
                    UPDATE predictions SET
                        market_favorite = ?,
                        market_favorite_prob = ?,
                        model_favorite = ?,
                        model_favorite_prob = ?,
                        home_prob = ?,
                        draw_prob = ?,
                        away_prob = ?,
                        home_odds = ?,
                        draw_odds = ?,
                        away_odds = ?,
                        prediction_time = ?
                    WHERE match_id = ?
                """, (
                    market_favorite, market_favorite_prob,
                    model_favorite, model_favorite_prob,
                    home_prob, draw_prob, away_prob,
                    home_odds, draw_odds, away_odds,
                    prediction_time, match_id
                ))
                pred_id = row[0]
                actual_result, home_goals, away_goals = row[1], row[2], row[3]
            else:
                # Insert new
                cursor = conn.execute("""
                    INSERT INTO predictions (
                        match_id, home_team, away_team, match_date, prediction_time,
                        market_favorite, market_favorite_prob,
                        model_favorite, model_favorite_prob,
                        home_prob, draw_prob, away_prob,
                        home_odds, draw_odds, away_odds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id, home_team, away_team, match_date, prediction_time,
                    market_favorite, market_favorite_prob,
                    model_favorite, model_favorite_prob,
                    home_prob, draw_prob, away_prob,
                    home_odds, draw_odds, away_odds
                ))
                pred_id = cursor.lastrowid
                actual_result, home_goals, away_goals = None, None, None

            conn.commit()

        return Prediction(
            id=pred_id,
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            prediction_time=prediction_time,
            market_favorite=market_favorite,
            market_favorite_prob=market_favorite_prob,
            model_favorite=model_favorite,
            model_favorite_prob=model_favorite_prob,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            actual_result=actual_result,
            home_goals=home_goals,
            away_goals=away_goals,
        )

    def update_result(
        self, match_id: str, *, result: str, home_goals: int, away_goals: int
    ) -> bool:
        """Update a prediction with actual result. Returns True if found."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE predictions
                SET actual_result = ?, home_goals = ?, away_goals = ?
                WHERE match_id = ?
            """, (result, home_goals, away_goals, match_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_pending(self) -> list[Prediction]:
        """Get predictions without results."""
        return self._query("SELECT * FROM predictions WHERE actual_result IS NULL")

    def get_validated(self) -> list[Prediction]:
        """Get predictions with results."""
        return self._query("SELECT * FROM predictions WHERE actual_result IS NOT NULL")

    def get_all(self) -> list[Prediction]:
        """Get all predictions."""
        return self._query("SELECT * FROM predictions ORDER BY match_date DESC")

    def _query(self, sql: str, params: tuple = ()) -> list[Prediction]:
        """Execute query and return Prediction objects."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [Prediction(**dict(row)) for row in rows]

    def get_metrics(self) -> ValidationMetrics:
        """Calculate validation metrics."""
        validated = self.get_validated()
        pending = self.get_pending()

        market_correct = 0
        model_correct = 0
        disagreements = 0
        model_wins_disagreed = 0

        for p in validated:
            # Determine actual winner name
            if p.actual_result == "home":
                winner = p.home_team
            elif p.actual_result == "away":
                winner = p.away_team
            else:
                winner = "Draw"

            if p.market_favorite == winner:
                market_correct += 1
            if p.model_favorite == winner:
                model_correct += 1

            if p.market_favorite != p.model_favorite:
                disagreements += 1
                if p.model_favorite == winner:
                    model_wins_disagreed += 1

        n = len(validated)
        return ValidationMetrics(
            total=len(validated) + len(pending),
            validated=n,
            pending=len(pending),
            market_correct=market_correct,
            model_correct=model_correct,
            market_accuracy=round(market_correct / n * 100, 1) if n else 0.0,
            model_accuracy=round(model_correct / n * 100, 1) if n else 0.0,
            disagreements=disagreements,
            model_wins_when_disagreed=model_wins_disagreed,
        )
