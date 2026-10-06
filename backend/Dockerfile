# Backend image: FastAPI + Uvicorn on Python 3.12 (slim = small Debian base).
# This same image runs on your Windows dev box and the Linux server.
FROM python:3.12-slim

# Don't buffer stdout/stderr — logs appear immediately in `docker compose logs`.
# Don't write .pyc files inside the container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first, separately from the app code. Docker caches this
# layer, so changing your code doesn't trigger a full dependency reinstall.
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Now copy the application code.
COPY app ./app

EXPOSE 8000

# --reload restarts Uvicorn when code changes. Great for dev; overridden in prod.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
