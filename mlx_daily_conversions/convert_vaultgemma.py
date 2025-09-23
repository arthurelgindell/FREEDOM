#!/usr/bin/env python3
"""
MLX Daily Conversion Script - VaultGemma 1B
Date: January 23, 2025
Target: google/vaultgemma-1b
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
MODEL_SOURCE = "google/vaultgemma-1b"
MODEL_NAME = "vaultgemma-1b"
MLX_REPO = f"mlx-community/{MODEL_NAME}-4bit"
WORK_DIR = Path("/Volumes/DATA/FREEDOM/MLXModels") / datetime.now().strftime("%Y%m%d")

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(cmd, description=""):
    """Execute command with error handling"""
    if description:
        log(description)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"❌ Command failed: {e.stderr}")
        return None

def main():
    log("=" * 60)
    log("MLX COMMUNITY DAILY CONTRIBUTION")
    log("=" * 60)
    log(f"Model: {MODEL_SOURCE}")
    log(f"Target: {MLX_REPO}")
    
    # Phase 1: Setup
    log("\n📁 Phase 1: Creating working directory...")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(WORK_DIR)
    
    # Phase 2: Environment check
    log("\n🔍 Phase 2: Checking MLX installation...")
    mlx_version = run_command(
        "python3 -c 'import mlx; import mlx_lm; print(f\"MLX={mlx.__version__}, MLX-LM={mlx_lm.__version__}\")'",
        "Verifying MLX packages"
    )
    
    if not mlx_version:
        log("Installing MLX packages...")
        run_command("pip3 install --upgrade mlx mlx-lm huggingface_hub")
        
    # Phase 3: Conversion
    log(f"\n🔄 Phase 3: Converting {MODEL_NAME} to MLX format...")
    start_time = time.time()
    
    conversion_cmd = f"""
    python3 -m mlx_lm.convert \
        --hf-path {MODEL_SOURCE} \
        --mlx-path ./{MODEL_NAME}-4bit \
        --quantize \
        --q-bits 4 \
        --q-group-size 64
    """
    
    result = run_command(conversion_cmd, f"Converting with 4-bit quantization")
    
    if not result:
        log("❌ Conversion failed. Exiting.")
        sys.exit(1)
        
    elapsed = time.time() - start_time
    log(f"✅ Conversion completed in {elapsed/60:.1f} minutes")
    
    # Phase 4: Validation
    log("\n🧪 Phase 4: Testing converted model...")
    
    test_script = f'''
from mlx_lm import load, generate
import sys

try:
    model, tokenizer = load("./{MODEL_NAME}-4bit")
    print("✅ Model loaded successfully")
    
    # Test generation
    test_prompts = [
        "Hello, I am",
        "The meaning of life is",
        "Explain quantum computing:"
    ]
    
    for prompt in test_prompts:
        response = generate(
            model, tokenizer,
            prompt=prompt,
            max_tokens=30,
            verbose=False
        )
        if len(response) > 0:
            print(f"✅ Generated for '{prompt[:20]}...'")
        else:
            print(f"⚠️ Empty response for '{prompt}'")
            
    # Check file sizes
    import os
    model_path = "./{MODEL_NAME}-4bit"
    total_size = 0
    for root, dirs, files in os.walk(model_path):
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    
    size_gb = total_size / 1e9
    print(f"📊 Total model size: {size_gb:.2f}GB")
    
    if size_gb < 0.1:
        print("❌ Model suspiciously small")
        sys.exit(1)
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)
'''
    
    with open("test_model.py", "w") as f:
        f.write(test_script)
    
    test_result = run_command("python3 test_model.py", "Running model tests")
    
    if not test_result:
        log("❌ Model testing failed")
        sys.exit(1)
    
    # Phase 5: Create README
    log("\n📝 Phase 5: Creating model card...")
    
    readme_content = f"""# {MODEL_NAME.title()} - MLX 4-bit

