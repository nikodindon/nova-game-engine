#!/usr/bin/env python3
"""
Nova Game Engine — AI-powered Python game generator.

Usage:
    python main.py "Space Invaders avec des aliens pixel art et des explosions"
    python main.py --session stellar-siege "create a breakout game"
    python main.py --list
    python main.py --play stellar-siege_20250425_143022
"""
import argparse
import os
import sys

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


def cmd_generate(session_name, prompt, config, play_immediately=False):
    """Run Architect → Coder → Critic loop, then optionally play."""
    print(f"\n🎮  Starting session: {session_name}")
    llm = LLMClient(config)

    session = Session(session_name).setup()
    architect = Architect(llm, config)
    coder = Coder(llm, config, session)
    critic = Critic(llm, config)
    planner = Planner(llm)

    # ── Step 1: Architect builds spec ────────────────────────────────────────
    print("\n📐  [1/4] Architect is writing the specification...")
    spec_md = architect.build_spec(prompt, session.output_dir)
    session.save_spec(spec_md)
    parsed = architect.parse_spec(spec_md)
    file_list = parsed["file_list"]
    file_roles = parsed["file_roles"]
    print(f"   Spec saved → {session.spec_path}")
    print(f"   Files: {', '.join(file_list)}")

    # ── Step 2: Coder generates all files ────────────────────────────────────
    print(f"\n💻  [2/4] Coder is generating {len(file_list)} file(s)...")
    generated = coder.generate_files(spec_md, file_list, file_roles)
    print(f"   Generated: {', '.join(generated)}")

    # ── Step 3: Critic reviews ───────────────────────────────────────────────
    print("\n🔍  [3/4] Critic is reviewing the code...")
    verdict, review_text, issues = critic.review(
        spec_md, generated, session.output_dir
    )
    print(f"   Verdict: {verdict}")
    if issues:
        for issue in issues[:5]:
            print(f"   {issue}")

    # ── Step 4: Fix loop (max 3 cycles) ───────────────────────────────────────
    cycle = 0
    while verdict != "ALL_COMPLETE" and cycle < MAX_CYCLES:
        cycle += 1
        print(f"\n🔧  [Fix cycle {cycle}/{MAX_CYCLES}]")
        fixes = planner.plan_fixes(review_text)
        if not fixes:
            print("   Planner could not produce a fix plan — skipping remaining cycles.")
            break
        for fix in fixes[:3]:
            fpath = fix.get("path", "")
            fname = os.path.basename(fpath)
            reason = fix.get("reason", "unknown")
            print(f"   Fix: {fname} — {reason}")
            if fname in generated and os.path.exists(os.path.join(session.output_dir, fname)):
                with open(os.path.join(session.output_dir, fname)) as fh:
                    current = fh.read()
                coder.fix_file(fname, reason, current)
            else:
                print(f"   ⚠️  File {fname} not found in generated files — skipping")
        # Re-review
        verdict, review_text, issues = critic.review(
            spec_md, generated, session.output_dir
        )
        print(f"   Re-verdict: {verdict}")

    # ── Done ───────────────────────────────────────────────────────────────────
    session.save_result(
        f"SESSION: {session_name}\n"
        f"PROMPT: {prompt}\n"
        f"VERDICT: {verdict}\n"
        f"CYCLES: {cycle}\n"
        f"GAME_DIR: {session.output_dir}\n\n"
        f"{spec_md}\n\n"
        f"## Review\n{review_text}"
    )
    print(f"\n✅  Session complete. Result → {session.result_path}")
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
    cmd_generate(session_name, prompt_text, config, play_immediately=True)


if __name__ == "__main__":
    main()
