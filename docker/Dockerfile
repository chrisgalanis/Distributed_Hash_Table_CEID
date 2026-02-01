# Dockerfile for DHT Node

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask requests

# Copy application code
COPY dht/ ./dht/
COPY distributed/ ./distributed/

# Expose port
EXPOSE 8000

# Set Python path
ENV PYTHONPATH=/app

# Run node server
ENTRYPOINT ["python", "-m", "distributed.node_server"]
