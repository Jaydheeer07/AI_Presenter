FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
# - gcc: compile native Python extensions
# - ffmpeg: required by pydub for audio format conversion
# - curl: healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure audio directory exists
RUN mkdir -p /app/frontend/audio

# Expose ports (FastAPI on 8000, Chainlit on 8001)
EXPOSE 8000 8001

# Healthcheck for the backend
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
