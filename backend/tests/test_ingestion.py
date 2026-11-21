import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.api import app
from backend.ingestion import engine, process_next
from backend.storage import Match


def test_ingest_real_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.environ.get("TEST_DATABASE_URL")
    demo = os.environ.get("TEST_DEMO_PATH")
    if not url or not demo:
        pytest.skip(
            "Set TEST_DATABASE_URL and TEST_DEMO_PATH for ingestion verification."
        )

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DEMO_SPOOL_DIR", str(tmp_path))
    engine.cache_clear()
    ids: list[str] = []
    try:
        with TestClient(app) as client:
            bad = client.post("/matches?filename=invalid.dem", content=b"bad")
            assert bad.status_code == 415
            corrupt = client.post(
                "/matches?filename=broken.dem", content=b"PBDEMS2\x00" + bytes(100)
            )
            assert corrupt.status_code == 202
            ids.append(corrupt.json()["id"])
            assert process_next()
            assert client.get(corrupt.json()["status_url"]).json()["status"] == "failed"

            data = Path(demo).read_bytes()
            first = client.post("/matches?filename=sample.dem", content=data)
            assert first.status_code == 202
            ids.append(first.json()["id"])
            repeated = client.post("/matches?filename=again.dem", content=data)
            assert repeated.status_code == 202
            assert first.json() == repeated.json()
            path = first.json()["status_url"]
            assert client.get(path).json()["status"] == "queued"
            assert process_next()
            assert client.get(path).json()["status"] == "ready"
            assert not list(tmp_path.iterdir())

            response = client.get(f"{path}/analytics")
            assert response.status_code == 200, response.text
            result = response.json()
            assert (result["map_name"], result["round_count"]) == ("de_mirage", 13)
            scores = {
                row["name"]: (row["kills"], row["deaths"]) for row in result["players"]
            }
            # The recorded world death at tick 40220 follows the final round.
            assert scores["organner.pl free trial"] == (27, 0)
            assert scores["bargota22"] == (4, 13)
    finally:
        database = engine()
        with Session(database) as session, session.begin():
            session.execute(delete(Match).where(Match.id.in_(ids)))
        database.dispose()
        engine.cache_clear()
