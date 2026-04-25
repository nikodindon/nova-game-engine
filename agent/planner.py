"""Planner — turns critic output into fix actions."""
import json
import time
from .prompts import PLANNER


class Planner:
    def __init__(self, llm_client, log=None):
        self.llm = llm_client
        self.log = log

    def plan_fixes(self, critic_response):
        prompt = critic_response + "\n\nProduce the fix plan as JSON."

        if self.log:
            self.log.llm_request("PLANNER", "planner", self.llm.model if hasattr(self.llm, "model") else "unknown", prompt, system=PLANNER)

        start = time.time()
        response = self.llm.complete(prompt, system=PLANNER)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("PLANNER", "planner", self.llm.model if hasattr(self.llm, "model") else "unknown", response, duration)

        try:
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1
            if start_idx != -1:
                return json.loads(response[start_idx:end_idx])
        except json.JSONDecodeError:
            pass
        return []
