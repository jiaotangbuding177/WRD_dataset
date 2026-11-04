#!/bin/bash
# Runs INSIDE container wrd_build. Waits for the orphaned 8B v2 run to exit, then launches 14B v2.
LOG=/workspace/logs58/launcher.log
while pgrep -f "wrd_train58.py --model 8b" >/dev/null; do sleep 60; done
echo "[handoff $(date -Is)] 8b exited; steps=$(grep -c "^\[step" /workspace/logs58/train_8b_v2.log 2>/dev/null)" >> $LOG
if ls -d /workspace/out58_8b_v2/checkpoint-241 >/dev/null 2>&1; then
  echo "[handoff $(date -Is)] 8b checkpoint-241 PRESENT" >> $LOG
else
  echo "[handoff $(date -Is)] WARNING: 8b checkpoint-241 MISSING" >> $LOG
fi
cd /workspace
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/hfcache
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True TOKENIZERS_PARALLELISM=false
echo "[handoff $(date -Is)] START 14b -> /workspace/out58_14b_v2" >> $LOG
/opt/wrd/bin/python /workspace/wrd_train58.py --model 14b --output-dir /workspace/out58_14b_v2 --profile budget_projection > /workspace/logs58/train_14b_v2.log 2>&1
rc=$?
echo "[handoff $(date -Is)] END 14b rc=$rc" >> $LOG
