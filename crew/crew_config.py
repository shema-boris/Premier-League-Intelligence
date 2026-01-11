from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict

from agents.discrepancy_agent import DiscrepancyAnalysisAgent
from agents.impact_agent import ImpactModelingAgent
from agents.odds_agent import OddsAgent
from agents.report_agent import ReportWriterAgent
from agents.team_news_agent import TeamNewsAgent
from schemas.discrepancy import MarketDiscrepancy
from schemas.impact import AdjustedProbabilities, ExpectedGoalsAdjustment
from schemas.match import Match
from schemas.odds import ImpliedProbabilities, RawOdds
from schemas.report import MarketAnalysisReport
from schemas.team_news import MatchTeamNews

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME") or os.getenv("GOOGLE_MODEL_NAME") or "gemini-2.0-flash"
LEAGUE_SCOPE = "Premier League"
MARKET_SCOPE = "1X2"


class ImpactModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xg_adjustment: ExpectedGoalsAdjustment
    adjusted_probabilities: AdjustedProbabilities


class DiscrepancyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discrepancies: list[MarketDiscrepancy]


@dataclass(slots=True)
class PipelineContext:
    match: Match
    raw_odds: RawOdds
    team_news: MatchTeamNews
    implied: ImpliedProbabilities | None = None
    validated_team_news: MatchTeamNews | None = None
    xg_adjustment: ExpectedGoalsAdjustment | None = None
    adjusted_probabilities: AdjustedProbabilities | None = None
    discrepancies: list[MarketDiscrepancy] | None = None
    report: MarketAnalysisReport | None = None


class _BasePipelineTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    result_as_answer: bool = True
    ctx: PipelineContext

    def _require(self, value: Any, name: str) -> Any:
        if value is None:
            raise ValueError(f"Pipeline context missing required value: {name}")
        return value


class EmitInputsTool(_BasePipelineTool):
    name: str = "emit_inputs"
    description: str = "Emit the validated mock inputs (match, raw odds, and team news) without modification."

    def _run(self) -> str:
        print("\n[0] Match")
        print(self.ctx.match.model_dump_json(indent=2))
        print("\n[1] Raw Odds")
        print(self.ctx.raw_odds.model_dump_json(indent=2))
        print("\n[2] Team News (raw)")
        print(self.ctx.team_news.model_dump_json(indent=2))
        return self.ctx.match.model_dump_json()


class ComputeImpliedProbabilitiesTool(_BasePipelineTool):
    name: str = "compute_implied_probabilities"
    description: str = "Convert raw 1X2 odds into normalized implied probabilities and record overround."

    def _run(self) -> str:
        implied = OddsAgent.implied_probabilities(self.ctx.raw_odds)
        self.ctx.implied = implied
        print("\n[3] Market Implied Probabilities (normalized; overround reported separately)")
        print(implied.model_dump_json(indent=2))
        return implied.model_dump_json()


class ValidateTeamNewsTool(_BasePipelineTool):
    name: str = "validate_team_news"
    description: str = "Validate team news against strict schema, preserving values (no inference)."

    def _run(self) -> str:
        validated = TeamNewsAgent.validate(self.ctx.team_news)
        self.ctx.validated_team_news = validated
        print("\n[4] Team News (validated)")
        print(validated.model_dump_json(indent=2))
        return validated.model_dump_json()


class ModelImpactTool(_BasePipelineTool):
    name: str = "model_impact"
    description: str = "Apply deterministic xG-based interpretability adjustments and emit adjusted probabilities."

    def _run(self) -> str:
        implied = self._require(self.ctx.implied, "implied")
        team_news = self._require(self.ctx.validated_team_news, "validated_team_news")
        xg_adj, adjusted = ImpactModelingAgent.model(implied, team_news)
        self.ctx.xg_adjustment = xg_adj
        self.ctx.adjusted_probabilities = adjusted
        output = ImpactModelOutput(xg_adjustment=xg_adj, adjusted_probabilities=adjusted)
        print("\n[5] Expected Goals Adjustment")
        print(xg_adj.model_dump_json(indent=2))
        print("\n[6] Adjusted Probabilities (team-news interpretability layer)")
        print(adjusted.model_dump_json(indent=2))
        return output.model_dump_json()


class AnalyzeDiscrepanciesTool(_BasePipelineTool):
    name: str = "analyze_discrepancies"
    description: str = "Compare market-implied vs adjusted probabilities to surface deltas."

    def _run(self) -> str:
        implied = self._require(self.ctx.implied, "implied")
        adjusted = self._require(self.ctx.adjusted_probabilities, "adjusted_probabilities")
        discrepancies = DiscrepancyAnalysisAgent.analyze(implied, adjusted)
        self.ctx.discrepancies = discrepancies
        output = DiscrepancyOutput(discrepancies=discrepancies)
        print("\n[7] Market Discrepancies (sorted by absolute delta)")
        print(output.model_dump_json(indent=2))
        return output.model_dump_json()


class WriteReportTool(_BasePipelineTool):
    name: str = "write_report"
    description: str = "Write a neutral market intelligence memo (no recommendations) as a strict schema object."

    def _run(self) -> str:
        team_news = self._require(self.ctx.validated_team_news, "validated_team_news")
        discrepancies = self._require(self.ctx.discrepancies, "discrepancies")
        report = ReportWriterAgent.write(self.ctx.match, team_news, discrepancies)
        self.ctx.report = report
        print("\n[8] Market Analysis Report (schema) — NO RECOMMENDATIONS")
        print(report.model_dump_json(indent=2))
        return report.model_dump_json()


