.PHONY: help up down logs ingest test clean dev-backend dev-frontend install

# Default target
help:
	@echo "Biotech Deal Network - Available Commands"
	@echo ""
	@echo "Quick Start (no Docker required):"
	@echo "  make install     - Install Python and Node dependencies"
	@echo "  make up          - Start backend and frontend (SQLite mode)"
	@echo "  make ingest      - Ingest MuM clinical trials data"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend  - Run backend only (port 8000)"
	@echo "  make dev-frontend - Run frontend only (port 3000)"
	@echo "  make test         - Run backend tests"
	@echo ""
	@echo "Docker (requires Docker):"
	@echo "  make docker-up    - Start with Docker Compose"
	@echo "  make docker-down  - Stop Docker services"
	@echo ""

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	cd backend && pip3 install -r requirements.txt
	@echo ""
	@echo "Installing Node dependencies..."
	cd frontend && npm install
	@echo ""
	@echo "Dependencies installed!"

# Start backend (SQLite mode - no Docker needed)
dev-backend:
	@echo "Starting backend (SQLite mode) on port 8001..."
	cd backend && USE_SQLITE=true python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Start frontend
dev-frontend:
	@echo "Starting frontend..."
	cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev

# Start both (run in separate terminals)
up:
	@echo "============================================"
	@echo "Starting Biotech Deal Network (SQLite mode)"
	@echo "============================================"
	@echo ""
	@echo "Run these in separate terminals:"
	@echo ""
	@echo "Terminal 1 (Backend):"
	@echo "  make dev-backend"
	@echo ""
	@echo "Terminal 2 (Frontend):"
	@echo "  make dev-frontend"
	@echo ""
	@echo "Then run 'make ingest' to load data."
	@echo ""
	@echo "Or use the quick-start script:"
	@echo "  ./scripts/start.sh"

# Ingest MuM data
ingest:
	@echo "Ingesting MuM clinical trials data..."
	curl -X POST "http://localhost:8001/api/ingest/clinicaltrials" \
		-H "Content-Type: application/json" \
		-d '{"indication": "MuM", "max_trials": 100}'
	@echo ""
	@echo "Ingestion complete! Open http://localhost:3000 to view the network."

# Run backend tests
test:
	@echo "Running backend tests..."
	cd backend && python3 -m pytest tests/ -v

# Check health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8001/api/health | python3 -m json.tool

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf backend/data/bdnetwork.db
	rm -rf frontend/.next
	rm -rf frontend/node_modules/.cache
	@echo "Cleaned!"

# ==================== Docker Commands ====================

# Start with Docker
docker-up:
	@echo "Starting with Docker Compose..."
	docker compose up -d --build
	@echo ""
	@echo "Services starting..."
	@echo "  - Neo4j:    http://localhost:7474"
	@echo "  - Backend:  http://localhost:8000"
	@echo "  - Frontend: http://localhost:3000"

# Stop Docker
docker-down:
	docker compose down

# Docker logs
docker-logs:
	docker compose logs -f
