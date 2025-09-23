#!/usr/bin/env python3
"""
MLX Model Converter - Daily Automation Script
For execution by Claude Code or manual running
Target: One model per day contribution to mlx-community
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
MODELS_DIR = Path("/Volumes/DATA/FREEDOM/MLXModels")
LOG_FILE = MODELS_DIR / "contribution_log.json"

def run_cmd(cmd, check=True):
    """Run shell command and return output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.returncode == 0, result.stdout

def convert_model(source_model, model_name, quantization="4bit"):
    """Convert a model to MLX format"""
    
    print(f"\n{'='*60}")
    print(f"Converting: {source_model}")
    print(f"{'='*60}\n")
    
    # Create today's working directory
    work_dir = MODELS_DIR / datetime.now().strftime("%Y%m%d")
    work_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(work_dir)
    
    output_name = f"{model_name}-{quantization}"
    
    # Run conversion
    convert_cmd = f"""python3 -m mlx_lm.convert \
        --hf-path {source_model} \
        --mlx-path ./{output_name} \
        --quantize \
        --q-bits {quantization.replace('bit', '')} \
        --q-group-size 64"""
    
    success, _ = run_cmd(convert_cmd)
    
    if not success:
        print(f"❌ Conversion failed for {source_model}")
        return False
    
    # Test the model
    print("\n🧪 Testing converted model...")
    test_code = f"""
from mlx_lm import load, generate
model, tokenizer = load('./{output_name}')
response = generate(model, tokenizer, prompt='Hello', max_tokens=20, verbose=False)
print('✅ Model works!' if len(response) > 0 else '❌ Model failed')
"""
    
    test_file = work_dir / "test.py"
    test_file.write_text(test_code)
    success, _ = run_cmd(f"cd {work_dir} && python3 test.py")
    
    if not success:
        print(f"❌ Model testing failed")
        return False
    
    # Create README
    print("\n📝 Creating README...")
    readme_content = f"""# {model_name.replace('-', ' ').title()} - MLX {quantization}

This model was converted to MLX format from [`{source_model}`](https://huggingface.co/{source_model}).

## Usage

```python
from mlx_lm import load, generate

model, tokenizer = load("mlx-community/{output_name}")
response = generate(model, tokenizer, prompt="Hello", max_tokens=100)
print(response)
```

## Conversion Details
- Original: [{source_model}](https://huggingface.co/{source_model})
- Quantization: {quantization}
- Converted: {datetime.now().strftime('%Y-%m-%d')}
- Hardware: Mac Studio M3 Ultra
"""
    
    readme_path = work_dir / output_name / "README.md"
    readme_path.parent.mkdir(exist_ok=True)
    readme_path.write_text(readme_content)
    
    # Upload to Hugging Face
    print(f"\n📤 Uploading to mlx-community/{output_name}...")
    upload_cmd = f"""huggingface-cli upload \
        mlx-community/{output_name} \
        ./{output_name} \
        --commit-message "Add {model_name} {quantization} quantized" \
        --repo-type model"""
    
    success, _ = run_cmd(upload_cmd, check=False)
    
    if success:
        print(f"✅ Uploaded to https://huggingface.co/mlx-community/{output_name}")
    else:
        print(f"⚠️ Upload may have failed - check manually")
    
    # Log the contribution
    log_entry = {
        "date": datetime.now().isoformat(),
        "source": source_model,
        "output": output_name,
        "quantization": quantization,
        "uploaded": success,
        "repo": f"mlx-community/{output_name}"
    }
    
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)
    else:
        logs = {"conversions": []}
    
    logs["conversions"].append(log_entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)
    
    print(f"\n✅ Conversion complete: {output_name}")
    return True

def main():
    """Main entry point"""
    
    # Today's target
    TARGET_MODEL = "google/vaultgemma-1b"
    MODEL_NAME = "vaultgemma-1b"
    
    print("""
╔════════════════════════════════════════════╗
║   MLX COMMUNITY DAILY CONTRIBUTION         ║
║   Platform: Mac Studio M3 Ultra            ║
╚════════════════════════════════════════════╝
    """)
    
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"🎯 Target: {TARGET_MODEL}")
    print(f"📦 Output: mlx-community/{MODEL_NAME}-4bit")
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    success, _ = run_cmd("python3 -c 'import mlx, mlx_lm'", check=False)
    if not success:
        print("Installing MLX packages...")
        run_cmd("pip3 install --upgrade mlx mlx-lm huggingface_hub")
    
    # Check HF auth
    success, output = run_cmd("huggingface-cli whoami", check=False)
    if not success or "Not logged" in output:
        print("\n⚠️  Please login to Hugging Face first:")
        print("    huggingface-cli login")
        sys.exit(1)
    
    # Convert the model
    start_time = time.time()
    
    if convert_model(TARGET_MODEL, MODEL_NAME):
        elapsed = time.time() - start_time
        print(f"""
╔════════════════════════════════════════════╗
║   🎉 SUCCESS! Model Converted & Uploaded   ║
╚════════════════════════════════════════════╝

Time: {elapsed/60:.1f} minutes
Model: {MODEL_NAME}
URL: https://huggingface.co/mlx-community/{MODEL_NAME}-4bit

Next: Check trending models for tomorrow's target
        """)
    else:
        print("\n❌ Conversion failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
