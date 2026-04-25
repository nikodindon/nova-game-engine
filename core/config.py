"""Load config from config.json with defaults."""
import json
import os

DEFAULT_CONFIG = {
    "base_url": "http://localhost:11434/v1",
    "api_key": "ollama",
    "model": "qwen2.5-coder:7b",
    "context_size": 32768,
    "max_out_tokens": 4096,
    "temperature": 0.1,
}


def load_config(config_path="config.json"):
    if os.path.exists(config_path):
        with open(config_path) as f:
            user = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(user)
        return cfg
    return DEFAULT_CONFIG.copy()
