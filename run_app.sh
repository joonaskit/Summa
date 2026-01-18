#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Backend (FastAPI)..."
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

sleep 3 # Wait a bit for backend to start

echo "Starting Frontend (Streamlit)..."
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo "Services running. Press Ctrl+C to stop."
wait $BACKEND_PID $FRONTEND_PID
