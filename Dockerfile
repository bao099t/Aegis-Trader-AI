# Base Image: Python 3.10 Slim (Lightweight & Fast)
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies (build-essential needed for some py packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Common Tools (Optional: curl/ping for debugging)
RUN apt-get update && apt-get install -y curl

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project Code
COPY . .

# Create data directory structure if missing
RUN mkdir -p data/logs data/cache data/models

# Expose port (if web dashboard is added later - e.g. 5000)
EXPOSE 5000

# Default Command: Launch the Zenith Hybrid Core
CMD ["python", "src/main.py"]
