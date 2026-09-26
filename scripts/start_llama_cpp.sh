#!/usr/bin/env bash
set -euo pipefail

model="${LLAMA_CPP_HF_MODEL:-ggml-org/gemma-4-E2B-it-GGUF:Q4_0}"
alias_name="${LLAMA_CPP_MODEL:-apakhabar-gemma}"
host="${LLAMA_CPP_HOST:-127.0.0.1}"
port="${LLAMA_CPP_PORT:-8080}"
context_size="${LLAMA_CPP_CONTEXT_SIZE:-8192}"
gpu_layers="${LLAMA_CPP_GPU_LAYERS:-99}"
parallel="${LLAMA_CPP_PARALLEL:-1}"

if ! command -v llama-server >/dev/null 2>&1; then
    echo "llama-server tidak ditemukan. Instal dengan: brew install llama.cpp" >&2
    exit 1
fi

echo "Starting ${alias_name} at http://${host}:${port}/v1"
echo "Model: ${model}"

exec llama-server \
    -hf "${model}" \
    --alias "${alias_name}" \
    --host "${host}" \
    --port "${port}" \
    --ctx-size "${context_size}" \
    --n-gpu-layers "${gpu_layers}" \
    --parallel "${parallel}" \
    --jinja \
    --reasoning off
