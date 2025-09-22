#!/usr/bin/env python3
"""
Start MLX-VLM server for UI-TARS integration
"""

import sys
import os
import uvicorn
from mlx_vlm.server import app, load_model_resources

def main():
    """Start the MLX-VLM server"""
    model_path = "./models/portalAI/UI-TARS-1.5-7B-mlx-bf16"

    if not os.path.exists(model_path):
        print(f"❌ Model not found at: {model_path}")
        sys.exit(1)

    print(f"🚀 Starting MLX-VLM server with model: {model_path}")
    print(f"📡 Server will be available at: http://localhost:8000")
    print(f"🔗 API endpoint: http://localhost:8000/v1")

    # Load model resources
    load_model_resources(model_path)

    # Start server on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()