"""Loopback-only web interface. Runs stay in memory and exports are explicit."""
from __future__ import annotations

import copy
import io
import json
import logging
import os
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import EXAMPLES, get_catalog

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
MAX_RUNS = 30
RUN_TTL = 3600
RUNS: dict[str, dict] = {}
LOCK = threading.RLock()
WORKERS = ThreadPoolExecutor(max_workers=1, thread_name_prefix="scopeproof")
LOGGER = logging.getLogger("scopeproof")

app = FastAPI(title="ScopeProof", version="0.1.0", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])


@app.middleware("http")
async def local_browser_only(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
        return JSONResponse({"detail": "Only a local browser can use this app."}, status_code=403)
    if request.headers.get("sec-fetch-site") == "cross-site":
        return JSONResponse({"detail": "Cross-site requests are not accepted."}, status_code=403)
    if request.method == "POST":
        size = request.headers.get("content-length")
        if size and (not size.isdigit() or int(size) > 65536):
            return JSONResponse({"detail": "Request is too large."}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


class BriefRequest(BaseModel):
    brief: str = Field(min_length=20, max_length=12000)
    change_request: str | None = Field(default=None, max_length=4000)


def model_health() -> dict:
    model = os.environ.get("SCOPEPROOF_MODEL", "").strip()
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    base = {"status": "ok", "provider": "Ollama / Strands", "model": model or "Not configured", "ready": False}
    if not model:
        return {**base, "detail": "Set SCOPEPROOF_MODEL to a locally installed Ollama model, then restart."}
    if urlsplit(host).hostname not in {"127.0.0.1", "localhost", "::1"}:
        return {**base, "detail": "This build supports a local Ollama server only."}
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            response = client.get(f"{host}/api/tags")
            response.raise_for_status()
            names = {m.get("name") for m in response.json().get("models", [])}
        ready = model in names or f"{model}:latest" in names
        return {**base, "ready": ready, "detail": "Local model ready. No paid API calls." if ready else f"Install the model with: ollama pull {model}"}
    except (httpx.HTTPError, ValueError):
        return {**base, "detail": "Start the local Ollama server, then refresh. No model request has been made."}


@app.get("/api/health")
def health():
    return model_health()


@app.get("/api/catalog")
def catalog():
    return get_catalog()


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES, "synthetic": True}


def cleanup() -> None:
    now = time.time()
    for key in list(RUNS):
        if RUNS[key]["status"] in {"complete", "failed"} and now - RUNS[key]["created_at"] > RUN_TTL:
            del RUNS[key]
    while len(RUNS) >= MAX_RUNS:
        finished = next((k for k, r in RUNS.items() if r["status"] in {"complete", "failed"}), None)
        if finished is None:
            break
        del RUNS[finished]


def execute(run_id: str, brief: str, change: str | None) -> None:
    from .core import run_scope

    started = time.monotonic()
    with LOCK:
        RUNS[run_id].update(status="running", stage="Reading the brief")

    def event(item: dict) -> None:
        safe = {k: str(item.get(k, ""))[:3000] for k in ("step", "label", "status", "detail")}
        safe["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        with LOCK:
            if len(RUNS[run_id]["events"]) < 60:
                RUNS[run_id]["events"].append(safe)
            RUNS[run_id]["stage"] = safe["label"] or safe["step"]

    try:
        result = run_scope(brief, change, on_event=event)
        result.setdefault("metrics", {})["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        with LOCK:
            RUNS[run_id].update(status="complete", stage="Scope pack ready for review", result=result)
    except Exception as exc:
        # Do not log the brief or expose provider requests/credentials in responses.
        LOGGER.warning("Scope run failed: %s", type(exc).__name__)
        with LOCK:
            RUNS[run_id].update(status="failed", stage="Run stopped", error=(
                "The local model could not produce a validated scope pack. "
                "Check that Ollama and the configured model are available, or try a shorter brief. "
                "No quote was issued."
            ))


@app.post("/api/runs", status_code=202)
def create_run(body: BriefRequest):
    if not body.brief.strip():
        raise HTTPException(422, "Please enter a client brief.")
    state = model_health()
    if not state["ready"]:
        raise HTTPException(503, state["detail"])
    with LOCK:
        cleanup()
        if any(r["status"] in {"queued", "running"} for r in RUNS.values()):
            raise HTTPException(429, "A local run is already in progress. Wait for it to finish.")
        key = str(uuid.uuid4())
        RUNS[key] = {"id": key, "status": "queued", "stage": "Queued", "events": [], "created_at": time.time(),
                     "brief": body.brief, "change_request": body.change_request}
        WORKERS.submit(execute, key, body.brief, body.change_request)
    return {"id": key, "status": "queued"}


def get_run(run_id: str) -> dict:
    with LOCK:
        if run_id not in RUNS:
            raise HTTPException(404, "Run not found. Runs expire after one hour or when the server restarts.")
        return copy.deepcopy(RUNS[run_id])


@app.get("/api/runs/{run_id}")
def read_run(run_id: str):
    data = get_run(run_id)
    data.pop("brief", None)
    data.pop("change_request", None)
    return data


def quote_line(value, currency: str) -> str:
    return "Not quoted — clarification required" if value is None else f"{currency} {value} (draft)"


def build_pack(run: dict) -> bytes:
    result = run["result"]
    quote = result.get("quote", {})
    lines = ["# ScopeProof — scope pack", "", "DRAFT FOR HUMAN REVIEW. Not an accepted offer or agreement.", "",
             "Sample catalogue prices are illustrative. Confirm real rates, scope and terms with your client.", "",
             f"## {result.get('headline', 'Scope review')}", result.get("summary", ""), "",
             "## Proposed price", quote_line(quote.get("total"), quote.get("currency", "")), "", "## Scope and evidence"]
    for item in result.get("scope_items", []):
        lines.extend([f"- [{item.get('status', 'clarify')}] {item.get('text', '')}", f"  Source: {item.get('evidence', '')}"])
    lines.extend(["", "## Questions before commitment"])
    for item in result.get("questions", []):
        lines.extend([f"- {item.get('question', '')}", f"  Why: {item.get('reason', '')}"])
    lines.extend(["", "## Risks"])
    for item in result.get("risks", []):
        lines.append(f"- {item.get('severity', '')}: {item.get('title', '')} — {item.get('detail', '')}")
    lines.extend(["", "## Proposed deliverables"])
    lines.extend(f"- {item}" for item in result.get("deliverables", []))
    lines.extend(["", "## Limitations", "Exact quote matching checks provenance, not semantic truth. Review classifications and omissions.",
                  "The agent has no messaging, payment, browsing or shell tools. This export does not send anything."])
    audit = {"id": run["id"], "brief": run["brief"], "change_request": run.get("change_request"),
             "events": run["events"], "result": result}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scope-review.md", "\n".join(lines))
        archive.writestr("client-message-DRAFT.txt", result.get("client_message", ""))
        archive.writestr("evidence-and-audit.json", json.dumps(audit, ensure_ascii=False, indent=2))
        archive.writestr("delivery-checklist.md", "# Proposed delivery checklist\n\nReview and agree scope first.\n\n" +
                         "\n".join(f"- [ ] {d}" for d in result.get("deliverables", [])))
    return buf.getvalue()


@app.get("/api/runs/{run_id}/download")
def download(run_id: str):
    run = get_run(run_id)
    if run["status"] != "complete":
        raise HTTPException(409, "A validated result is required before export.")
    return Response(build_pack(run), media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="scopeproof-review-pack.zip"'
    })


app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
