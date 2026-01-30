FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY browser_session_service/ browser_session_service/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Run as non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "browser_session_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
