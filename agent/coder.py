"""Coder — generates each file from spec + tool calls."""
import os
import re
from .prompts import CODER


class Coder:
    def __init__(self, llm_client, config, session):
        self.llm = llm_client
        self.config = config
        self.session = session

    def generate_files(self, spec_md, file_list, file_roles):
        """Generate all files in sequence. Returns list of (filename, path)."""
        generated = []
        # Build context: spec + already-generated files
        context = self._build_context(spec_md)

        for filename in file_list:
            role = file_roles.get(filename, "no role specified")
            prompt = (
                f"{context}\n\n"
                f"# File to generate: `{filename}`\n"
                f"# Role: {role}\n\n"
                f"Write this file now. Output only the <tool> call."
            )
            response = self.llm.complete(prompt, system=CODER)
            written = self._parse_tool_call(response)
            if written:
                path = os.path.join(self.session.output_dir, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(written["content"])
                generated.append(filename)
                # Update context for next file
                context += f"\n\n# Already generated: {filename}\n{written['content'][:500]}"
            else:
                print(f"  ⚠️  Coder could not parse tool call for {filename}")
        return generated

    def fix_file(self, filename, issue, current_content):
        """Fix a specific file based on critic feedback."""
        prompt = (
            f"# EXISTING FILE (read carefully):\n{current_content[:3000]}\n\n"
            f"# ISSUE TO FIX:\n{issue}\n\n"
            f"# File: {filename}\n\n"
            f"Fix this file. Output only the <tool> call."
        )
        response = self.llm.complete(prompt, system=CODER)
        written = self._parse_tool_call(response)
        if written:
            path = os.path.join(self.session.output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(written["content"])
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
            # Try simpler pattern
            match = re.search(r'"path"\s*:\s*"([^"]+)"[^}]*"content"\s*:\s*"(.*?)"', response, re.DOTALL)
        if match:
            path, content = match.groups()
            # Unescape newlines
            content = content.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            return {"path": path, "content": content}
        return None
