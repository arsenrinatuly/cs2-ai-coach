"""HTTP entry point for CS2 AI Coach."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="CS2 AI Coach")


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")
