FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY janus_baseline_agent_cli/__init__.py janus_baseline_agent_cli/
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# Copy application code
COPY . .

# Install package in development mode for all modules
RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app /app

# Copy agent-pack for reference docs
COPY --from=builder /app/agent-pack /agent-pack

RUN chown -R app:app /app /agent-pack

# Environment configuration
ENV HOST=0.0.0.0
ENV PORT=8080
ENV LOG_LEVEL=INFO
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose competitor port
EXPOSE 8080

USER app

# Run the server
CMD ["python", "-m", "janus_baseline_agent_cli.main"]
