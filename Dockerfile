# ===============================
# Neuraluxe-AI v10k Hyperluxe Dockerfile
# Deployra-ready, no local build needed
# ===============================

# Base image with Python 3.10
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port from .env (default 10000)
EXPOSE 10000

# Set environment variables for production
ENV FLASK_ENV=production
ENV PORT=10000
ENV OPENAI_ENABLED=false
ENV CACHE_TYPE=simple
ENV LOG_LEVEL=info
ENV ENABLE_ENV_CHECK=true

# Start the app using Gunicorn + Uvicorn workers
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:10000", "--timeout", "120"]