def build_premier_league_crew(
    *,
    match: Match,
    raw_odds: RawOdds,
    team_news: MatchTeamNews,
    verbose: bool = True,
) -> Crew:
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    has_vertex = bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
    if not (has_gemini_key or has_vertex):
        raise ValueError(
            "Missing Gemini credentials. Set GEMINI_API_KEY (or GOOGLE_API_KEY) for the Gemini API, "
            "or set GOOGLE_CLOUD_PROJECT (and related Vertex config) for Vertex AI."
        )

    llm = LLM(
        model=f"google/{MODEL_NAME}",
        temperature=0.0,
        timeout=120,
    )

    ctx = PipelineContext(match=match, raw_odds=raw_odds, team_news=team_news)

    inputs_agent = Agent(
        role="Input Validator",
        goal="Emit validated mock inputs without modification.",
        backstory=f"You operate strictly within {LEAGUE_SCOPE} scope and do not infer missing data.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[EmitInputsTool(ctx=ctx)],
    )
    odds_agent = Agent(
        role="Odds Normalization Analyst",
        goal="Convert raw odds into implied probabilities deterministically.",
        backstory=f"You compute {MARKET_SCOPE} implied probabilities and overround without editorialization.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[ComputeImpliedProbabilitiesTool(ctx=ctx)],
    )
    team_news_agent = Agent(
        role="Team News Schema Steward",
        goal="Validate team news strictly and preserve raw values.",
        backstory="You enforce Pydantic contracts; you do not perform NLP, scraping, or inference.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[ValidateTeamNewsTool(ctx=ctx)],
    )
    impact_agent = Agent(
        role="Interpretability Impact Modeler",
        goal="Apply a bounded, deterministic team-news adjustment layer.",
        backstory="You are not a predictive engine; you provide an interpretable transformation only.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[ModelImpactTool(ctx=ctx)],
    )
    discrepancy_agent = Agent(
        role="Market Discrepancy Analyst",
        goal="Compute deltas between market and model probabilities.",
        backstory="You compare probability vectors and sort by absolute delta.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[AnalyzeDiscrepanciesTool(ctx=ctx)],
    )
    report_agent = Agent(
        role="Report Writer",
        goal="Write a neutral market intelligence memo with no recommendations.",
        backstory="You only restate deterministic outputs and avoid prescriptive language.",
        allow_delegation=False,
        verbose=verbose,
        llm=llm,
        tools=[WriteReportTool(ctx=ctx)],
    )

    t0 = Task(
        description="Emit the validated match and inputs used for downstream tasks.",
        expected_output="A Match object (validated).",
        agent=inputs_agent,
        tools=[inputs_agent.tools[0]],
        output_pydantic=Match,
    )
    t1 = Task(
        description="Compute market implied probabilities from raw odds.",
        expected_output="ImpliedProbabilities (validated) including overround.",
        agent=odds_agent,
        tools=[odds_agent.tools[0]],
        output_pydantic=ImpliedProbabilities,
    )
    t2 = Task(
        description="Validate team news strictly against schema.",
        expected_output="MatchTeamNews (validated; values preserved).",
        agent=team_news_agent,
        tools=[team_news_agent.tools[0]],
        output_pydantic=MatchTeamNews,
    )
    t3 = Task(
        description="Compute xG adjustment and adjusted probabilities deterministically.",
        expected_output="ImpactModelOutput (validated).",
        agent=impact_agent,
        tools=[impact_agent.tools[0]],
        output_pydantic=ImpactModelOutput,
    )
    t4 = Task(
        description="Analyze market-to-model discrepancies.",
        expected_output="DiscrepancyOutput (validated) listing discrepancies.",
        agent=discrepancy_agent,
        tools=[discrepancy_agent.tools[0]],
        output_pydantic=DiscrepancyOutput,
    )
    t5 = Task(
        description="Write the final market analysis report in strict schema form.",
        expected_output="MarketAnalysisReport (validated).",
        agent=report_agent,
        tools=[report_agent.tools[0]],
        output_pydantic=MarketAnalysisReport,
    )

    return Crew(
        agents=[
            inputs_agent,
            odds_agent,
            team_news_agent,
            impact_agent,
            discrepancy_agent,
            report_agent,
        ],
        tasks=[t0, t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=verbose,
    )


def run_offline_pipeline(*, match: Match, raw_odds: RawOdds, team_news: MatchTeamNews) -> MarketAnalysisReport:
    ctx = PipelineContext(match=match, raw_odds=raw_odds, team_news=team_news)

    EmitInputsTool(ctx=ctx)._run()
    ComputeImpliedProbabilitiesTool(ctx=ctx)._run()
    ValidateTeamNewsTool(ctx=ctx)._run()
    ModelImpactTool(ctx=ctx)._run()
    AnalyzeDiscrepanciesTool(ctx=ctx)._run()
    WriteReportTool(ctx=ctx)._run()

    if ctx.report is None:
        raise RuntimeError("Offline pipeline did not produce a report")
    return ctx.report
