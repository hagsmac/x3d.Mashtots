"""Download tokenizer.json only (plus tiktoken BPE files) into one new directory per source. Data files, never executed."""
import os, sys
from huggingface_hub import hf_hub_download
root = sys.argv[1]
repos = {"nemotron-nano-9b-v2": "nvidia/NVIDIA-Nemotron-Nano-9B-v2", "gpt-oss-20b": "openai/gpt-oss-20b",
         "mistral-nemo": "mistralai/Mistral-Nemo-Instruct-2407", "deepseek-v3": "deepseek-ai/DeepSeek-V3"}
for name, repo in repos.items():
    d = os.path.join(root, "tok-" + name); os.makedirs(d, exist_ok=False)
    try:
        p = hf_hub_download(repo, "tokenizer.json", local_dir=d); print("OK  ", name, os.path.getsize(p))
    except Exception as e: print("FAIL", name, type(e).__name__, str(e)[:150])
