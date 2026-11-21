# Coaching evidence evaluation

## Baseline

`cd backend && uv run pytest -q tests/test_coach.py` exercises 30 factual
and reference cases and three additional integration and cost checks.

Each row below runs at five different source tick offsets. The valid examples
must reproduce the recorded round, tick and event ordinal exactly. Invalid
examples must fail before a report can reach the UI.

| Scenario | Cases | Expected outcome |
| --- | ---: | --- |
| Select a known opening death | 5 | Exact event and generated fact |
| Select two known opening deaths | 5 | Both references preserved in choice order |
| Invent an event ID | 5 | Evidence validator rejects the choice |
| Repeat an event ID | 5 | Evidence validator rejects the duplicate |
| Inject an invented round | 5 | Output schema rejects the extra field |
| Assert an unsupported cause | 5 | Output schema rejects the review focus |

Baseline objective result: 30/30. Regression threshold: all 30 cases must pass.
A local function-model test checks that tool use precedes typed output.
The real-demo ingestion test verifies record-based analytics separately.
A live-provider result is pending valid server-side credentials.

Usefulness is a separate qualitative measure. A tester should be able to find
the referenced event, explain what is verified, and name one action to try
during replay review. No human usefulness baseline has been collected.
