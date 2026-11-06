#!/usr/bin/env bash
set -euo pipefail

die() { printf '%s\n' "$*" >&2; exit 1; }

size=${1:-}
profile=${2:-smoke32}
case "$size" in
    8b)
        repo=Qwen3-8B
        revision=b968826d9c46dd6066d109eabc6255188de91218
        sha0=27fb78e716391ef21bb3255fa00846e32e021bc2801f7d3391a73f62d84bbb47
        sha26=2442a2e8f2dad2d5bdd88b0f4e054064548f28023246ea80473e46ddbc7dd786
        ;;
    14b)
        repo=Qwen3-14B
        revision=40c069824f4251a91eefaf281ebe4c544efd3e18
        sha0=a82c0cd548758be31f603d0f6b156f6ef57178363277bead42581e5df85a7512
        sha26=81d2d09784f6d4239f9dd0fb1fa3b99930966e01d78d5c5f949c123f191d1792
        ;;
    *) die "Usage: bash serve_wrd58.sh {8b|14b} [smoke32|yarn128]" ;;
esac
case "$profile" in
    smoke32) context=32768 ;;
    yarn128) context=131072 ;;
    *) die "Unknown context profile: $profile" ;;
esac

image=${WRD_VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.10.pre1-py3}
train_container=${WRD_TRAIN_CONTAINER:-wrd_build}
container="wrd58-vllm-$size"
command -v docker >/dev/null || die "Docker is required on Spark."
[[ $(uname -m) == aarch64 ]] || die "This launcher targets the aarch64 Spark host."

for running in wrd58-vllm-8b wrd58-vllm-14b; do
    if [[ $(docker inspect --type container --format '{{.State.Running}}' "$running" 2>/dev/null || true) == true ]]; then
        die "A WRD58 service is already running: $running. Stop it before switching size or context."
    fi
done

workspace=${WRD_WORKSPACE_ROOT:-$(docker inspect --type container --format '{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}' "$train_container" 2>/dev/null || true)}
hf_root=${WRD_HF_ROOT:-$(docker inspect --type container --format '{{range .Mounts}}{{if eq .Destination "/hfcache"}}{{.Source}}{{end}}{{end}}' "$train_container" 2>/dev/null || true)}
[[ "$workspace" = /* && -d "$workspace" ]] || die "Set WRD_WORKSPACE_ROOT to the Spark host path containing out58_${size}_v2."
[[ "$hf_root" = /* && -d "$hf_root/hub" ]] || die "Set WRD_HF_ROOT to the Spark host HF_HOME containing hub/."
workspace=$(realpath "$workspace")
hf_root=$(realpath "$hf_root")
snapshot="hub/models--Qwen--$repo/snapshots/$revision"
[[ -s "$hf_root/$snapshot/config.json" && -s "$hf_root/$snapshot/tokenizer_config.json" ]] || die "Frozen Qwen snapshot unavailable: $hf_root/$snapshot"

verify_adapter() {
    local step=$1 expected=$2 dir actual
    dir="$workspace/out58_${size}_v2/checkpoint-$step"
    [[ -s "$dir/adapter_config.json" && -s "$dir/adapter_model.safetensors" ]] || die "Incomplete adapter: $dir"
    actual=$(sha256sum "$dir/adapter_model.safetensors")
    [[ ${actual%% *} == "$expected" ]] || die "Adapter SHA256 mismatch: $dir"
}
verify_adapter 0 "$sha0"
verify_adapter 26 "$sha26"

image_id=$(docker image inspect --format '{{.Id}}' "$image" 2>/dev/null) || die "Local vLLM image unavailable. See the runbook for an explicit pull command. Image: $image"
[[ $(docker image inspect --format '{{.Architecture}}' "$image_id") == arm64 ]] || die "A Spark arm64 vLLM image is required."
if ! serve_help=$(docker run --rm --pull never --gpus all --entrypoint vllm "$image_id" serve --help=all 2>&1); then
    if ! serve_help=$(docker run --rm --pull never --gpus all --entrypoint vllm "$image_id" serve --help 2>&1); then
        printf '%s\n' "$serve_help" >&2
        die "The installed vLLM CLI did not start."
    fi
fi
for flag in --default-chat-template-kwargs --reasoning-parser --tool-call-parser --enable-auto-tool-choice --lora-modules --enable-lora --max-lora-rank --override-generation-config; do
    [[ "$serve_help" == *"$flag"* ]] || die "Installed vLLM CLI did not advertise $flag. Use the documented Spark image."
done

rope=()
if [[ "$profile" == yarn128 ]]; then
    if [[ "$serve_help" == *"--rope-scaling"* ]]; then
        rope=(--rope-scaling '{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}')
    elif [[ "$serve_help" == *"--hf-overrides"* ]]; then
        rope=(--hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}}')
    else
        die "Installed vLLM does not advertise a supported YaRN override option."
    fi
fi

printf 'spark_service size=%s profile=%s model_length=%s revision=%s image=%s\n' "$size" "$profile" "$context" "$revision" "$image_id"
printf 'spark_service adapter_0_sha256=%s adapter_26_sha256=%s\n' "$sha0" "$sha26"
exec docker run --rm --pull never --name "$container" --gpus all --ipc host --network host \
    --mount "type=bind,source=$hf_root,target=/hfcache,readonly" \
    --mount "type=bind,source=$workspace/out58_${size}_v2,target=/wrd-adapters,readonly" \
    -e HF_HOME=/hfcache -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e VLLM_NO_USAGE_STATS=1 \
    --entrypoint vllm "$image_id" serve "/hfcache/$snapshot" \
    --host 127.0.0.1 --port 18758 --dtype bfloat16 --enforce-eager \
    --max-model-len "$context" --max-num-seqs 1 --gpu-memory-utilization 0.75 \
    --served-model-name "wrd58-$size-bare" \
    --enable-lora --max-lora-rank 32 --max-loras 1 --max-cpu-loras 2 \
    --lora-modules "wrd58-$size-0=/wrd-adapters/checkpoint-0" "wrd58-$size-26=/wrd-adapters/checkpoint-26" \
    --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser hermes \
    --default-chat-template-kwargs '{"enable_thinking":true}' \
    --generation-config vllm --override-generation-config '{"temperature":0.6,"top_p":0.95,"top_k":20,"min_p":0.0}' \
    "${rope[@]}"
