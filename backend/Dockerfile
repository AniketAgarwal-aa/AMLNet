FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN useradd --create-home appuser
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY data ./data
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
