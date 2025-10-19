FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install httpx==0.27.0

COPY register_eliza_tools.py ./register_eliza_tools.py

CMD ["python", "register_eliza_tools.py"]
