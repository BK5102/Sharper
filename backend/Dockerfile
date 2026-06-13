FROM python:3.11-slim

WORKDIR /app

# Copy only what pip needs to install the package
COPY pyproject.toml README.md ./
COPY sharper/ ./sharper/

# Install into the container's system Python — no venv, no PATH ambiguity
RUN pip install --no-cache-dir -e .

ENV SHARPER_API_HOST=0.0.0.0
# sharper-api calls run() which reads PORT (Railway) then SHARPER_API_PORT then 8000
CMD ["sharper-api"]
