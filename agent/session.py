"""Session — manages a single game project generation session."""
import os
import shutil
import datetime


class Session:
    def __init__(self, name, base_dir=None):
        self.name = name
        self.created_at = datetime.datetime.now()
        self.base_dir = base_dir or os.path.expanduser("~/nova-game-engine/sessions")
        self.session_dir = os.path.join(self.base_dir, f"{name}_{self.created_at:%Y%m%d_%H%M%S}")
        self.output_dir = os.path.join(self.session_dir, "game")
        self.spec_path = os.path.join(self.session_dir, "SPEC.md")
        self.result_path = os.path.join(self.session_dir, "result.txt")

    def setup(self):
        os.makedirs(self.output_dir, exist_ok=True)
        return self

    def save_spec(self, spec_md):
        with open(self.spec_path, "w", encoding="utf-8") as f:
            f.write(spec_md)

    def save_result(self, result_md):
        with open(self.result_path, "w", encoding="utf-8") as f:
            f.write(result_md)

    @property
    def game_dir(self):
        return self.output_dir
