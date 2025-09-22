#!/bin/bash
# Start script for RAG API with virtual environment

cd /Volumes/DATA/FREEDOM/services/rag_chunker
source /Volumes/DATA/FREEDOM/.venv/bin/activate
exec python3 rag_api.py