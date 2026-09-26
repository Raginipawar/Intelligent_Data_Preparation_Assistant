#!/bin/sh
# Copyright (c) Ragini Pawar. All rights reserved.
# start.sh — launches all four engines as background processes on fixed
# localhost ports, then runs the gateway in the foreground bound to the
# platform's assigned $PORT. Only the gateway is ever reachable from outside
# the container; the four engines are only reachable from each other/the
# gateway via 127.0.0.1, exactly mirroring local dev (localhost:8000-8003)
# minus any need for a browser to reach them directly.
set -e

(cd person1_engine && PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
(cd person2_engine && PYTHONPATH=. python -m uvicorn app.suggestion_api:app --host 127.0.0.1 --port 8001) &
(cd person3_engine && PYTHONPATH=. python -m uvicorn app.apply_api:app --host 127.0.0.1 --port 8002) &
(cd person4_engine && PYTHONPATH=. python -m uvicorn app.recommend_api:app --host 127.0.0.1 --port 8003) &

# Give the four engines a moment to bind their ports before the gateway (and
# therefore the platform's health check, which polls the gateway) starts
# accepting traffic — avoids a burst of "connection refused" during boot.
sleep 3

cd gateway && PYTHONPATH=. exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
