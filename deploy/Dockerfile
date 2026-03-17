# Stage 1: Dependencies
FROM python:3.12-slim as builder
WORKDIR /build
COPY server/requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim
WORKDIR /app

# Security: non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy application
COPY server/ ./server/
COPY frontend/ ./frontend/

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app/server
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

CMD ["sh", "-c", "cd /app/server && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --access-log"]
