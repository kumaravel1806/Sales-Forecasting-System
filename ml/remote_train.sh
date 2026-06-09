#!/usr/bin/env bash
# Remote training helper (example). Use on a cloud VM with GPU + TensorFlow installed.
# Usage: ./remote_train.sh path/to/data.csv
set -euo pipefail

INPUT=${1:-}
if [ -z "$INPUT" ]; then
  echo "Usage: $0 <input.csv|xlsx>" >&2
  exit 1
fi

# Activate your environment here if needed, e.g. conda/venv
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate retail-ml

export PYTHONPATH=backend:$PYTHONPATH
python -m backend.ml.train_lstm --input "$INPUT" --config ml/config.cloud.yaml