This model was converted to MLX format from [`{MODEL_SOURCE}`](https://huggingface.co/{MODEL_SOURCE}).

## About VaultGemma

VaultGemma is Google's first **privacy-preserving** language model, trained with Differential Privacy (DP) to provide strong mathematical guarantees that the model cannot memorize or reveal individual training examples. This makes it ideal for applications involving sensitive data.

## Key Features
- **Privacy-Preserving**: Trained with Differential Privacy
- **No Memorization**: Cannot reproduce training data sequences
- **Lightweight**: 1B parameters, perfect for on-device use
- **Gemma Architecture**: Based on proven Gemma 2 design

## Usage

```python
from mlx_lm import load, generate

model, tokenizer = load("mlx-community/{MODEL_NAME}-4bit")

prompt = "Explain differential privacy in simple terms:"
response = generate(model, tokenizer, prompt=prompt, max_tokens=200)
print(response)
```

## Conversion Details
- Original: [{MODEL_SOURCE}](https://huggingface.co/{MODEL_SOURCE})
- Quantization: 4-bit (q-group-size: 64)
- Converted: {datetime.now().strftime('%Y-%m-%d')}
- Hardware: Mac Studio M3 Ultra
- Framework: mlx-lm {mlx_version.split('MLX-LM=')[1].strip() if mlx_version and 'MLX-LM=' in mlx_version else 'latest'}

## Use Cases
- Privacy-sensitive applications
- Healthcare and financial analysis
- On-device personal assistants
- Research on privacy-preserving AI

## License
Please refer to Google's Gemma license terms for usage restrictions.
"""
    
    readme_path = Path(f"./{MODEL_NAME}-4bit/README.md")
    readme_path.write_text(readme_content)
    log("✅ README created")
    
    # Phase 6: Upload to Hugging Face
    log(f"\n📤 Phase 6: Uploading to {MLX_REPO}...")
    
    # Check HF authentication
    auth_check = run_command("huggingface-cli whoami", "Checking HF authentication")
    
    if not auth_check or "Not logged" in str(auth_check):
        log("⚠️ Not logged in to Hugging Face")
        log("Please run: huggingface-cli login")
        sys.exit(1)
    
    upload_cmd = f"""
    huggingface-cli upload \
        {MLX_REPO} \
        ./{MODEL_NAME}-4bit \
        --commit-message "Add VaultGemma 1B - First privacy-preserving MLX model" \
        --repo-type model
    """
    
    upload_result = run_command(upload_cmd, "Uploading to MLX Community")
    
    if upload_result and "error" not in upload_result.lower():
        log(f"✅ Successfully uploaded to https://huggingface.co/{MLX_REPO}")
    else:
        log("⚠️ Upload may have failed - check manually")
    
    # Phase 7: Report
    log("\n📊 Phase 7: Creating contribution report...")
    
    report = {
        "date": datetime.now().isoformat(),
        "model": MODEL_NAME,
        "source": MODEL_SOURCE,
        "quantization": "4bit",
        "conversion_time_minutes": round(elapsed/60, 1),
        "model_size_gb": size_gb if 'size_gb' in locals() else "Unknown",
        "upload_status": "SUCCESS" if upload_result else "FAILED",
        "repo_url": f"https://huggingface.co/{MLX_REPO}",
        "special_notes": "First privacy-preserving model in MLX Community"
    }
    
    # Save to log
    log_file = Path.home() / "mlx_contribution_log.json"
    
    if log_file.exists():
        with open(log_file) as f:
            logs = json.load(f)
    else:
        logs = {"conversions": []}
    
    logs["conversions"].append(report)
    
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)
    
    log("\n" + "=" * 60)
    log("🎉 DAILY MLX CONTRIBUTION COMPLETE!")
    log("=" * 60)
    log(f"Model: {MODEL_NAME}")
    log(f"Size: {report['model_size_gb']}GB")
    log(f"Time: {report['conversion_time_minutes']} minutes")
    log(f"URL: {report['repo_url']}")
    log("=" * 60)

if __name__ == "__main__":
    main()
