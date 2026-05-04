# Stage 1: Builder - compile/prepare dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Only install build essentials needed to compile packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (compiles C extensions if needed)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime - minimal final image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the compiled Python packages from builder (no build tools!)
COPY --from=builder /root/.local /root/.local

# Update PATH to use the installed packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . /app

# Expose the port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]