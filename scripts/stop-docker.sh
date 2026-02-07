#!/bin/bash
# Stop Docker Compose nodes

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' is available"
    exit 1
fi

echo "Stopping all DHT nodes..."
$DOCKER_COMPOSE -f docker/docker-compose.yml down

echo "✓ All nodes stopped and removed"
