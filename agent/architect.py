"""Architect — prompt → structured spec.md."""
import os
import time
from .prompts import ARCHITECT


class Architect:
    def __init__(self, llm_client, config, log=None):
        self.llm = llm_client
        self.config = config
        self.log = log

    def build_spec(self, prompt):
        full_prompt = f"# User request:\n{prompt}\n\nWrite the project specification."
        if self.log:
            self.log.llm_request("ARCHITECT", "architect", self.config.get("model"), full_prompt, system=ARCHITECT)

        start = time.time()
        spec_md = self.llm.complete(full_prompt, system=ARCHITECT)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("ARCHITECT", "architect", self.config.get("model"), spec_md, duration)
        return spec_md

    @staticmethod
    def parse_spec(spec_md):
        """Extract file list and roles from spec markdown."""
        import re
        files = re.findall(r"- `([^`]+)` —", spec_md)
        roles = {}
        for f in files:
            match = re.search(rf"- `{re.escape(f)}` — (.+)", spec_md)
            if match:
                roles[f] = match.group(1).strip()
        return {"file_list": files, "file_roles": roles}
