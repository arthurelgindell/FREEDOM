#!/bin/bash

while true; do
  clear
  echo "=== Foundation-Sec-8B Download Monitor ==="
  echo "Time: $(date +%H:%M:%S)"
  echo ""

  # Check total download size
  total_size=$(du -ch models/Foundation-Sec-8B 2>/dev/null | grep total | awk '{print $1}')
  echo "Total Downloaded: $total_size"
  echo ""

  # Show individual file progress
  echo "Model Shards Progress:"
  for file in models/Foundation-Sec-8B/.cache/huggingface/download/*.incomplete; do
    if [ -f "$file" ]; then
      size=$(ls -lh "$file" | awk '{print $5}')
      name=$(basename "$file" | cut -c1-20)
      echo "  $name: $size"
    fi
  done

  # Check if download is complete
  if [ ! -f models/Foundation-Sec-8B/.cache/huggingface/download/*.incomplete 2>/dev/null ]; then
    echo ""
    echo "✅ Download appears to be complete!"
  fi

  echo ""
  echo "Press Ctrl+C to stop monitoring"
  sleep 5
done