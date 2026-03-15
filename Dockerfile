FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY server/main_minimal.py ./main.py
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
