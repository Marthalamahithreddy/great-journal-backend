#!/bin/bash
echo "Working directory: $(pwd)"
echo "Files here:"
ls -la
echo "Starting uvicorn..."
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
