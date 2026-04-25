"""Critic — verifies SPEC.md against generated files."""

import os
import re
import time

from .prompts import CRITIC


class Critic:
    def __init__(self, llm_client, config, log=None):
        self.llm = llm_client
        self.config = config
        self.log = log

    def review(self, spec_md: str, generated_files: list, output_dir: str) -> tuple:
        """
        Review all generated files against the spec.
        Returns (verdict: str, review_text: str, issues: list[str]).
        """
        # Read all generated files
        file_snapshots = {}
        for fname in generated_files:
            path = os.path.join(output_dir, fname)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    file_snapshots[fname] = f.read()

        # Build context: SPEC + files
        files_md = "\n\n".join(
            f"# FILE: {fname}\n```python\n{content}\n```"
            for fname, content in file_snapshots.items()
        )

        prompt = (
            "# VERIFICATION TASK\n"
            "Check that the generated code matches the SPEC.\n\n"
            f"# SPEC:\n{spec_md}\n\n"
            f"# GENERATED FILES:\n{files_md}\n\n"
            "Output the checklist + verdict as described in the system prompt."
        )

        if self.log:
            self.log.llm_request("CRITIC", "critic",
                                 self.config.get("model"), prompt, system=CRITIC)

        start = time.time()
        response = self.llm.complete(prompt, system=CRITIC)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("CRITIC", "critic",
                                   self.config.get("model"), response, duration)

        # Parse verdict
        if "ALL_COMPLETE" in response:
            verdict = "ALL_COMPLETE"
            issues = []
        else:
            verdict = "NEEDS_FIXES"
            issues = self._extract_issues(response)

        return verdict, response, issues

    @staticmethod
    def _extract_issues(response: str) -> list:
        """Extract problem descriptions from critic's review text."""
        issues = []
        for line in response.splitlines():
            line = line.strip()
            # Look for lines starting with problem indicators
            if re.match(r'^\d+\.', line) and any(
                kw in line.lower() for kw in ['missing', 'not found', 'wrong', 'error', 'broken', '✗']
            ):
                issues.append(line)
        return issues[:5]  # top 5 max
