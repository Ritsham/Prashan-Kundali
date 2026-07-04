FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY services/llm_engine_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy full repo so shared app/llm_engine/ packages are available
COPY . .

EXPOSE 8002

CMD ["uvicorn", "services.llm_engine_service.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
