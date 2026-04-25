"""Critic — verifies spec against generated files."""
import os
import re
from .prompts import CRITIC


class Critic:
    def __init__(self, llm_client, config):
        self.llm = llm_client

    def review(self, spec_md, generated_files, output_dir):
        """Review all files and return (verdict, issues)."""
        # Load all file contents
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

        response = self.llm.complete(prompt, system=CRITIC)

        # Extract verdict
        if "ALL_COMPLETE" in response:
            verdict = "ALL_COMPLETE"
            issues = []
        else:
            verdict = "NEEDS_FIXES"
            # Extract top issues from response
            issues = self._extract_issues(response)

        return verdict, response, issues

    def _extract_issues(self, response):
        issues = []
        for line in response.split("\n"):
            if "✗" in line or "NEEDS FIXES" in line.upper():
                issues.append(line.strip())
        return issues
