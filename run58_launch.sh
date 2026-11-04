#!/bin/bash
# audit58 sequential training launcher: 8B control first, then 14B main.
# Runs INSIDE container wrd_build via: docker exec -d wrd_build bash /workspace/run58_launch.sh
# All logs land in /workspace/logs58/ (host: ~/WRD_dataset/logs58/).
set -u
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HOME=/hfcache
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
cd /workspace
mkdir -p /workspace/logs58
PY=/opt/wrd/bin/python

run_model () {
  local m=$1 out=$2 log=$3
  echo "[launcher $(date -Is)] START $m -> $out" >> /workspace/logs58/launcher.log
  $PY /workspace/wrd_train58.py --model "$m" --output-dir "$out" \
      --profile budget_projection > "$log" 2>&1
  local rc=$?
  echo "[launcher $(date -Is)] END $m rc=$rc" >> /workspace/logs58/launcher.log
  return $rc
}

run_model 8b /workspace/out58_8b /workspace/logs58/train_8b.log
rc8=$?
run_model 14b /workspace/out58_14b /workspace/logs58/train_14b.log
rc14=$?
echo "[launcher $(date -Is)] ALL_DONE rc8=$rc8 rc14=$rc14" >> /workspace/logs58/launcher.log
