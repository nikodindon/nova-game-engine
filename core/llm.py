"""
core/llm.py — Client LLM pour Nova Game Engine.

Provider supportes :
  - "llama-server"  → HTTP POST /v1/chat/completions  (notre default)
  - "ollama"        → ollama run <model>  (CLI, mode interactif)

Usage :
  from core.llm import LLMClient
  client = LLMClient({"provider": "llama-server", "model": "...", "base_url": "http://localhost:8081"})
  response = client.complete("ton prompt")
"""

import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error


class LLMClient:
    """
    Client LLM simple, sans verrou (une seule session a la fois pour game dev).
    Pour llama-server : HTTP POST OpenAI-compatible.
    Pour ollama CLI   : subprocess stdin/stdout.
    """

    def __init__(self, config: dict):
        self.provider = config.get("provider", "llama-server")
        self.model    = config.get("model", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")
        self.base_url = config.get("base_url", "http://localhost:8081").rstrip("/")
        self.timeout  = int(config.get("timeout", 300))
        self.temperature = float(config.get("temperature", 0.1))
        self.max_tokens  = int(config.get("max_out_tokens", 4096))

    def complete(self, prompt: str, system: str = None) -> str:
        """Envoie un prompt et retourne la reponse LLM."""
        if self.provider == "llama-server":
            return self._call_llama_server(prompt, system)
        else:
            return self._call_ollama_cli(prompt, system)

    # ── llama-server (HTTP) ─────────────────────────────────────────────────────

    def _call_llama_server(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }).encode("utf-8")

        url = f"{self.base_url}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_err = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if "error" in data:
                    raise RuntimeError(f"LLM error: {data['error']}")
                return data["choices"][0]["message"]["content"]
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
        raise RuntimeError(f"llama-server request failed after 3 attempts: {last_err}")

    # ── Ollama CLI ─────────────────────────────────────────────────────────────

    def _call_ollama_cli(self, prompt: str, system: str = None) -> str:
        full_prompt = prompt
        if system:
            full_prompt = f"[SYSTEM]\n{system}\n\n[USER]\n{prompt}"

        env = {**os.environ, "TERM": "dumb", "NO_COLOR": "1"}
        result = subprocess.run(
            ["ollama", "run", self.model],
            input=full_prompt,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return self._clean_ansi(result.stdout)

    @staticmethod
    def _clean_ansi(text: str) -> str:
        """Supprime les codes ANSI residuals."""
        text = re.sub(r'\x1b\[[0-9;]*[mGKHFABCDSuJh]', '', text)
        text = re.sub(r'\[\d+[ABCDEFGHJKSTSu]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()
