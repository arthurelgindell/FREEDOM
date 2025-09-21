#!/usr/bin/env python3
"""Test OpenAI API key configuration"""

import os
from openai import OpenAI

def test_openai_key():
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY not set in environment")
        return False

    print(f"✓ API Key found: {api_key[:8]}...")

    try:
        client = OpenAI(api_key=api_key)

        # Test with a simple embedding
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input="Test embedding generation"
        )

        print(f"✓ Successfully generated embedding")
        print(f"  Model: {response.model}")
        print(f"  Dimensions: {len(response.data[0].embedding)}")
        print(f"  Usage: {response.usage.total_tokens} tokens")

        return True

    except Exception as e:
        print(f"❌ API Error: {e}")
        return False

if __name__ == "__main__":
    test_openai_key()