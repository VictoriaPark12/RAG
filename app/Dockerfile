FROM python:3.11-slim

WORKDIR /app

# Disable Python output buffering
ENV PYTHONUNBUFFERED=1

# Install system dependencies for PyTorch and transformers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_rag.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_rag.txt

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["python", "-u", "main.py"]

