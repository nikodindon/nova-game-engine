"""Architect — prompt → structured spec.md."""
import os
from .prompts import ARCHITECT


class Architect:
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config

    def build_spec(self, prompt, output_dir):
        full_prompt = f"# User request:\n{prompt}\n\nWrite the project specification."
        spec_md = self.llm.complete(full_prompt, system=ARCHITECT)
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
