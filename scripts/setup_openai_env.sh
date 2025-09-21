#!/bin/bash
# FREEDOM Platform - OpenAI Environment Setup Script
# This script ensures OpenAI API key is properly configured

echo "=== FREEDOM OpenAI Environment Setup ==="
echo

# Check if .env file exists
if [ ! -f "/Volumes/DATA/FREEDOM/.env" ]; then
    echo "❌ Error: .env file not found at /Volumes/DATA/FREEDOM/.env"
    exit 1
fi

# Source the environment file
source /Volumes/DATA/FREEDOM/.env

# Verify OpenAI key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not found in .env file"
    exit 1
fi

echo "✅ OpenAI API Key loaded: ${OPENAI_API_KEY:0:20}..."

# Test the API key
echo
echo "Testing OpenAI API connection..."
python3 -c "
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
try:
    response = client.embeddings.create(
        model='text-embedding-ada-002',
        input='test'
    )
    print('✅ OpenAI API connection successful!')
    print(f'   Model: text-embedding-ada-002')
    print(f'   Dimensions: {len(response.data[0].embedding)}')
except Exception as e:
    print(f'❌ API test failed: {e}')
    exit(1)
"

# Export for current session
export OPENAI_API_KEY="$OPENAI_API_KEY"

echo
echo "✅ Environment setup complete!"
echo
echo "To make this permanent, add to your shell profile:"
echo "  echo 'source /Volumes/DATA/FREEDOM/.env' >> ~/.zshrc"
echo
echo "Or run this script before using RAG services:"
echo "  source /Volumes/DATA/FREEDOM/scripts/setup_openai_env.sh"