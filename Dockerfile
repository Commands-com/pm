# Multi-stage Dockerfile for Project Manager MCP
# Production-optimized build with security hardening

# Build stage - prepare Python package
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Copy project files for build
COPY pyproject.toml .
COPY src/ ./src/
COPY examples/ ./examples/

# Build wheel package
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Production stage - minimal runtime environment
FROM python:3.11-slim as production

WORKDIR /app

# Security: Install security updates and create non-root user
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        # Required for health checks and monitoring
        curl \
        && rm -rf /var/lib/apt/lists/* && \
    groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Install application from wheel
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir *.whl && \
    rm -f *.whl

# Create data directory with proper ownership
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

# Copy health check script
COPY deploy/docker-healthcheck.py /app/docker-healthcheck.py
RUN chmod +x /app/docker-healthcheck.py && \
    chown appuser:appuser /app/docker-healthcheck.py

# Create volume mount point for persistent data
VOLUME ["/app/data"]

# Security: Switch to non-root user
USER appuser

# Expose ports for API and WebSocket/SSE
EXPOSE 8080 8081

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/docker-healthcheck.py

# Default command - can be overridden by docker-compose or deployment
CMD ["project-manager-mcp", "--port", "8080"]