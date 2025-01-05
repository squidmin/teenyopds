#!/bin/bash

# Find containers running on port 5000
container_ids=$(docker ps --filter "publish=5000" --format "{{.ID}}")

if [ -z "$container_ids" ]; then
  echo "No containers are using port 5000."
else
  echo "Stopping containers running on port 5000..."
  for container_id in $container_ids; do
    docker stop "$container_id"
    echo "Stopped container $container_id."
  done
fi
