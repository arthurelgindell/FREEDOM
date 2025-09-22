#!/usr/bin/env python
import argparse, os, json, time, random
from pathlib import Path
import numpy as np

# Minimal MLX BERT training using transformers tokenization + a simple MLX classifier.
# This is a pragmatic skeleton; replace with ml-explore/mlx-examples text/bert when needed.

import mlx.core as mx
import mlx.nn as nn
from datasets import load_dataset

class BertClassifier(nn.Module):
    def __init__(self, hidden=768, num_labels=2):
        super().__init__()
        # Tiny head; assume we use frozen embeddings from a simple bag-of-words style as placeholder.
        # For production: port ModernBERT/bert-base-uncased-mlx backbone.
        self.linear = nn.Linear(hidden, num_labels)

    def __call__(self, x):
        return self.linear(x)

def seed_all(seed=42):
    random.seed(seed); np.random.seed(seed); mx.random.seed(seed)

def load_jsonl(path):
    rows = []
    with open(path, "r") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-len", type=int, default=512)
    args = ap.parse_args()

    seed_all()
    os.makedirs(args.out, exist_ok=True)

    rows = load_jsonl(args.data)
    labels = sorted(list({r["label"] for r in rows}))
    label2id = {l:i for i,l in enumerate(labels)}
    # Extremely simple featurization: mean-pooled hashed token ids -> embedding matrix (toy example).
    # Replace with proper BERT backbone from MLX examples in real runs.
    vocab = {}
    def featurize(txt):
        tokens = txt.lower().split()
        ids = []
        for t in tokens:
            if t not in vocab:
                vocab[t] = len(vocab)+1
            ids.append(vocab[t])
        # embed ids into 768-d random embedding (fixed)
        emb = mx.random.normal((len(vocab)+1, 768))
        vecs = emb[mx.array(ids)]
        return mx.mean(vecs, axis=0)

    X = [featurize(r["text"]) for r in rows]
    y = [label2id[r["label"]] for r in rows]
    X = mx.stack(X)
    y = mx.array(y)

    model = BertClassifier(hidden=768, num_labels=len(labels))
    opt = mx.optimizer.Adam(learning_rate=args.lr)

    def loss_fn(logits, targets):
        return mx.losses.cross_entropy(logits, targets)

    for epoch in range(args.epochs):
        logits = model(X)
        loss = loss_fn(logits, y)
        opt.update(model, loss)
        print(f"epoch={epoch+1} loss={float(loss)}")

    mx.savez(os.path.join(args.out, "clf.npz"), **model.state_dict())
    with open(os.path.join(args.out, "labels.json"), "w") as f:
        json.dump({"labels": labels}, f, indent=2)

if __name__ == "__main__":
    main()
