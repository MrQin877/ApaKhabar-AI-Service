#!/usr/bin/env bash
set -euo pipefail

echo "Script started"

model="${LLAMA_CPP_HF_MODEL:-ggml-org/gemma-4-E2B-it-GGUF:Q4_0}"
alias_name="${LLAMA_CPP_MODEL:-apakhabar-gemma}"
host="${LLAMA_CPP_HOST:-127.0.0.1}"
port="${LLAMA_CPP_PORT:-8080}"
context_size="${LLAMA_CPP_CONTEXT_SIZE:-8192}"
gpu_layers="${LLAMA_CPP_GPU_LAYERS:-99}"
parallel="${LLAMA_CPP_PARALLEL:-1}"

# Git Bash mounts C: at /c; WSL mounts it at /mnt/c.
windows_drive="/c"
if [ -d /mnt/c/Users ]; then
    windows_drive="/mnt/c"
fi
LLAMA_SERVER_PATH="${LLAMA_SERVER_PATH:-${windows_drive}/Users/yingx/AppData/Local/Microsoft/WinGet/Packages/ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe/llama-server.exe}"

if [ ! -f "${LLAMA_SERVER_PATH}" ]; then
    echo "llama-server tidak ditemukan: ${LLAMA_SERVER_PATH}" >&2
    echo "Set LLAMA_SERVER_PATH to the executable path for your Bash environment." >&2
    exit 1
fi

echo "Found llama-server: ${LLAMA_SERVER_PATH}"

echo "Starting ${alias_name} at http://${host}:${port}/v1"
echo "Model: ${model}"

exec "${LLAMA_SERVER_PATH}" \
    -hf "${model}" \
    --alias "${alias_name}" \
    --host "${host}" \
    --port "${port}" \
    --ctx-size "${context_size}" \
    --n-gpu-layers "${gpu_layers}" \
    --parallel "${parallel}" \
    --jinja \
    --reasoning off
