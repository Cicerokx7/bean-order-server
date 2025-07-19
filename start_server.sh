#!/bin/bash

# Exit on any error
set -e

# Log function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/order_server.log
}

# Change to the server directory
cd /home/carousel/order-server

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    log "ERROR: Virtual environment not found. Creating it..."
    python3 -m venv venv
fi

# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    log "ERROR: Flask not found. Installing dependencies..."
    pip install Flask==2.3.3 requests==2.31.0
fi

# Start the server
log "Starting order server..."
exec python order_server.py 