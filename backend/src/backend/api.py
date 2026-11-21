"""HTTP entry point for CS2 AI Coach."""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.analytics import MatchAnalytics, load_analytics
from backend.coach import (
    CoachingReport,
    CoachUnavailable,
    ReviewContext,
    generate_report,
)
from backend.ingestion import engine, enqueue, spool_dir
from backend.storage import Match

app = FastAPI(title="CS2 AI Coach")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


class MatchStatus(BaseModel):
    id: str
    filename: str
    size_bytes: int
    status: str
    map_name: str | None
    error: str | None


@app.post("/matches", status_code=202)
async def upload_match(request: Request, filename: str) -> dict[str, str]:
    if (
        not filename.lower().endswith(".dem")
        or "/" in filename
        or "\\" in filename
        or any(ord(char) < 32 for char in filename)
        or len(filename) > 255
    ):
        raise HTTPException(400, "Provide the filename of an extracted .dem recording.")

    digest = hashlib.sha256()
    size = 0
    with tempfile.NamedTemporaryFile(dir=spool_dir(), delete=False) as upload:
        temporary = Path(upload.name)
        try:
            async for chunk in request.stream():
                size += len(chunk)
                if size > 512 * 1024 * 1024:
                    raise HTTPException(413, "The recording exceeds 512 MiB.")
                digest.update(chunk)
                upload.write(chunk)
            upload.flush()
            upload.seek(0)
            if upload.read(8) != b"PBDEMS2\x00":
                raise HTTPException(415, "Expected a CS2 Source 2 recording.")
            match_id = digest.hexdigest()
            await run_in_threadpool(enqueue, match_id, filename, size, temporary)
        finally:
            temporary.unlink(missing_ok=True)
    return {"id": match_id, "status_url": f"/matches/{match_id}"}


@app.get("/matches/{match_id}")
def match_status(match_id: str) -> MatchStatus:
    with Session(engine()) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise HTTPException(404, "Match not found.")
        return MatchStatus.model_validate(match, from_attributes=True)


@app.get("/matches/{match_id}/analytics")
def match_analytics(match_id: str) -> MatchAnalytics:
    with Session(engine()) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise HTTPException(404, "Match not found.")
        if match.status != "ready":
            raise HTTPException(409, "Match analytics are unavailable.")
        return load_analytics(session, match)


@app.post("/matches/{match_id}/players/{steamid}/coach")
async def player_coach(match_id: str, steamid: str) -> CoachingReport:
    analytics = await run_in_threadpool(match_analytics, match_id)
    player = next((row for row in analytics.players if row.steamid == steamid), None)
    if player is None:
        raise HTTPException(404, "Player not found in this match.")
    try:
        return await generate_report(ReviewContext(match_id, player))
    except CoachUnavailable as error:
        raise HTTPException(503, str(error)) from error
