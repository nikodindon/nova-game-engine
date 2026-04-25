"""Coder — generates each file from SPEC.md as Markdown code blocks."""

import os
import re
import time
import ast
import sys

from .prompts import CODER


class Coder:
    FILE_ORDER = ["constants.py", "entities.py", "sound_manager.py", "main.py"]

    def __init__(self, llm_client, config, session, log=None):
        self.llm = llm_client
        self.config = config
        self.session = session
        self.log = log

    def generate_files(self, spec_md, file_list, file_roles):
        """Generate all files in sequence. Returns list of filenames actually written."""
        # Respect file order: constants first, main last
        ordered = sorted(file_list, key=lambda f: (
            0 if f == "constants.py" else
            99 if f == "main.py" else
            50
        ))

        generated = []
        # Cumulatif context: already-written files feed into next prompts
        already_generated = ""

        for filename in ordered:
            role = file_roles.get(filename, "no role specified")
            prompt = self._build_prompt(spec_md, filename, role, already_generated)

            if self.log:
                self.log.llm_request("CODER", "coder",
                                     self.config.get("model"), prompt, system=CODER)

            start = time.time()
            response = self.llm.complete(prompt, system=CODER)
            duration = time.time() - start

            if self.log:
                self.log.llm_response("CODER", "coder",
                                       self.config.get("model"), response, duration)

            code = self._extract_code_block(response)
            if code is None:
                print(f"  ⚠️  No code block found for {filename} — skipping")
                if self.log:
                    self.log.error("CODER", f"No code block for {filename}",
                                   data={"response": response[:500]})
                continue

            # Syntax validation before writing
            if not self._validate_syntax(code, filename):
                print(f"  ⚠️  Syntax error in {filename} — attempting fix prompt")
                code = self._fix_syntax(code, filename)

            path = os.path.join(self.session.output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)

            generated.append(filename)
            if self.log:
                self.log.file_generated("CODER", filename, code)

            already_generated += f"\n\n# === {filename} ===\n{code[:1500]}"
            print(f"  ✓ {filename} ({len(code)} chars, {duration:.1f}s)")

        return generated

    def fix_file(self, filename, issue, current_content):
        """Rewrite a specific file to fix the given issue."""
        prompt = (
            f"# EXISTING FILE:\n"
            f"```python\n{current_content}\n```\n\n"
            f"# ISSUE TO FIX:\n"
            f"{issue}\n\n"
            f"# Write the COMPLETE fixed version of {filename}.\n"
            f"Output only a ```python code block."
        )

        if self.log:
            self.log.llm_request("CODER_FIX", "coder",
                                 self.config.get("model"), prompt, system=CODER)

        start = time.time()
        response = self.llm.complete(prompt, system=CODER)
        duration = time.time() - start

        if self.log:
            self.log.llm_response("CODER_FIX", "coder",
                                  self.config.get("model"), response, duration)

        code = self._extract_code_block(response)
        if code is None:
            print(f"  ⚠️  Fix: no code block for {filename}")
            return False

        if not self._validate_syntax(code, filename):
            code = self._fix_syntax(code, filename)

        path = os.path.join(self.session.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        if self.log:
            self.log.file_generated("CODER_FIX", filename, code)
        print(f"  ✓ {filename} fixed ({duration:.1f}s)")
        return True

    # ─── Prompt building ─────────────────────────────────────────────────────

    def _build_prompt(self, spec_md, filename, role, already_generated):
        context = (
            "# PROJECT SPEC:\n"
            f"{spec_md}\n\n"
            "# ALREADY GENERATED FILES:\n"
            f"{already_generated if already_generated else '(none yet)'}\n\n"
        )

        instructions = {
            "constants.py": (
                "Write constants.py FIRST. It defines all tunable values.\n"
                "Include: SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, all colors as (R,G,B) tuples,\n"
                "all speeds, sizes, timings. Every other file imports from constants.py."
            ),
            "entities.py": (
                "Write entities.py SECOND. Import everything from constants.\n"
                "Define: Player, Enemy, Bullet, Star (background), Explosion.\n"
                "Each class has update(self, dt_ms) and draw(self, surface)."
            ),
            "sound_manager.py": (
                "Write sound_manager.py THIRD. Import pygame, numpy.\n"
                "Generate all sounds procedurally with numpy. Pre-build Sound objects.\n"
                "Expose a SoundManager class with play(self, name) method."
            ),
            "main.py": (
                "Write main.py LAST. Import from constants, entities, sound_manager.\n"
                "Assemble: game loop, event handling, state machine, collision detection,\n"
                "HUD rendering, title screen, game-over screen."
            ),
        }

        extra = instructions.get(filename, "")
        return (
            f"{context}\n"
            f"# FILE TO WRITE: `{filename}`\n"
            f"# ROLE: {role}\n"
            f"{extra}\n\n"
            f"Output ONLY a ```python code block containing the complete {filename} file."
        )

    # ─── Code block extraction ──────────────────────────────────────────────

    def _extract_code_block(self, response: str):
        """
        Robust extraction: find first ```python and last ```.
        Strips the markdown markers. Returns None if no block found.
        """
        # Remove markdown code fences with optional language tag
        pattern = r'```(?:python)?\s*(.*?)\s*```'
        matches = re.findall(pattern, response, re.DOTALL)

        if not matches:
            return None

        # Take the largest match (usually the main code block)
        code = max(matches, key=len).strip()

        # Clean up common issues
        code = self._clean_code(code)
        return code if code else None

    @staticmethod
    def _clean_code(code: str) -> str:
        """Remove residual markdown artifacts."""
        lines = code.splitlines()
        cleaned = []
        for line in lines:
            # Remove lines that are just markdown artifacts
            if line.strip() in ('```', '```python', '```py'):
                continue
            # Remove lines that are LLM monologue/prompt-echo
            if re.match(r'^(Write the|Create the|Here is|This file)', line.strip()):
                continue
            cleaned.append(line)
        result = '\n'.join(cleaned)
        # Remove leading blank lines
        result = result.lstrip('\n')
        return result

    # ─── Syntax validation ───────────────────────────────────────────────────

    @staticmethod
    def _validate_syntax(code: str, filename: str) -> bool:
        """Check Python syntax via ast.parse. Returns True if valid."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            print(f"    SyntaxError in {filename}:{e.lineno} — {e.msg}")
            return False

    def _fix_syntax(self, code: str, filename: str) -> str:
        """Attempt to auto-fix common syntax errors."""
        lines = code.splitlines()
        fixed = []
        errors = 0

        for i, line in enumerate(lines, 1):
            original = line
            # Fix common issues
            line = line.rstrip()

            # Unclosed strings: line ends with " or ' without closing
            if re.search(r'["\']\s*$', line) and not line.strip().startswith('#'):
                # Skip this line
                errors += 1
                continue

            # Fix bare "return" without value when not in function
            # (very rough heuristic)
            fixed.append(line)

        result = '\n'.join(fixed)
        try:
            ast.parse(result)
            print(f"    Auto-fixed {errors} line(s) in {filename}")
            return result
        except SyntaxError:
            print(f"    Auto-fix failed for {filename} — keeping original")
            return code
