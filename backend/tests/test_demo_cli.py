import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend import demo_cli


def test_cli_prints_sorted_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    players = [
        {"steamid": "76561198000000002", "name": "Shared", "kills": 0, "deaths": 1},
        {"steamid": "76561198000000001", "name": "Shared", "kills": 1, "deaths": 0},
    ]
    inspection = {
        "filename": "match.dem",
        "size_bytes": 42,
        "map_name": "de_mirage",
        "round_count": 1,
        "players": players,
    }
    inspect_demo = Mock(return_value=inspection)
    monkeypatch.setattr(demo_cli, "inspect_demo", inspect_demo)

    assert demo_cli.main(["match.dem"]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out) == {**inspection, "players": players[::-1]}
    assert captured.err == ""
    inspect_demo.assert_called_once_with(Path("match.dem"))


def test_cli_reports_missing_file(tmp_path: Path, capsys) -> None:
    with pytest.raises(SystemExit) as error:
        demo_cli.main([str(tmp_path / "missing.dem")])

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert captured.out == ""
    assert "Cannot read missing.dem" in captured.err
