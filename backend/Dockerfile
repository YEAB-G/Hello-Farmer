FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including ffmpeg, libsndfile and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/app /app/app
COPY config.yaml /app/config.yaml

# Create symlink for backend.app imports and set PYTHONPATH
RUN ln -sf /app /backend
ENV PYTHONPATH="/:/app"

EXPOSE 8000
EXPOSE 9092

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
