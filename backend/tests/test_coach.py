import asyncio

import pytest
from pydantic import ValidationError
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from backend.analytics import EventReference, PlayerMetrics
from backend.coach import (
    CoachSelection,
    ReviewChoice,
    ReviewContext,
    coach,
    estimated_cost,
    generate_report,
    render_report,
)


def context_for(tick: int, count: int = 2) -> ReviewContext:
    return ReviewContext(
        match_id="sample",
        player=PlayerMetrics(
            steamid="123",
            name="Player",
            kills=0,
            deaths=count,
            assists=0,
            rounds_with_death_event_participation=list(range(1, count + 1)),
            opening_deaths=[
                EventReference(
                    round_number=index, event_ordinal=index * 7, tick=tick + index
                )
                for index in range(1, count + 1)
            ],
        ),
    )


@pytest.mark.parametrize("tick", [500, 702, 1024, 2077, 6000])
@pytest.mark.parametrize(
    ("case", "choices"),
    [
        ("valid-first", [{"event_ordinal": 7, "focus": "positioning"}]),
        (
            "valid-two",
            [
                {"event_ordinal": 14, "focus": "timing"},
                {"event_ordinal": 7, "focus": "team_support"},
            ],
        ),
        ("invented-event", [{"event_ordinal": 99, "focus": "timing"}]),
        (
            "duplicate",
            [
                {"event_ordinal": 7, "focus": "positioning"},
                {"event_ordinal": 7, "focus": "timing"},
            ],
        ),
        (
            "invented-round",
            [{"event_ordinal": 7, "focus": "timing", "round_number": 99}],
        ),
        ("unsupported-cause", [{"event_ordinal": 7, "focus": "bad aim"}]),
    ],
)
def test_coaching_evidence_matrix(tick: int, case: str, choices: list[dict]) -> None:
    context = context_for(tick)
    if case.startswith("valid"):
        selection = CoachSelection.model_validate({"choices": choices})
        report = render_report(context, selection, "model")
        expected = {
            event.event_ordinal: event for event in context.player.opening_deaths
        }
        for chosen, observation in zip(
            selection.choices, report.observations, strict=True
        ):
            event = expected[chosen.event_ordinal]
            assert observation.evidence == event
            assert (
                observation.observation
                == f"You had the first recorded death in round {event.round_number}."
            )
    elif case in {"invented-round", "unsupported-cause"}:
        with pytest.raises(ValidationError):
            CoachSelection.model_validate({"choices": choices})
    else:
        selection = CoachSelection.model_validate({"choices": choices})
        with pytest.raises(ValueError):
            render_report(context, selection, "model")


def test_empty_evidence_does_not_call_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACH_MODEL", "invalid")
    report = asyncio.run(generate_report(context_for(500, 0)))
    assert report.observations == []
    assert report.source == "deterministic"


def test_model_tool_and_typed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACH_MODEL", "test")
    choices = CoachSelection(choices=[ReviewChoice(event_ordinal=7, focus="timing")])
    calls = []

    def respond(messages, info):
        if not calls:
            calls.append("tool")
            return ModelResponse(parts=[ToolCallPart("verified_opening_deaths", {})])
        calls.append("output")
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, choices.model_dump())]
        )

    with coach.override(model=FunctionModel(respond)):
        report = asyncio.run(generate_report(context_for(500)))
    assert calls == ["tool", "output"]
    assert report.source == "model"
    assert report.observations[0].evidence.tick == 501


def test_cost_uses_configured_token_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACH_INPUT_USD_PER_MILLION", "1.00")
    monkeypatch.setenv("COACH_OUTPUT_USD_PER_MILLION", "2.00")
    assert str(estimated_cost(500_000, 250_000)) == "1.00"
