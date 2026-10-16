# SpliceGAIP Docker Image
# Multi-stage build for optimized production deployment

# ---- Stage 1: Build dependencies ----
FROM python:3.11-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-bookworm AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPLICEGAIP_RUNTIME_ROOT=/data/runtime \
    SPLICEGAIP_MEMORY_DB=/data/splicegaip.sqlite3 \
    SPLICEGAIP_LITERATURE_DB=/data/literature.sqlite3

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r splicegaip && useradd -r -g splicegaip -m splicegaip

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create data directory and set permissions
RUN mkdir -p /data && chown -R splicegaip:splicegaip /data /app

# Expose ports
EXPOSE 8800 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8800/api/health')" || exit 1

# Switch to non-root user
USER splicegaip

# Default command: serve API and UI
CMD ["python", "run.py", "serve", "--api", "--ui", "--port", "8800"]
