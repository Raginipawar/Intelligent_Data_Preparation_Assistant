# Copyright (c) Ragini Pawar. All rights reserved.
# Original design and source — not to be copied, cloned, or reproduced without permission.
"""
main.py — the single public entry point for deployment.

Reverse-proxies /person1/*, /person2/*, /person3/*, /person4/* to each engine,
which keeps running as its own independent process on a fixed localhost port
inside the same deployment (see start.sh). This exists purely so the whole
backend ships as ONE deployable service (one URL, one CORS config, one hosting
service) without touching a single line of any of the four engines' own code.

Why not just import all four FastAPI apps into one process and mount() them?
Every engine defines its own top-level `app` Python package (app/schemas.py,
app/main.py, etc. — see each engine's own README, "Why this engine doesn't
import the other[s'] code"). That was a deliberate choice to avoid a namespace
collision if two ever ran in the same process — and deployment is exactly that
scenario. Rather than rename the `app` package across four codebases (a real,
risky refactor touching ~75 files) just to satisfy Python's import system, each
engine keeps running as its own OS process, and this gateway does plain HTTP
reverse-proxying between them — zero risk to any of the four engines' tested
logic, since none of their code changes at all.
"""
from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

UPSTREAMS = {
    "person1": os.environ.get("PERSON1_UPSTREAM", "http://127.0.0.1:8000"),
    "person2": os.environ.get("PERSON2_UPSTREAM", "http://127.0.0.1:8001"),
    "person3": os.environ.get("PERSON3_UPSTREAM", "http://127.0.0.1:8002"),
    "person4": os.environ.get("PERSON4_UPSTREAM", "http://127.0.0.1:8003"),
}

# Comma-separated list of allowed origins in production (e.g. your deployed
# frontend's URL). Defaults to "*" for local testing only.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = ["*"] if _origins_env.strip() == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]

app = FastAPI(title="AutoML Gateway", description="Reverse proxy fronting all four engines as one service.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Long-lived client reused across requests. Generous timeout: Person 4's
# /recommend can legitimately take a minute or more for real CV benchmarking
# on messy/wide data (observed ~52s in local testing).
_client = httpx.AsyncClient(timeout=200.0)

# Headers that must never be forwarded verbatim: connection-management headers
# are per-hop, not end-to-end; content-length/content-encoding get recomputed
# by Starlette from the actual body we're returning; the CORS headers are
# re-added by this gateway's own CORSMiddleware, which must be the only source
# of truth for them (forwarding the upstream's own wide-open "*" alongside our
# CORSMiddleware's headers would send duplicate/conflicting values).
_STRIP_RESPONSE_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
    "content-encoding", "content-length",
    "access-control-allow-origin", "access-control-allow-credentials",
    "access-control-allow-methods", "access-control-allow-headers",
    "date", "server",  # the gateway's own response cycle sets these; forwarding
                        # the upstream's copies alongside them just duplicates the header
}
_STRIP_REQUEST_HEADERS = {"host", "content-length"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway", "engines": list(UPSTREAMS)}


@app.api_route("/{engine}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(engine: str, path: str, request: Request):
    base = UPSTREAMS.get(engine)
    if base is None:
        return Response(
            content=f'{{"error": "Unknown engine \\"{engine}\\". Valid: {list(UPSTREAMS)}"}}',
            status_code=404,
            media_type="application/json",
        )

    url = f"{base}/{path}"
    body = await request.body()
    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in _STRIP_REQUEST_HEADERS}

    upstream_response = await _client.request(
        request.method,
        url,
        params=request.query_params,
        content=body,
        headers=forward_headers,
    )

    response_headers = {k: v for k, v in upstream_response.headers.items() if k.lower() not in _STRIP_RESPONSE_HEADERS}
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
