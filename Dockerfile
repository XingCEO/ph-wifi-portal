# Stage 1: Build Next.js brand site
FROM node:22-slim AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY frontend/ ./frontend/

# Copy Next.js static export
COPY --from=web-builder /web/out ./web/out/

ENV PYTHONPATH=/app:/app/server
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "cd server && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
