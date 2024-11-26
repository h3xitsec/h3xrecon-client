FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY ./dist/h3xrecon_client-0.0.1-py3-none-any.whl /app/h3xrecon_client-0.0.1-py3-none-any.whl

RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install /app/h3xrecon_client-0.0.1-py3-none-any.whl

ENV PYTHONUNBUFFERED=1

ENV PYTHONFAULTHANDLER=1

ENTRYPOINT ["/app/venv/bin/python", "-m", "h3xrecon_client.main"]
