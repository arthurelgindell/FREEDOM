
SHELL := /bin/bash
PY := python
VENV := .venv

# Adjustable
SEC8B_HF ?= fdtn-ai/Foundation-Sec-8B
SEC8B_OUT ?= runs/sec8b-mlx
SEC8B_QUANT ?= 4

.PHONY: setup sec8b_convert sec8b_lora bert_train eval

setup:
	python -m venv $(VENV) && source $(VENV)/bin/activate && pip install -r requirements.txt

sec8b_convert:
	$(PY) -m mlx_lm.convert --hf-path $(SEC8B_HF) -q --bits $(SEC8B_QUANT) --out $(SEC8B_OUT)

# LoRA finetune Foundation-Sec-8B (expects MLX-ready model; mlx-lm can also pull HF directly)
sec8b_lora:
	$(PY) -m mlx_lm.finetune \
	  --model $(SEC8B_OUT) \
	  --dataset $(DATA) \
	  --train-type lora \
	  --lora-r 16 --lora-alpha 32 \
	  --lora-target-modules q_proj k_proj v_proj o_proj \
	  --batch-size 64 --grad-accum 2 \
	  --max-seq-len 4096 \
	  --epochs 2 \
	  --learning-rate 1.5e-4 \
	  --dtype bf16 \
	  --save-best $(OUT)

bert_train:
	$(PY) scripts/train_bert_gladiator.py --data $(DATA) --out $(OUT) --epochs 3 --batch-size 128 --lr 3e-5 --max-len 512

eval:
	$(PY) scripts/eval_gladiator.py --llm_ckpt $(LLM_CKPT) --bert_ckpt $(BERT_CKPT) --sft_eval data/sample_sft.jsonl --clf_eval data/sample_classification.jsonl
