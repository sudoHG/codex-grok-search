#!/usr/bin/env python3
"""Bridge Codex to Grok Build from a private, repository-free run directory."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_RETENTION_DAYS = 7
DEFAULT_MAX_TURNS = 40
DEFAULT_TIMEOUT = 600
REQUIRED_MODEL = "grok-4.5"
RUN_MARKER = ".codex-grok-search-run-v1"
KEEP_MARKER = "KEEP"
RUN_ID_RE = re.compile(r"\A\d{8}T\d{6}Z-[0-9a-f]{32}\Z")
AUTH_FAILURE_RE = re.compile(
    r"not logged in|not authenticated|unauthorized|login required|please (?:log|sign) in|"
    r"authentication (?:failed|required)|invalid (?:access |refresh )?token|"
    r"token (?:expired|invalid)|re-authentication required",
    re.IGNORECASE,
)


class BridgeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_since(value: str | None, now: datetime) -> datetime | None:
    if not value:
        return None
    duration = re.fullmatch(r"(\d+)([hdw])", value.strip().lower())
    if duration:
        amount = int(duration.group(1))
        unit = duration.group(2)
        delta = {
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
        }[unit]
        return now - delta
    return parse_datetime(value)


def default_cache_root() -> Path:
    return Path.home() / ".cache" / "codex-grok-search" / "runs"


def private_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def private_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_json(path: Path, payload: object) -> None:
    private_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_text(path: Path, limit: int = 32 * 1024 * 1024) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise BridgeError("invalid_artifact", f"Cannot safely read {path.name}.")
    return path.read_text(encoding="utf-8")


def _inside_git_worktree(path: Path) -> bool:
    resolved = path.resolve()
    for parent in (resolved, *resolved.parents):
        git_entry = parent / ".git"
        if git_entry.exists() or git_entry.is_symlink():
            return True
    return False


def ensure_cache_root(create: bool = True) -> Path:
    root = default_cache_root()
    if create:
        private_mkdir(root)
    if not root.exists():
        raise BridgeError("cache_not_found", "No retained Grok runs were found.")
    resolved = root.resolve()
    if _inside_git_worktree(resolved):
        raise BridgeError(
            "unsafe_cache_root",
            "The Grok run cache resolves inside a Git worktree; move ~/.cache outside the repository.",
        )
    resolved.chmod(0o700)
    return resolved


def is_run_dir(path: Path) -> bool:
    if not RUN_ID_RE.fullmatch(path.name):
        return False
    try:
        return (
            path.is_dir()
            and not path.is_symlink()
            and read_text(path / RUN_MARKER, 128).strip()
            == "codex-grok-search run v1"
        )
    except (FileNotFoundError, OSError, BridgeError):
        return False


def load_manifest(run_dir: Path) -> dict[str, object]:
    try:
        payload = json.loads(read_text(run_dir / "manifest.json"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, BridgeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def cleanup_expired(root: Path, retention_days: int) -> list[str]:
    if retention_days < 0:
        return []
    cutoff = utc_now() - timedelta(days=retention_days)
    removed: list[str] = []
    for path in root.iterdir():
        if not is_run_dir(path) or (path / KEEP_MARKER).is_file():
            continue
        manifest = load_manifest(path)
        created = manifest.get("created_at")
        try:
            created_at = parse_datetime(str(created))
        except (TypeError, ValueError, OverflowError):
            continue
        if created_at < cutoff:
            shutil.rmtree(path)
            removed.append(path.name)
    return sorted(removed)


def create_run(root: Path, now: datetime, keep: bool) -> tuple[str, Path]:
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex}"
    run_dir = root / run_id
    run_dir.mkdir(mode=0o700)
    private_write(run_dir / RUN_MARKER, "codex-grok-search run v1\n")
    if keep:
        private_write(run_dir / KEEP_MARKER, "Pinned by user request.\n")
    return run_id, run_dir


def find_grok() -> str:
    candidates = [Path.home() / ".grok" / "bin" / "grok"]
    discovered = shutil.which("grok")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve(strict=True)
        except (FileNotFoundError, RuntimeError):
            continue
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return str(resolved)
    raise BridgeError(
        "grok_not_found",
        "Grok Build was not found. Install it, then make sure `grok` is available or ~/.grok/bin/grok exists.",
    )


def _base_environment() -> dict[str, str]:
    allowed = ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _copy_auth(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        return
    try:
        json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return
    shutil.copyfile(source, destination)
    destination.chmod(0o600)


def _persist_refreshed_auth(isolated_auth: Path, real_auth: Path) -> None:
    if not isolated_auth.is_file() or isolated_auth.is_symlink():
        return
    try:
        content = isolated_auth.read_text(encoding="utf-8")
        json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return
    real_auth.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_write(real_auth, content)


@contextmanager
def isolated_environment(run_dir: Path) -> Iterator[dict[str, str]]:
    """Expose only Grok auth and a minimal config; never expose the user's project."""
    with tempfile.TemporaryDirectory(prefix="codex-grok-search-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        home = root / "home"
        grok_home = home / ".grok"
        tmp = home / "tmp"
        for path in (home, grok_home, tmp):
            private_mkdir(path)

        real_auth = Path.home() / ".grok" / "auth.json"
        isolated_auth = grok_home / "auth.json"
        _copy_auth(real_auth, isolated_auth)
        private_write(
            grok_home / "config.toml",
            """[compat.cursor]
skills = false
rules = false
agents = false
mcps = false
hooks = false
sessions = false

[compat.claude]
skills = false
rules = false
agents = false
mcps = false
hooks = false
sessions = false

[compat.codex]
sessions = false
""",
        )
        env = _base_environment()
        env.update(
            {
                "HOME": str(home),
                "GROK_HOME": str(grok_home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "TMPDIR": str(tmp),
                "GROK_CURSOR_SKILLS_ENABLED": "false",
                "GROK_CURSOR_RULES_ENABLED": "false",
                "GROK_CURSOR_AGENTS_ENABLED": "false",
                "GROK_CURSOR_MCPS_ENABLED": "false",
                "GROK_CURSOR_HOOKS_ENABLED": "false",
                "GROK_CLAUDE_SKILLS_ENABLED": "false",
                "GROK_CLAUDE_RULES_ENABLED": "false",
                "GROK_CLAUDE_AGENTS_ENABLED": "false",
                "GROK_CLAUDE_MCPS_ENABLED": "false",
                "GROK_CLAUDE_HOOKS_ENABLED": "false",
            }
        )
        try:
            yield env
        finally:
            _persist_refreshed_auth(isolated_auth, real_auth)


def build_prompt(
    query: str,
    platform: str,
    since: datetime | None,
    until: datetime,
    depth: str,
) -> str:
    focus = {
        "x": "Focus on X/Twitter. Use X Search first, but include useful public-web context when helpful.",
        "reddit": "Focus on Reddit. Use public search and direct Reddit links when available.",
        "web": "Focus on the public web.",
        "auto": "Use X Search, Reddit, and the public web as useful for the task.",
    }[platform]
    window = (
        f"The requested time window is {iso_utc(since)} through {iso_utc(until)}."
        if since
        else f"Research current information through {iso_utc(until)}."
    )
    effort = (
        "Answer quickly with the most useful results; do not over-research."
        if depth == "quick"
        else "Research thoroughly and cross-check important claims when useful."
    )
    return f"""Act as Codex's Grok search worker.

User task:
{query}

Guidance:
- {focus}
- {window}
- {effort}
- Return a useful answer in Markdown with direct source links.
- If a date, metric, or claim cannot be verified, say so instead of inventing it.
- Do not inspect local files, repositories, environment variables, credentials, or configuration.
"""


def run_process(
    command: list[str], cwd: Path, env: dict[str, str], timeout: int
) -> tuple[int, str, str, bool]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        return process.returncode or 124, stdout, stderr, True
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise


def extract_answer(stdout: str) -> tuple[str | None, str]:
    stripped = stdout.strip()
    if not stripped:
        return None, "empty_stdout"
    try:
        envelope = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped, "raw_stdout"
    if isinstance(envelope, dict):
        text = envelope.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip(), "grok_json"
        return None, "grok_json_without_text"
    return stripped, "raw_stdout"


def recover_session(
    grok: str,
    session_id: str,
    run_dir: Path,
    env: dict[str, str],
    timeout: int,
) -> str | None:
    return_code, stdout, stderr, timed_out = run_process(
        [grok, "export", session_id], run_dir, env, min(timeout, 120)
    )
    if stdout.strip():
        private_write(run_dir / "session-export.md", stdout)
    if stderr.strip():
        private_write(run_dir / "session-export-error.txt", stderr)
    if timed_out or return_code != 0:
        return None
    marker = "## Assistant\n"
    if marker in stdout:
        answer = stdout.rsplit(marker, 1)[-1].strip()
        return answer or None
    return stdout.strip() or None


def run_grok(args: argparse.Namespace) -> int:
    if not args.query.strip():
        raise BridgeError("invalid_arguments", "The search request cannot be blank.")
    now = utc_now()
    try:
        since = parse_since(args.since, now)
        until = parse_datetime(args.until) if args.until else now
    except (ValueError, OverflowError) as exc:
        raise BridgeError("invalid_arguments", f"Invalid time boundary: {exc}") from exc
    if since and since > until:
        raise BridgeError("invalid_arguments", "--since must not be later than --until.")

    grok = find_grok()
    cache_root = ensure_cache_root()
    removed = cleanup_expired(cache_root, args.retention_days)
    run_id, run_dir = create_run(cache_root, now, args.keep_run)
    prompt = build_prompt(args.query, args.platform, since, until, args.depth)
    private_write(run_dir / "prompt.txt", prompt)
    session_id = str(uuid.uuid4())
    manifest: dict[str, object] = {
        "run_id": run_id,
        "created_at": iso_utc(now),
        "query": args.query,
        "platform_hint": args.platform,
        "depth": args.depth,
        "window": {
            "since": iso_utc(since) if since else None,
            "until": iso_utc(until),
        },
        "status": "running",
        "grok_model": REQUIRED_MODEL,
        "grok_session_id": session_id,
        "cwd": str(run_dir),
        "isolated_home": True,
        "cleaned_runs": removed,
        "keep": args.keep_run,
    }
    write_json(run_dir / "manifest.json", manifest)

    command = [
        grok,
        "--prompt-file",
        str(run_dir / "prompt.txt"),
        "--cwd",
        str(run_dir),
        "--session-id",
        session_id,
        "--tools",
        "x_search,web_search,web_fetch",
        "--deny",
        "MCPTool",
        "--always-approve",
        "--model",
        REQUIRED_MODEL,
        "--output-format",
        "json",
        "--no-memory",
        "--no-subagents",
        "--no-plan",
        "--max-turns",
        str(args.max_turns),
    ]
    with isolated_environment(run_dir) as env:
        return_code, stdout, stderr, timed_out = run_process(
            command, run_dir, env, args.timeout
        )
        private_write(run_dir / "stdout.txt", stdout)
        private_write(run_dir / "stderr.txt", stderr)
        answer, source = extract_answer(stdout)
        if not answer and not timed_out:
            answer = recover_session(
                grok, session_id, run_dir, env, args.timeout
            )
            if answer:
                source = "session_export"

    if answer:
        result_path = run_dir / "result.md"
        private_write(result_path, answer.rstrip() + "\n")
        status = "complete" if return_code == 0 and not timed_out else "partial"
        manifest.update(
            {
                "status": status,
                "completed_at": iso_utc(utc_now()),
                "grok_exit_code": return_code,
                "timed_out": timed_out,
                "result_source": source,
                "result_path": str(result_path),
            }
        )
        write_json(run_dir / "manifest.json", manifest)
        payload: dict[str, object] = {
            "ok": True,
            "run_id": run_id,
            "status": status,
            "result_path": str(result_path),
            "result_source": source,
        }
        if status == "partial":
            payload["warning"] = (
                "Grok returned usable output before the process ended unsuccessfully; "
                "the unfiltered result was retained."
            )
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    combined_error = "\n".join(part for part in (stdout, stderr) if part).strip()
    if timed_out:
        error = "grok_timed_out"
        message = "Grok timed out before returning a usable answer."
    elif AUTH_FAILURE_RE.search(combined_error):
        error = "grok_not_authenticated"
        message = "Grok reported that authentication is required. Run `grok login`, then retry."
    else:
        error = "grok_execution_failed"
        message = (
            "Grok did not return a usable answer. Its raw stdout and stderr were retained "
            "in the run directory."
        )
    manifest.update(
        {
            "status": "failed",
            "completed_at": iso_utc(utc_now()),
            "grok_exit_code": return_code,
            "timed_out": timed_out,
            "error": error,
        }
    )
    write_json(run_dir / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "ok": False,
                "run_id": run_id,
                "error": error,
                "message": message,
                "run_path": str(run_dir),
            },
            ensure_ascii=False,
        )
    )
    return 1


