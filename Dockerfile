FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY backend /app/backend
COPY frontend /app/frontend
COPY tests /app/tests
RUN pip install --no-cache-dir -e ".[dev]"


EXPOSE 8000
EXPOSE 8501

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
