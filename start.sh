#!/bin/bash

# FactTrace - Start Script
# Starts both backend (FastAPI) and frontend (Next.js)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting FactTrace...${NC}"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found. Please create one with OPENAI_API_KEY.${NC}"
    exit 1
fi

# Start backend
echo -e "${YELLOW}Starting backend on http://localhost:8000...${NC}"
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start frontend
echo -e "${YELLOW}Starting frontend on http://localhost:3000...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}Both services started!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:3000"
echo -e "  API Docs: http://localhost:8000/docs"
echo -e "\nPress Ctrl+C to stop both services."

# Wait for both processes
wait
