# Base Image: Python 3.10 Slim
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create a non-root user
RUN useradd -m -u 1000 aegis

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Common Tools
# (Already installed above)

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project Code
COPY . .

# Create data directory structure and set permissions
RUN mkdir -p data/logs data/cache data/models && \
    chown -R aegis:aegis /app

# Switch to non-root user
USER aegis

# Expose port
EXPOSE 5000

# Default Command
CMD ["python", "src/main.py"]
