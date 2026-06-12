FROM python:3.11-slim

WORKDIR /app

# Copy only what pip needs to install the package
COPY pyproject.toml README.md ./
COPY sharper/ ./sharper/

# Install into the container's system Python — no venv, no PATH ambiguity
RUN pip install --no-cache-dir -e .

# Railway injects PORT; shell form expands env vars at runtime
CMD python -m uvicorn sharper.api:app --host 0.0.0.0 --port ${PORT:-8000}
