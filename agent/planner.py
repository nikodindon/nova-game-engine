"""Planner — turns critic output into fix actions."""
import json
from .prompts import PLANNER


class Planner:
    def __init__(self, llm_client):
        self.llm = llm_client

    def plan_fixes(self, critic_response):
        prompt = critic_response + "\n\nProduce the fix plan as JSON."
        response = self.llm.complete(prompt, system=PLANNER)
        # Extract JSON
        try:
            # Find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return []
