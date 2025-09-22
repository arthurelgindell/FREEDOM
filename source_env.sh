#!/bin/bash
# Source this file to load FREEDOM environment variables
# Usage: source ./source_env.sh

source /Volumes/DATA/FREEDOM/.env
echo "✓ FREEDOM environment loaded"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
echo "  DB_NAME: $DB_NAME"
echo "  MLX_ENDPOINT: $MLX_ENDPOINT"