def list_runs(_args: argparse.Namespace) -> int:
    try:
        root = ensure_cache_root(create=False)
    except BridgeError as exc:
        if exc.code == "cache_not_found":
            print("[]")
            return 0
        raise
    rows = []
    for run_dir in sorted(root.iterdir(), reverse=True):
        if not is_run_dir(run_dir):
            continue
        manifest = load_manifest(run_dir)
        rows.append(
            {
                "run_id": run_dir.name,
                "created_at": manifest.get("created_at"),
                "status": manifest.get("status", "unknown"),
                "platform_hint": manifest.get("platform_hint", manifest.get("platform")),
                "keep": (run_dir / KEEP_MARKER).is_file(),
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def show_run(args: argparse.Namespace) -> int:
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise BridgeError("invalid_run_id", "The run ID is malformed.")
    root = ensure_cache_root(create=False)
    run_dir = root / args.run_id
    if not is_run_dir(run_dir):
        raise BridgeError("run_not_found", "The requested run was not found.")
    result_path = run_dir / "result.md"
    result = read_text(result_path) if result_path.is_file() else None
    print(
        json.dumps(
            {
                "ok": True,
                "run_id": args.run_id,
                "manifest": load_manifest(run_dir),
                "result": result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cleanup_command(args: argparse.Namespace) -> int:
    root = ensure_cache_root()
    removed = cleanup_expired(root, args.retention_days)
    print(json.dumps({"ok": True, "removed": removed, "count": len(removed)}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run Grok from a private isolated directory")
    run_parser.add_argument("query", help="Complete search or research request")
    run_parser.add_argument("--platform", choices=("auto", "x", "reddit", "web"), default="auto")
    run_parser.add_argument("--depth", choices=("quick", "deep"), default="quick")
    run_parser.add_argument("--since", help="ISO-8601 timestamp or duration such as 24h, 7d, or 2w")
    run_parser.add_argument("--until", help="ISO-8601 end timestamp; defaults to now")
    run_parser.add_argument("--keep-run", action="store_true", help="Keep this run during cleanup")
    run_parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    run_parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    run_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    run_parser.set_defaults(handler=run_grok)

    list_parser = subparsers.add_parser("list", help="List retained runs")
    list_parser.set_defaults(handler=list_runs)

    show_parser = subparsers.add_parser("show", help="Read a retained Grok answer")
    show_parser.add_argument("run_id")
    show_parser.set_defaults(handler=show_run)

    cleanup_parser = subparsers.add_parser("cleanup", help="Remove expired unpinned runs")
    cleanup_parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    cleanup_parser.set_defaults(handler=cleanup_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "retention_days") and args.retention_days < 0:
        parser.error("--retention-days must be non-negative")
    if hasattr(args, "timeout") and args.timeout < 1:
        parser.error("--timeout must be at least 1 second")
    if hasattr(args, "max_turns") and args.max_turns < 1:
        parser.error("--max-turns must be at least 1")
    try:
        return args.handler(args)
    except KeyboardInterrupt:
        print(
            json.dumps(
                {"ok": False, "error": "interrupted", "message": "The Grok run was interrupted."},
                ensure_ascii=False,
            )
        )
        return 130
    except BridgeError as exc:
        print(
            json.dumps(
                {"ok": False, "error": exc.code, "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": "local_runtime_error", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
