# MLX Model Conversion - Quick Start

## For Claude Code / LM API Execution

### One-liner to run today's conversion:
```bash
cd /Volumes/DATA/FREEDOM/MLXModels && python3 daily_mlx_convert.py
```

### Manual step-by-step:
```bash
# 1. Navigate to working directory
cd /Volumes/DATA/FREEDOM/MLXModels

# 2. Run the automated conversion
python3 daily_mlx_convert.py

# The script will:
# - Convert google/vaultgemma-1b to MLX 4-bit
# - Test the model
# - Create documentation
# - Upload to mlx-community
# - Log the contribution
```

### To convert a different model:
Edit line 139-140 in daily_mlx_convert.py:
```python
TARGET_MODEL = "organization/model-name"  # Change this
MODEL_NAME = "model-name"                 # Change this
```

### Check what needs converting:
1. Visit: https://huggingface.co/models?sort=trending
2. Check: https://huggingface.co/mlx-community
3. Find models in #1 but not in #2

### Today's target:
**VaultGemma 1B** - Google's first privacy-preserving LLM with Differential Privacy

### Expected output:
- Working directory: `/Volumes/DATA/FREEDOM/MLXModels/20250123/`
- Converted model: `vaultgemma-1b-4bit/`
- HF repository: `mlx-community/vaultgemma-1b-4bit`
- Estimated time: 15-30 minutes

### Prerequisites check:
```bash
python3 -c "import mlx, mlx_lm; print('MLX ready')"
huggingface-cli whoami
```

If not logged in to HF:
```bash
huggingface-cli login
```

## Success Verification
After completion, verify at:
https://huggingface.co/mlx-community/vaultgemma-1b-4bit

## Next Steps
Tomorrow, update the TARGET_MODEL in the script to convert the next trending unconverted model.
