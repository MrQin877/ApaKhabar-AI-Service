"""Cross-platform local judge launcher; downloads Qwen separately from the writer."""
import os
import shutil
import subprocess

if __name__ == '__main__':
    server = shutil.which('llama-server')
    if not server:
        raise SystemExit('Install llama.cpp first: Windows: winget install llama.cpp; macOS: brew install llama.cpp')
    raise SystemExit(subprocess.call([
        server, '-hf', os.getenv('JUDGE_HF_MODEL', 'Qwen/Qwen3-4B-GGUF:Q4_K_M'),
        '--alias', 'apakhabar-judge', '--host', '127.0.0.1', '--port', '8082',
        '--ctx-size', '16384', '--parallel', '1', '--jinja', '--reasoning', 'off',
        '--n-gpu-layers', os.getenv('JUDGE_GPU_LAYERS', '99'),
    ]))
