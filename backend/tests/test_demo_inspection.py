from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend import demo_inspection


def test_inspect_demo_reports_awpy_data(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "match.dem"
    path.write_bytes(b"fixture")
    scoreboard = Mock()
    scoreboard.iter_rows.return_value = [
        {"steamid": 76561198000000000, "name": "Player", "kills": 4, "deaths": 0},
        {"steamid": None, "name": None, "kills": None, "deaths": 2},
    ]
    parsed = SimpleNamespace(
        header={"map_name": "de_mirage"},
        rounds=SimpleNamespace(height=13),
        player_stats=Mock(return_value=scoreboard),
    )
    demo = Mock(return_value=parsed)
    monkeypatch.setattr(demo_inspection, "Demo", demo)

    assert demo_inspection.inspect_demo(path) == {
        "filename": "match.dem",
        "size_bytes": 7,
        "map_name": "de_mirage",
        "round_count": 13,
        "players": [
            {"steamid": "76561198000000000", "name": "Player", "kills": 4, "deaths": 0},
            {"steamid": None, "name": None, "kills": None, "deaths": 2},
        ],
    }
    demo.assert_called_once_with(path)
    parsed.player_stats.assert_called_once_with(include_knife_rounds=True)


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("match.rar", None, "Expected an extracted"),
        ("missing.dem", None, "Cannot read missing.dem"),
        ("source1.dem", b"HL2DEMO\x00" + bytes(100), "magic bytes mismatch"),
        ("truncated.dem", b"PBDEMS2\x00" + bytes(100), "DEM_FileHeader not found"),
    ],
)
def test_inspect_demo_rejects_invalid_input(
    tmp_path: Path, filename: str, content: bytes | None, message: str
) -> None:
    path = tmp_path / filename
    if content is not None:
        path.write_bytes(content)
    with pytest.raises(demo_inspection.DemoInspectionError, match=message):
        demo_inspection.inspect_demo(path)
