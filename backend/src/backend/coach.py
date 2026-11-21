"""Provide evidence-backed review recommendations for one player."""

import asyncio
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import AgentRunError, UserError
from pydantic_ai.usage import UsageLimits

from backend.analytics import EventReference, PlayerMetrics

logger = logging.getLogger("uvicorn.error").getChild("coach")

Focus = Literal["positioning", "timing", "team_support"]
ACTIONS: dict[Focus, str] = {
    "positioning": "Review where you were exposed before the first death.",
    "timing": "Review when you took the engagement relative to the round start.",
    "team_support": "Review whether a teammate could support the engagement.",
}


class ReviewChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_ordinal: int = Field(gt=0)
    focus: Focus


class CoachSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choices: list[ReviewChoice] = Field(min_length=1, max_length=3)


class CoachingObservation(BaseModel):
    observation: str
    evidence: EventReference
    suggested_review_action: str
    uncertainty: str


class CoachingReport(BaseModel):
    match_id: str
    steamid: str
    source: Literal["deterministic", "model"]
    observations: list[CoachingObservation]


@dataclass
class ReviewContext:
    match_id: str
    player: PlayerMetrics
    tool_called: bool = False


class CoachUnavailable(RuntimeError):
    """A configured model did not generate a usable report."""


def validate_choices(context: ReviewContext, selection: CoachSelection) -> None:
    valid_ids = {event.event_ordinal for event in context.player.opening_deaths}
    selected_ids = [choice.event_ordinal for choice in selection.choices]
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("Evidence references must be unique.")
    if not set(selected_ids).issubset(valid_ids):
        raise ValueError(
            "Use only opening-death event IDs returned by the analytics tool."
        )


def render_report(
    context: ReviewContext,
    selection: CoachSelection | None,
    source: Literal["deterministic", "model"],
) -> CoachingReport:
    observations = []
    if selection is not None:
        validate_choices(context, selection)
        evidence_by_id = {
            event.event_ordinal: event for event in context.player.opening_deaths
        }
        for choice in selection.choices:
            evidence = evidence_by_id[choice.event_ordinal]
            observations.append(
                CoachingObservation(
                    observation=f"You had the first recorded death in round {evidence.round_number}.",
                    evidence=evidence,
                    suggested_review_action=ACTIONS[choice.focus],
                    uncertainty="Death events alone cannot establish why the engagement was lost.",
                )
            )
    return CoachingReport(
        match_id=context.match_id,
        steamid=context.player.steamid,
        source=source,
        observations=observations,
    )


coach = Agent(
    deps_type=ReviewContext,
    output_type=CoachSelection,
    instructions=(
        "Call verified_opening_deaths. Choose up to three distinct events from the tool "
        "and a review focus for each. Select review actions as questions to investigate. "
        "The tool does not establish causes, positions, intentions, or teammate mistakes."
    ),
    retries=1,
)


@coach.tool
def verified_opening_deaths(context: RunContext[ReviewContext]) -> list[EventReference]:
    """Read opening-death evidence for the requested match and player."""
    context.deps.tool_called = True
    return context.deps.player.opening_deaths


@coach.output_validator
def validate_model_output(
    context: RunContext[ReviewContext], selection: CoachSelection
) -> CoachSelection:
    if not context.deps.tool_called:
        raise ModelRetry("Call verified_opening_deaths first.")
    try:
        validate_choices(context.deps, selection)
    except ValueError as error:
        raise ModelRetry(str(error)) from error
    return selection


def estimated_cost(input_tokens: int, output_tokens: int) -> Decimal | None:
    try:
        input_rate = Decimal(os.environ["COACH_INPUT_USD_PER_MILLION"])
        output_rate = Decimal(os.environ["COACH_OUTPUT_USD_PER_MILLION"])
        if not all(
            rate.is_finite() and rate >= 0 for rate in (input_rate, output_rate)
        ):
            return None
    except (KeyError, InvalidOperation):
        return None
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


async def generate_report(context: ReviewContext) -> CoachingReport:
    model = os.environ.get("COACH_MODEL")
    if not context.player.opening_deaths:
        return render_report(context, None, "deterministic")
    if not model:
        choices = [
            ReviewChoice(event_ordinal=event.event_ordinal, focus="timing")
            for event in context.player.opening_deaths[:3]
        ]
        return render_report(context, CoachSelection(choices=choices), "deterministic")

    started = perf_counter()
    try:
        async with asyncio.timeout(25):
            result = await coach.run(
                "Choose evidence to review for this player.",
                deps=context,
                model=model,
                usage_limits=UsageLimits(request_limit=3, tool_calls_limit=2),
                model_settings={"max_tokens": 400},
            )
    except (TimeoutError, AgentRunError, UserError, ValueError, OSError) as error:
        logger.warning(
            "coach_failed elapsed_ms=%d category=%s",
            (perf_counter() - started) * 1000,
            type(error).__name__,
        )
        raise CoachUnavailable(
            "The model could not produce a coaching report."
        ) from error

    usage = result.usage
    logger.info(
        "coach_completed elapsed_ms=%d input_tokens=%d output_tokens=%d estimated_usd=%s",
        (perf_counter() - started) * 1000,
        usage.input_tokens,
        usage.output_tokens,
        estimated_cost(usage.input_tokens, usage.output_tokens),
    )
    return render_report(context, result.output, "model")
