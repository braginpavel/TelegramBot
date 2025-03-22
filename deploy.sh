#!/bin/bash

# Script to update the Telegram bot Docker container
# Usage: ./deploy.sh [container_name] [image_name]

# Default values if not provided
CONTAINER_NAME=${1:-"telegram_bot"}
IMAGE_NAME=${2:-"telegram_bot_image"}

echo "Starting deployment process..."

# Pull the latest code if using Git
# Uncomment the following line if you're using Git
# git pull

echo "Building new Docker image..."
docker rm image $IMAGE_NAME
docker build -t $IMAGE_NAME .

echo "Stopping and removing the current container..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

echo "Starting a new container with the updated image..."
docker run -d --name $CONTAINER_NAME --env-file ./.env

echo "Deployment completed successfully!"
echo "Container $CONTAINER_NAME is now running with the updated code."

# Optional: View logs from the new container
# docker logs -f $CONTAINER_NAME 