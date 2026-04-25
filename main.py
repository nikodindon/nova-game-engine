#!/usr/bin/env python3
"""
Nova Game Engine — AI-powered Python game generator.

Usage:
    python main.py "Space Invaders avec des aliens pixel art et des explosions"
    python main.py --session stellar-siege "create a breakout game"
    python main.py --list
    python main.py --play stellar-siege_20250425_143022
    python main.py --debug "Space Invaders minimal"
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import load_config
from core.llm import LLMClient
from agent.architect import Architect
from agent.coder import Coder
from agent.critic import Critic
from agent.planner import Planner
from agent.session import Session


MAX_CYCLES = 3


# ─── Debug Logger ─────────────────────────────────────────────────────────────

class DebugLogger:
    """
    Ecrit tout en JSON Lines dans un fichier debug.log de session.
    Chaque ligne = un evenement horodate.

    Quand debug=False : ecrit quand meme les evenements majeurs (session start,
    verdict, erreurs) mais pas les prompts/responses LLM complets.
    """

    def __init__(self, session_dir, debug=False):
        self.session_dir = session_dir
        self.debug = debug
        self.log_path = os.path.join(session_dir, "debug.log")
        self._file = open(self.log_path, "a", encoding="utf-8")
        self._logger = logging.getLogger(f"nova.debug.{session_dir}")
        # Suppress default handlers
        self._logger.handlers = []
        self._logger.propagate = False

    def _write(self, event_type, step, data=None, msg=None):
        line = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event_type,
            "step": step,
            "msg": msg,
            "data": data,
        }
        self._file.write(json.dumps(line, ensure_ascii=False) + "\n")
        self._file.flush()

    def debug_event(self, step, msg, data=None):
        self._write("DEBUG", step, data=data, msg=msg)

    def info(self, step, msg, data=None):
        self._write("INFO", step, data=data, msg=msg)

    def error(self, step, msg, data=None):
        self._write("ERROR", step, data=data, msg=msg)

    def llm_request(self, step, agent, model, prompt, system=None):
        if self.debug:
            self._write("LLM_REQ", step, data={
                "agent": agent,
                "model": model,
                "system": system,
                "prompt": prompt,
                "prompt_len": len(prompt),
            })

    def llm_response(self, step, agent, model, response, duration_s):
        if self.debug:
            self._write("LLM_RESP", step, data={
                "agent": agent,
                "model": model,
                "response": response,
                "response_len": len(response),
                "duration_s": round(duration_s, 2),
            })
        else:
            self._write("LLM_RESP", step, data={
                "agent": agent,
                "model": model,
                "response_len": len(response),
                "duration_s": round(duration_s, 2),
            })

    def file_generated(self, step, filename, content):
        self._write("FILE_GENERATED", step, data={
            "filename": filename,
            "content": content,
            "size_bytes": len(content.encode()),
        })

    def verdict(self, step, verdict, review_text):
        self._write("VERDICT", step, data={
            "verdict": verdict,
            "review": review_text,
        })

    def close(self):
        self._file.close()


# ─── Core generation loop ────────────────────────────────────────────────────

def cmd_generate(session_name, prompt, config, debug=False, play_immediately=False):
    """Run Architect -> Coder -> Critic loop, then optionally play."""
    session = Session(session_name).setup()
    log = DebugLogger(session.session_dir, debug=debug)

    log.info("SESSION_START", f"Starting session: {session_name}", data={
        "session_name": session_name,
        "prompt": prompt,
        "model": config.get("model"),
        "provider": config.get("provider"),
        "debug": debug,
    })

    print(f"\n🎮  Starting session: {session_name}" + (" [DEBUG MODE]" if debug else ""))
    llm = LLMClient(config)

    architect = Architect(llm, config, log)
    coder = Coder(llm, config, session, log)
    critic = Critic(llm, config, log)
    planner = Planner(llm, log)

    # ── Step 1: Architect builds spec ────────────────────────────────────────
    step = "ARCHITECT"
    print(f"\n📐  [1/4] Architect is writing the specification...")
    log.info(step, "Starting Architect")

    start = time.time()
    spec_md = architect.build_spec(prompt)
    duration = time.time() - start

    session.save_spec(spec_md)
    parsed = architect.parse_spec(spec_md)
    file_list = parsed["file_list"]
    file_roles = parsed["file_roles"]

    log.llm_response(step, "architect", config.get("model"), spec_md, duration)
    log.info(step, f"Spec complete — {len(file_list)} files", data={
        "file_list": file_list,
        "spec_len": len(spec_md),
    })
    print(f"   Spec saved → {session.spec_path}")
    print(f"   Files: {', '.join(file_list)}")

    # ── Step 2: Coder generates all files ────────────────────────────────────
    step = "CODER"
    print(f"\n💻  [2/4] Coder is generating {len(file_list)} file(s)...")
    log.info(step, f"Starting generation of {len(file_list)} files")

    start = time.time()
    generated = coder.generate_files(spec_md, file_list, file_roles)
    duration = time.time() - start

    for fname in generated:
        fpath = os.path.join(session.output_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            log.file_generated(step, fname, content)
    log.info(step, f"All files generated in {duration:.1f}s", data={
        "generated": generated,
        "duration_s": round(duration, 2),
    })
    print(f"   Generated: {', '.join(generated)}")

    # ── Step 3: Critic reviews ───────────────────────────────────────────────
    step = "CRITIC"
    print("\n🔍  [3/4] Critic is reviewing the code...")
    log.info(step, "Starting Critic review")

    start = time.time()
    verdict, review_text, issues = critic.review(spec_md, generated, session.output_dir)
    duration = time.time() - start

    log.verdict(step, verdict, review_text)
    log.llm_response(step, "critic", config.get("model"), review_text, duration)
    log.info(step, f"Review complete — verdict={verdict}", data={
        "verdict": verdict,
        "issues_count": len(issues),
    })
    print(f"   Verdict: {verdict}")
    if issues:
        for issue in issues[:5]:
            print(f"   {issue}")

    # ── Step 4: Fix loop (max 3 cycles) ───────────────────────────────────────
    cycle = 0
    while verdict != "ALL_COMPLETE" and cycle < MAX_CYCLES:
        cycle += 1
        step = f"FIX_CYCLE_{cycle}"
        print(f"\n🔧  [Fix cycle {cycle}/{MAX_CYCLES}]")
        log.info(step, "Starting fix cycle")

        fixes = planner.plan_fixes(review_text)
        if not fixes:
            print("   Planner could not produce a fix plan — skipping remaining cycles.")
            log.info(step, "Planner returned no fixes")
            break

        for fix in fixes[:3]:
            fpath = fix.get("path", "")
            fname = os.path.basename(fpath)
            reason = fix.get("reason", "unknown")
            print(f"   Fix: {fname} — {reason}")
            log.info(step, f"Applying fix: {fname}", data={"reason": reason})

            if fname in generated and os.path.exists(os.path.join(session.output_dir, fname)):
                with open(os.path.join(session.output_dir, fname)) as fh:
                    current = fh.read()

                start = time.time()
                coder.fix_file(fname, reason, current)
                duration = time.time() - start

                # Reload and log
                fpath_full = os.path.join(session.output_dir, fname)
                if os.path.exists(fpath_full):
                    with open(fpath_full, encoding="utf-8") as f:
                        new_content = f.read()
                    log.file_generated(step, fname, new_content)
                    log.llm_response(step, "coder", config.get("model"), "fix applied", duration)
            else:
                print(f"   ⚠️  File {fname} not found in generated files — skipping")
                log.error(step, f"File not found: {fname}")

        # Re-review
        start = time.time()
        verdict, review_text, issues = critic.review(spec_md, generated, session.output_dir)
        duration = time.time() - start

        log.verdict(step, verdict, review_text)
        log.llm_response(step, "critic", config.get("model"), review_text, duration)
        print(f"   Re-verdict: {verdict}")

    # ── Done ───────────────────────────────────────────────────────────────────
    log.info("SESSION_DONE", f"Session complete — verdict={verdict}", data={
        "verdict": verdict,
        "cycles": cycle,
        "generated_files": generated,
        "session_dir": session.session_dir,
        "game_dir": session.output_dir,
    })

    session.save_result(
        f"SESSION: {session_name}\n"
        f"PROMPT: {prompt}\n"
        f"MODEL: {config.get('model')}\n"
        f"VERDICT: {verdict}\n"
        f"CYCLES: {cycle}\n"
        f"GAME_DIR: {session.output_dir}\n\n"
        f"{spec_md}\n\n"
        f"## Review\n{review_text}"
    )

    log.close()

    print(f"\n✅  Session complete. Result → {session.result_path}")
    print(f"   Debug log  → {session.session_dir}/debug.log")
    print(f"   Game files → {session.output_dir}")

    if play_immediately or verdict == "ALL_COMPLETE":
        launch_game(session.output_dir)

    return session


def cmd_list(config):
    """List all sessions."""
    sessions_dir = os.path.expanduser("~/nova-game-engine/sessions")
    if not os.path.exists(sessions_dir):
        print("No sessions found.")
        return
    for entry in sorted(os.listdir(sessions_dir), reverse=True):
        print(f"  {entry}")


def launch_game(game_dir):
    """Try to run the generated game."""
    main_py = os.path.join(game_dir, "main.py")
    if os.path.exists(main_py):
        print(f"\n🚀  Launching game from {game_dir}...")
        os.chdir(game_dir)
        os.system(f"{sys.executable} main.py")
    else:
        print(f"\n⚠️  No main.py found in {game_dir} — can't auto-launch.")


def main():
    parser = argparse.ArgumentParser(description="Nova Game Engine")
    parser.add_argument("prompt", nargs="*", help="Game description")
    parser.add_argument("--session", "-s", help="Session name (auto-generated if omitted)")
    parser.add_argument("--list", "-l", action="store_true", help="List past sessions")
    parser.add_argument("--play", "-p", metavar="SESSION_ID", help="Play a session's game")
    parser.add_argument("--config", "-c", default="config.json", help="Config file")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging (full prompts/responses)")
    parser.add_argument("--no-play", action="store_true", help="Don't auto-launch game after generation")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.list:
        cmd_list(config)
        return

    if args.play:
        sessions_dir = os.path.expanduser("~/nova-game-engine/sessions")
        game_dir = os.path.join(sessions_dir, args.play, "game")
        launch_game(game_dir)
        return

    prompt_text = " ".join(args.prompt)
    if not prompt_text:
        print(__doc__)
        return

    session_name = args.session or prompt_text.split()[0].lower()
    play = not args.no_play
    cmd_generate(session_name, prompt_text, config, debug=args.debug, play_immediately=play)


if __name__ == "__main__":
    main()
