# Copyright (c) Ragini Pawar. All rights reserved.
#
# One image, five processes: all four engines + the gateway that fronts them.
# Uses Python 3.11 deliberately (not whatever the host machine has) — every
# engine's requirements.txt has real prebuilt Linux wheels available for 3.11,
# sidestepping the Windows/Python-3.14 wheel problems worked around locally
# during development (see each engine's README for that story).
FROM python:3.11-slim

WORKDIR /app

# libgomp1: OpenMP runtime lightgbm/scikit-learn need at import time, not just
# build time — omitting it produces a working build that crashes on first use.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy all four engines + the gateway, preserving their sibling layout exactly
# as it is locally — every engine's cross-engine storage lookup
# (BASE_DIR.parent / "personN_engine" / "storage") depends on this structure.
COPY person1_engine/ ./person1_engine/
COPY person2_engine/ ./person2_engine/
COPY person3_engine/ ./person3_engine/
COPY person4_engine/ ./person4_engine/
COPY gateway/ ./gateway/
COPY start.sh ./start.sh

# One shared Python environment for all five processes. They run as separate
# OS processes (see start.sh), so there's no import-namespace collision risk
# here (see gateway/main.py's docstring for why that matters) — this is purely
# about not needing five separate images/venvs.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    -r person1_engine/requirements.txt \
    -r person2_engine/requirements.txt \
    -r person3_engine/requirements.txt \
    -r person4_engine/requirements.txt \
    -r gateway/requirements.txt

RUN chmod +x ./start.sh

ENV PORT=8080
EXPOSE 8080

CMD ["./start.sh"]
