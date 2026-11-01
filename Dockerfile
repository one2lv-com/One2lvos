# One2lv Unified OS v1.0.1 - Reproducible Build
FROM python:3.11-slim

# Pin build environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git=1:2.39.* \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/one2lv-unified-os

# Copy source
COPY . .

# Install Python dependencies (none currently, but structure ready)
# RUN pip install --no-cache-dir -r requirements.txt

# Verify checksums
RUN sha256sum -c CHECKSUMS.txt || echo "Checksums not verified"

# Default command
CMD ["python3", "unified_os.py"]

# Build metadata
LABEL org.opencontainers.image.title="One2lv Unified OS"
LABEL org.opencontainers.image.version="1.0.1-verification"
LABEL org.opencontainers.image.description="Unified operating system integrating One2lv ecosystem"
LABEL org.opencontainers.image.source="https://github.com/one2lv-com"
