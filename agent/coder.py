"""Coder — generates each file from spec + tool calls."""
import os
import re
import time
from .prompts import CODER


class Coder:
    def __init__(self, llm_client, config, session, log=None):
        self.llm = llm_client
        self.config = config
        self.session = session
        self.log = log

    def generate_files(self, spec_md, file_list, file_roles):
        """Generate all files in sequence. Returns list of filenames."""
        generated = []
        context = self._build_context(spec_md)

        for filename in file_list:
            role = file_roles.get(filename, "no role specified")
            prompt = (
                f"{context}\n\n"
                f"# File to generate: `{filename}`\n"
                f"# Role: {role}\n\n"
                f"Write this file now. Output only the <tool> call."
            )

            if self.log:
                self.log.llm_request("CODER", "coder", self.config.get("model"), prompt, system=CODER)

            start = time.time()
            response = self.llm.complete(prompt, system=CODER)
            duration = time.time() - start

            if self.log:
                self.log.llm_response("CODER", "coder", self.config.get("model"), response, duration)

            written = self._parse_tool_call(response)
            if written:
                path = os.path.join(self.session.output_dir, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(written["content"])
                generated.append(filename)
                if self.log:
                    self.log.file_generated("CODER", filename, written["content"])
                context += f"\n\n# Already generated: {filename}\n{written['content'][:500]}"
            else:
                print(f"  ⚠️  Coder could not parse tool call for {filename}")
                if self.log:
                    self.log.error("CODER", f"Parse failed for {filename}", data={"response": response})
        return generated

    def fix_file(self, filename, issue, current_content):
        """Fix a specific file based on critic feedback."""
        prompt = (
            f"# EXISTING FILE (read carefully):\n{current_content[:3000]}\n\n"
            f"# ISSUE TO FIX:\n{issue}\n\n"
            f"# File: {filename}\n\n"
            f"Fix this file. Output only the <tool> call."
        )

        if self.log:
            self.log.llm_request("CODER_FIX", "coder", self.config.get("model"), prompt, system=CODER)

        start = time.time()
        response = self.llm.complete(prompt, system=CODER)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("CODER_FIX", "coder", self.config.get("model"), response, duration)

        written = self._parse_tool_call(response)
        if written:
            path = os.path.join(self.session.output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(written["content"])
            if self.log:
                self.log.file_generated("CODER_FIX", filename, written["content"])
            return True
        return False

    def _build_context(self, spec_md):
        return (
            "# PROJECT SPEC:\n"
            f"{spec_md}\n\n"
            "# IMPORTANT: write the file to the path shown above using:\n"
            "<tool>{\"command\": \"write_file\", \"path\": \"FULL_PATH/FILENAME.py\", \"content\": \"...\"}</tool>"
        )

    def _parse_tool_call(self, response):
        """Extract write_file call from LLM response."""
        match = re.search(
            r'<tool>\s*{.*?"command"\s*:\s*"write_file".*?"path"\s*:\s*"([^"]+)".*?"content"\s*:\s*"(.*?)"\s*}',
            response,
            re.DOTALL,
        )
        if not match:
            match = re.search(r'"path"\s*:\s*"([^"]+)"[^}]*"content"\s*:\s*"(.*?)"', response, re.DOTALL)
        if match:
            path, content = match.groups()
            content = content.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            return {"path": path, "content": content}
        return None
