"""Critic — verifies spec against generated files."""
import os
import re
import time
from .prompts import CRITIC


class Critic:
    def __init__(self, llm_client, config, log=None):
        self.llm = llm_client
        self.config = config
        self.log = log

    def review(self, spec_md, generated_files, output_dir):
        """Review all files and return (verdict, issues)."""
        file_snapshots = {}
        for fname in generated_files:
            path = os.path.join(output_dir, fname)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    file_snapshots[fname] = f.read()

        files_md = "\n\n".join(
            f"# FILE: {fname}\n```python\n{content}\n```"
            for fname, content in file_snapshots.items()
        )

        prompt = (
            f"# SPEC TO VERIFY:\n{spec_md}\n\n"
            f"# GENERATED FILES:\n{files_md}\n\n"
            "Review strictly. Output checklist + verdict."
        )

        if self.log:
            self.log.llm_request("CRITIC", "critic", self.config.get("model"), prompt, system=CRITIC)

        start = time.time()
        response = self.llm.complete(prompt, system=CRITIC)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("CRITIC", "critic", self.config.get("model"), response, duration)

        if "ALL_COMPLETE" in response:
            verdict = "ALL_COMPLETE"
            issues = []
        else:
            verdict = "NEEDS_FIXES"
            issues = self._extract_issues(response)

        return verdict, response, issues

    def _extract_issues(self, response):
        issues = []
        for line in response.split("\n"):
            if "✗" in line or "NEEDS FIXES" in line.upper():
                issues.append(line.strip())
        return issues
