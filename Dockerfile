FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

# Copy application files
COPY src/ ./src/
COPY web/ ./web/
COPY data/ ./data/
COPY run_web.py ./

ENV PYTHONPATH=/app/src:/app/web
ENV PORT=8000

EXPOSE 8000

# Start production server
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir web"]
