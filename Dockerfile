FROM python:3.12-slim
WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY frontend/ ./frontend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug"]
