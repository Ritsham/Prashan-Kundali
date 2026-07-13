"""
LLM Engine Microservice
=======================
Standalone FastAPI server + Celery worker for narrative generation.

Responsibilities:
  - Accept chart + interpretation payloads from the API Gateway
  - Enqueue background Map-Reduce LLM generation jobs
  - Publish streaming tokens to Redis Pub/Sub
  - Expose a direct (non-streaming) generation endpoint for internal use

Endpoints:
  POST /generate        — enqueue async LLM generation, returns task_id
  GET  /generate/sync   — synchronous, blocks until generation is complete
  GET  /health          — liveness probe

Run worker separately:
  celery -A services.llm_engine_service.worker worker --loglevel=info
"""
from dotenv import load_dotenv
load_dotenv()

import sys, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.llm_engine import generate_interpretation_answer
from app.config import get_settings

app = FastAPI(
    title="LLM Engine",
    version="1.0.0",
    description="Internal microservice: Map-Reduce LLM narrative generation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────── Models ────────────────────────────

class GenerateRequest(BaseModel):
    chart_id: str
    chart: dict
    interpretation: dict


# ─────────────────────────── Routes ────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "llm_engine"}


@app.post("/generate")
def generate_async(payload: GenerateRequest) -> dict:
    """
    Enqueue a background Map-Reduce LLM generation job.
    Returns immediately. Frontend connects to Redis SSE stream for tokens.
    """
    try:
        from app.worker import generate_reading_task
        task = generate_reading_task.delay(payload.chart_id, payload.chart, payload.interpretation)
        return {
            "status": "queued",
            "task_id": task.id,
            "chart_id": payload.chart_id,
            "stream_channel": f"stream:{payload.chart_id}"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/generate/sync")
def generate_sync(payload: GenerateRequest) -> dict:
    """
    Synchronous generation — blocks until the reading is complete.
    Use for internal calls or CLI testing where streaming is not needed.
    """
    try:
        answer = generate_interpretation_answer(
            payload.chart,
            payload.interpretation,
            chart_id=payload.chart_id
        )
        return {"status": "done", "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
