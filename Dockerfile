# SpliceGAIP Docker Image
# Based on Alpine for minimal size and reliable package management

FROM python:3.11-alpine AS builder

WORKDIR /build

# Install build dependencies (Alpine uses apk, much faster than apt)
RUN apk add --no-cache gcc g++ musl-dev

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.11-alpine AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPLICEGAIP_RUNTIME_ROOT=/data/runtime \
    SPLICEGAIP_MEMORY_DB=/data/splicegaip.sqlite3 \
    SPLICEGAIP_LITERATURE_DB=/data/literature.sqlite3

# Install runtime dependencies (libgomp for OpenMP support)
RUN apk add --no-cache libgomp

# Create non-root user
RUN addgroup -S splicegaip && adduser -S splicegaip -G splicegaip

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

# Default command
CMD ["python", "run.py", "serve", "--api", "--ui", "--port", "8800"]
