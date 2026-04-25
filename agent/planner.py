"""Planner — turns critic output into fix actions (JSON)."""

import json
import time

from .prompts import PLANNER


class Planner:
    def __init__(self, llm_client, log=None):
        self.llm = llm_client
        self.log = log

    def plan_fixes(self, critic_response: str) -> list:
        prompt = (
            f"# Critic's review:\n{critic_response}\n\n"
            "Based on the problems above, produce a fix plan as JSON.\n"
            "Output ONLY a JSON array, no markdown, no explanation."
        )

        if self.log:
            self.log.llm_request("PLANNER", "planner",
                                 self.llm.model if hasattr(self.llm, "model") else "unknown",
                                 prompt, system=PLANNER)

        start = time.time()
        response = self.llm.complete(prompt, system=PLANNER)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("PLANNER", "planner",
                                  self.llm.model if hasattr(self.llm, "model") else "unknown",
                                  response, duration)

        # Parse JSON — find first [ ... ]
        try:
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1
            if start_idx != -1:
                parsed = json.loads(response[start_idx:end_idx])
                # Normalise: support both "file" and "path" keys
                for item in parsed:
                    if "path" in item and "file" not in item:
                        item["file"] = item["path"]
                return parsed[:3]  # max 3 fixes
        except json.JSONDecodeError:
            pass

        return []
