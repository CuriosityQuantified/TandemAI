#!/bin/bash
# Quick test script for creating ATLAS tasks

echo "Creating test task..."
curl -X POST http://localhost:8000/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"description": "Create a simple plan to organize my code", "type": "general", "priority": "medium"}'
echo ""