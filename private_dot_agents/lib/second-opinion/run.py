#!/usr/bin/env python3
"""Run one independent, full-permission review using a pinned model."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
MODELS = {"claude": ("claude-opus-5-5", "high"), "codex": ("gpt-6.1-sol", "xhigh")}


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    except ProcessLookupError:
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer", choices=MODELS)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--brief", required=True, type=Path, help="Requirements and exact review scope")
    parser.add_argument("--timeout", type=int, default=1800, help="Wall-clock seconds (default: 1800)")
    args = parser.parse_args()
    if os.environ.get("SECOND_OPINION_ACTIVE"):
        parser.error("Already inside a second-opinion review; return findings to the author instead.")
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        parser.error("--repo must be an existing directory")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        brief = args.brief.expanduser().resolve().read_text()
    except OSError as error:
        parser.error(str(error))
    if not brief.strip():
        parser.error("--brief must contain requirements and review scope")
    binary = shutil.which(args.reviewer)
    if not binary:
        parser.error(f"{args.reviewer} is not on PATH")

    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "second-opinion"
    cache.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"{args.reviewer}-", dir=cache))
    prompt = (HERE / "review-contract.md").read_text() + "\n\n# Review brief\n\n" + brief
    (output / "prompt.md").write_text(prompt)
    model, effort = MODELS[args.reviewer]
    report = output / "report.md"
    if args.reviewer == "codex":
        command = [binary, "exec", "--model", model, "-c", f'model_reasoning_effort="{effort}"',
                   "--dangerously-bypass-approvals-and-sandbox", "--ephemeral",
                   "--skip-git-repo-check", "--json", "--output-last-message", str(report), "-"]
    else:
        command = [binary, "--print", "--model", model, "--effort", effort,
                   "--dangerously-skip-permissions", "--no-session-persistence", "--output-format", "json"]
    env = os.environ.copy()
    env["SECOND_OPINION_ACTIVE"] = "1"
    if args.reviewer == "claude":
        # A fresh CLI subprocess, not a continuation of the caller's Claude session.
        env.pop("CLAUDECODE", None)
    metadata = {"reviewer": args.reviewer, "model": model, "effort": effort,
                "repo": str(repo), "command": command, "status": "running"}
    meta_path = output / "run.json"
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Review artifacts: {output}", flush=True)
    started = time.monotonic()
    result_code = 1
    try:
        with (output / "prompt.md").open() as stdin, (output / "stdout.log").open("w") as stdout, \
                (output / "stderr.log").open("w") as stderr:
            process = subprocess.Popen(command, cwd=repo, env=env, stdin=stdin,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = process.wait(timeout=args.timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                stop(process)
                raise
        metadata["exit_code"] = code
        if code != 0:
            raise RuntimeError(f"Reviewer exited with code {code}; inspect stderr.log and stdout.log")
        if args.reviewer == "claude":
            payload = json.loads((output / "stdout.log").read_text())
            if payload.get("is_error"):
                raise RuntimeError(f"Claude reported an error: {payload.get('result', payload.get('errors'))}")
            text = payload.get("result")
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Claude returned no final review")
            report.write_text(text + "\n")
        if not report.is_file() or not report.read_text().strip():
            raise RuntimeError("Reviewer returned no final review")
        metadata["status"] = "completed"
        result_code = 0
        print(f"Review completed: {report}")
    except subprocess.TimeoutExpired:
        metadata.update(status="timed_out", error=f"Exceeded {args.timeout} seconds")
        result_code = 124
    except KeyboardInterrupt:
        metadata.update(status="interrupted", error="Interrupted by caller")
        result_code = 130
    except (OSError, ValueError, RuntimeError, AttributeError) as error:
        metadata.update(status="failed", error=str(error))
    finally:
        metadata["duration_seconds"] = round(time.monotonic() - started, 2)
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    if result_code:
        print(f"Review {metadata['status']}: {metadata['error']}\nArtifacts: {output}", file=sys.stderr)
    return result_code


if __name__ == "__main__":
    sys.exit(main())
