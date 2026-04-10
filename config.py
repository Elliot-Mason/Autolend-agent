LLM_PROVIDER = "lmstudio"     # Change to "lmstudio" to use LM Studio
MODEL = "qwen3:8b"    
OLLAMA_BASE_URL = "http://localhost:11434"
LMSTUDIO_BASE_URL = "http://localhost:1234/v1"

import os

def load_system_prompt(path: str = None) -> str:
    if path is None:
        # Use absolute path relative to this config file
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

SYSTEM_PROMPT = load_system_prompt()