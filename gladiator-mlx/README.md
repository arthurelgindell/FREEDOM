# Gladiator — MLX-Optimized Cyber Models (macOS / Apple Silicon)

**Baseline models**: Foundation-Sec-8B (LLM) and SecureBERT (encoder).  
**Target**: On-device fine-tuning with MLX on Apple Silicon (M3 Ultra), LoRA/QLoRA for LLM; MLX BERT for classification/NER.

## Quickstart

```bash
# 1) Env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) (Optional) Convert + quantize LLM to MLX
make sec8b_convert  # default: 4-bit quant, uploads to local dir by default

# 3) Fine-tune LLM via LoRA
make sec8b_lora DATA=data/sample_sft.jsonl OUT=runs/gladiator-sec8b-lora

# 4) Train MLX-BERT classifier (distillation optional)
make bert_train DATA=data/sample_classification.jsonl OUT=runs/gladiator-bert-mlx

# 5) Evaluate
make eval LLM_CKPT=runs/gladiator-sec8b-lora BERT_CKPT=runs/gladiator-bert-mlx
```

### Dataset formats
- **SFT (LLM)**: JSONL with fields `instruction`, `input`, `output` (simple Alpaca-style) or `messages` chat format.
- **Classification (BERT)**: JSONL with fields `text`, `label` (int or string).

See `data/sample_sft.jsonl` and `data/sample_classification.jsonl`.

### Sources
- Foundation‑Sec‑8B on Hugging Face.
- SecureBERT paper (arXiv).
- MLX LM + Hugging Face MLX docs.
- QLoRA background (arXiv).

### Verification gates
1) Model loads in MLX with intended dtype/quant.
2) Train: loss decreases, no NaNs, throughput recorded.
3) Eval: pass configured thresholds on your task suite.
4) Artifact: adapters or merged weights + tokenizer saved with run manifest.
