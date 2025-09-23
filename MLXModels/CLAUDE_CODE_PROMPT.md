# MLX Daily Model Conversion Assignment

## MISSION
Convert one high-impact Hugging Face model to MLX format daily and contribute it to the mlx-community on Hugging Face. You have access to 2x Mac Studio M3 Ultra systems (512GB + 256GB RAM, 160 GPUs total).

## WORKING DIRECTORY
All work should be done in: `/Volumes/DATA/FREEDOM/MLXModels/`

## TODAY'S TASK: Convert VaultGemma-1B

### Step 1: Discovery
Find a model that:
- Is trending on Hugging Face
- Is NOT already in mlx-community
- Has high community value
- Can be converted with available RAM

Today's target: `google/vaultgemma-1b` - Google's first privacy-preserving LLM with Differential Privacy

### Step 2: Setup Environment
```bash
cd /Volumes/DATA/FREEDOM/MLXModels
mkdir -p $(date +%Y%m%d)
cd $(date +%Y%m%d)

# Verify MLX installation
python3 -c "import mlx; import mlx_lm; print(f'MLX ready: {mlx.__version__}')"
```

### Step 3: Convert Model
```bash
python3 -m mlx_lm.convert \
    --hf-path google/vaultgemma-1b \
    --mlx-path ./vaultgemma-1b-4bit \
    --quantize \
    --q-bits 4 \
    --q-group-size 64
```

### Step 4: Test Model
```python
from mlx_lm import load, generate

# Load and test
model, tokenizer = load("./vaultgemma-1b-4bit")
response = generate(model, tokenizer, prompt="Hello world", max_tokens=50)
print(f"Test successful: {len(response) > 0}")
```

### Step 5: Create README
Create `./vaultgemma-1b-4bit/README.md`:

```markdown
# VaultGemma 1B - MLX 4-bit

This model was converted to MLX format from [`google/vaultgemma-1b`](https://huggingface.co/google/vaultgemma-1b).

## About VaultGemma
First privacy-preserving LLM trained with Differential Privacy, providing mathematical guarantees against memorization of training data.

## Usage
```python
from mlx_lm import load, generate
model, tokenizer = load("mlx-community/vaultgemma-1b-4bit")
response = generate(model, tokenizer, prompt="Your prompt here")
```

## Conversion Details
- Quantization: 4-bit
- Date: [TODAY'S DATE]
- Hardware: Mac Studio M3 Ultra
```

### Step 6: Upload to Hugging Face
```bash
huggingface-cli upload \
    mlx-community/vaultgemma-1b-4bit \
    ./vaultgemma-1b-4bit \
    --commit-message "Add VaultGemma 1B - First privacy-preserving MLX model" \
    --repo-type model
```

### Step 7: Log Success
Create/append to `/Volumes/DATA/FREEDOM/MLXModels/contribution_log.json`:
```json
{
  "date": "2025-01-23",
  "model": "vaultgemma-1b",
  "source": "google/vaultgemma-1b",
  "quantization": "4bit",
  "uploaded": true,
  "repo": "mlx-community/vaultgemma-1b-4bit"
}
```

## SUCCESS CRITERIA
- [ ] Model converts without errors
- [ ] Model loads and generates text
- [ ] Model size is reasonable (>0.5GB)
- [ ] README includes usage examples
- [ ] Successfully uploaded to mlx-community
- [ ] Contribution logged

## NEXT MODELS TO CONSIDER
After VaultGemma, consider these for subsequent days:
1. Any new Gemma variants not yet converted
2. New vision models (check if MLX-VLM compatible)
3. New releases from DeepSeek, Alibaba, or Meta
4. Community-requested models from MLX GitHub issues

## DAILY WORKFLOW
1. Check what's trending: `https://huggingface.co/models?sort=trending`
2. Verify not already converted: `https://huggingface.co/mlx-community`
3. Pick highest value unconverted model
4. Execute conversion pipeline
5. Test thoroughly
6. Upload with good documentation
7. Log contribution

Execute this now with VaultGemma-1B as today's target!
