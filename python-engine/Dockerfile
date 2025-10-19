FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine.py celery_app.py healthcheck.py mcp_client.py ./
COPY config ./config

CMD ["python", "engine.py"]
