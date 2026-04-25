"""Architect — prompt → structured SPEC.md."""

import os
import re
import time

from .prompts import ARCHITECT


class Architect:
    def __init__(self, llm_client, config, log=None):
        self.llm = llm_client
        self.config = config
        self.log = log

    def build_spec(self, prompt: str) -> str:
        full_prompt = (
            "# User request:\n"
            f"{prompt}\n\n"
            "Write the project specification in the exact format described in the system prompt."
        )

        if self.log:
            self.log.llm_request("ARCHITECT", "architect",
                                 self.config.get("model"), full_prompt, system=ARCHITECT)

        start = time.time()
        spec_md = self.llm.complete(full_prompt, system=ARCHITECT)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("ARCHITECT", "architect",
                                   self.config.get("model"), spec_md, duration)

        return spec_md

    @staticmethod
    def parse_spec(spec_md: str) -> dict:
        """
        Extract file list and roles from SPEC.md markdown.
        Also extracts features for the Critic to verify against.
        """
        # File list: - `filename.py` — role description
        files = re.findall(r"- `([^`]+)` —", spec_md)

        roles = {}
        for f in files:
            match = re.search(rf"- `{re.escape(f)}` — (.+)", spec_md)
            if match:
                roles[f] = match.group(1).strip()

        # Features: numbered items under ## Fonctionnalités
        features = []
        feat_section = re.search(
            r'## Fonctionnalités\s*\n((?:- .+\n)*)', spec_md, re.MULTILINE
        )
        if feat_section:
            for line in feat_section.group(1).splitlines():
                m = re.match(r'^\s*\*?\s*\d+\.\s*\*\*(.+?)\*\*:', line)
                if m:
                    features.append(m.group(1).strip())
                elif line.strip().startswith('-'):
                    features.append(line.strip().lstrip('-* '))

        return {
            "file_list": files,
            "file_roles": roles,
            "features": features,
        }
