# Use Python official image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV MPLBACKEND=Agg
ENV XDG_RUNTIME_DIR=/tmp/runtime-appuser
ENV DISPLAY=:99
ENV DOCKER_ENV=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgif-dev \
    libopenblas-dev \
    gfortran \
    ffmpeg \
    xvfb \
    sox \
    libsox-fmt-all \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-recommended \
    cm-super \
    dvipng \
    tipa \
    texlive-xetex \
    texlive-extra-utils \
    texlive-plain-generic \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories with correct permissions
RUN mkdir -p /app/media/videos/scene/1080p30 \
    && mkdir -p /app/tmp \
    && chown -R appuser:appuser /app/media \
    && chown -R appuser:appuser /app/tmp \
    && chmod -R 755 /app/media \
    && chmod -R 755 /app/tmp

# Switch to non-root user
USER appuser

# Copy application files
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 5001

# Set environment variables for media paths
ENV MEDIA_DIR=/app/media
ENV TEMP_DIR=/app/tmp

# Start Xvfb and Gunicorn
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 -ac +extension GLX +render -noreset & gunicorn --bind 0.0.0.0:5001 --timeout 300 app:app"]