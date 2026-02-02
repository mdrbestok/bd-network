#!/bin/bash
# Start script for Biotech Deal Network (SQLite mode)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Biotech Deal Network - Starting..."
echo "============================================"

# Check for required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm is required but not installed."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$PROJECT_DIR/frontend" && npm install
fi

# Check if backend dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing backend dependencies..."
    cd "$PROJECT_DIR/backend" && pip3 install -r requirements.txt
fi

# Kill any existing processes on our ports
echo "Checking for existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start backend in background
echo "Starting backend on http://localhost:8001..."
cd "$PROJECT_DIR/backend"
USE_SQLITE=true python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Start frontend in background
echo "Starting frontend on http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev &
FRONTEND_PID=$!

# Wait for frontend
echo "Waiting for frontend to start..."
sleep 5

echo ""
echo "============================================"
echo "Services are running!"
echo "============================================"
echo ""
echo "  Backend API:  http://localhost:8001"
echo "  Frontend:     http://localhost:3000"
echo "  API Docs:     http://localhost:8001/docs"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Click 'Ingest Data' to load MuM trials"
echo "  3. Explore the network!"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Handle shutdown
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
