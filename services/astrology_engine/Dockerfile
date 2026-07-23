FROM python:3.11-slim

WORKDIR /app

# Install system deps for pyswisseph
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY services/astrology_engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy source code (entire repo so shared app/ packages are available)
COPY . .

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

# Ephemeris data must be mounted or baked in
ENV SE_EPHE_PATH=/app/ephemeris

EXPOSE 8001

USER appuser

CMD ["uvicorn", "services.astrology_engine.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
