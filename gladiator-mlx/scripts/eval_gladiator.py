#!/usr/bin/env python
import argparse, os, json
import mlx.core as mx
import mlx.nn as nn

def load_labels(path):
    with open(os.path.join(path,"labels.json")) as f:
        return json.load(f)["labels"]

class Clf(nn.Module):
    def __init__(self, w, b):
        super().__init__()
        self.linear = nn.Linear(w.shape[0], w.shape[1])
        self.linear.weight = mx.array(w.T)
        self.linear.bias = mx.array(b)

    def __call__(self, x):
        return self.linear(x)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm_ckpt", required=True)
    ap.add_argument("--bert_ckpt", required=True)
    ap.add_argument("--sft_eval", required=True)
    ap.add_argument("--clf_eval", required=True)
    args = ap.parse_args()
    # LLM eval left as placeholder (use mlx_lm.generate + prompt list); focus on wiring.
    print("LLM checkpoint path:", args.llm_ckpt)
    # Simple classifier load (toy)
    clf_npz = mx.loadz(os.path.join(args.bert_ckpt, "clf.npz"))
    labels = load_labels(args.bert_ckpt)
    print("Classifier labels:", labels)
    print("Eval harness ready. Implement dataset-specific metrics here.")

if __name__ == "__main__":
    main()
