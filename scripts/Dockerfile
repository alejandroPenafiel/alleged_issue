FROM python:3.11-slim

WORKDIR /app

COPY registry.py ./

EXPOSE 8500

CMD ["python", "registry.py", "--serve"]
