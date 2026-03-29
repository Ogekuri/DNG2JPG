#!/usr/bin/env python3
## @file core.py
# @brief Core command dispatch and dng2jpg CLI runtime orchestration.
# @details Provides command routing and management command workflows.

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence
from urllib import error, request

from . import __version__

PROGRAM = "dng2jpg"
OWNER = "Ogekuri"
REPOSITORY = "DNG2JPG"
VERSION_ENDPOINT = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/releases/latest"
DEFAULT_IDLE_DELAY_SECONDS = 300
RATE_LIMIT_IDLE_DELAY_SECONDS = 3600
HTTP_TIMEOUT_SECONDS = 2
CACHE_FILE = Path.home() / ".cache" / PROGRAM / "check_version_idle-time.json"
BRIGHT_GREEN = "\033[92m"
BRIGHT_RED = "\033[91m"
RESET_COLOR = "\033[0m"


def _usage_text() -> str:
    return (
        f"Usage: {PROGRAM} [command] [options] ({__version__})\n\n"
        "Management Commands:\n"
        f"  --upgrade   - Reinstall {PROGRAM} on Linux; print manual command elsewhere.\n"
        f"  --uninstall - Uninstall {PROGRAM} on Linux; print manual command elsewhere.\n"
        f"  --ver       - Print the {PROGRAM} version.\n"
        f"  --version   - Print the {PROGRAM} version.\n"
        "  --help      - Print the full help screen or the help text of a specific command.\n\n"
        "Commands:\n"
        "  ..."
    )


def _normalize_version(raw_version: str) -> str:
    trimmed = raw_version.strip()
    if trimmed.startswith("v"):
        trimmed = trimmed[1:]
    return trimmed


def _version_tuple(version: str) -> tuple[int, int, int]:
    normalized = _normalize_version(version)
    clean = normalized.split("-", 1)[0].split("+", 1)[0]
    parts = clean.split(".")
    if len(parts) < 3:
        raise ValueError(f"Invalid version format: {version}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _write_cache(delay_seconds: int) -> None:
    now_epoch = int(time.time())
    idle_time_epoch = now_epoch + delay_seconds
    payload = {
        "last_check_epoch": now_epoch,
        "last_check_human": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_epoch)),
        "idle_time_epoch": idle_time_epoch,
        "idle_time_human": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(idle_time_epoch)),
    }
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _should_skip_check(force: bool) -> bool:
    if force or not CACHE_FILE.exists():
        return False

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    idle_time_epoch = data.get("idle_time_epoch")
    if not isinstance(idle_time_epoch, int):
        return False

    return int(time.time()) < idle_time_epoch


def _fetch_latest_release_version() -> str:
    req = request.Request(
        VERSION_ENDPOINT,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{PROGRAM}/version-check",
        },
    )
    with request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    latest = payload.get("tag_name")
    if not isinstance(latest, str) or not latest.strip():
        raise ValueError("GitHub API response does not include a valid tag_name.")
    return _normalize_version(latest)


def check_online_version(*, force: bool = False) -> None:
    if _should_skip_check(force):
        return

    installed = _normalize_version(__version__)
    try:
        latest = _fetch_latest_release_version()
    except error.HTTPError as http_error:
        if http_error.code == 429:
            _write_cache(RATE_LIMIT_IDLE_DELAY_SECONDS)
        print(
            f"{BRIGHT_RED}Version check failed (HTTP {http_error.code}).{RESET_COLOR}",
            file=sys.stderr,
        )
        return
    except error.URLError as url_error:
        print(f"{BRIGHT_RED}Version check failed: {url_error.reason}.{RESET_COLOR}", file=sys.stderr)
        return
    except (OSError, ValueError, json.JSONDecodeError) as generic_error:
        print(f"{BRIGHT_RED}Version check failed: {generic_error}.{RESET_COLOR}", file=sys.stderr)
        return

    _write_cache(DEFAULT_IDLE_DELAY_SECONDS)

    try:
        is_newer = _version_tuple(latest) > _version_tuple(installed)
    except ValueError as parse_error:
        print(
            f"{BRIGHT_RED}Version comparison failed: {parse_error}.{RESET_COLOR}",
            file=sys.stderr,
        )
        return

    if is_newer:
        print(
            f"{BRIGHT_GREEN}Versione Disponibile: {latest} | Versione Installata: {installed}{RESET_COLOR}"
        )
        return

    print(
        f"{BRIGHT_RED}Versione Disponibile: {latest} | Versione Installata: {installed}{RESET_COLOR}",
        file=sys.stderr,
    )


def _run_management_command(command: Sequence[str]) -> int:
    if platform.system() == "Linux":
        result = subprocess.run(command, check=False)
        return int(result.returncode)

    print(
        f"{BRIGHT_RED}This command is automatic only on Linux. Run it manually:{RESET_COLOR}",
        file=sys.stderr,
    )
    print(" ".join(command))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    first_arg = args[0] if args else None
    force_check = first_arg in {"--ver", "--version"}
    check_online_version(force=force_check)

    if not args or first_arg == "--help":
        print(_usage_text())
        return 0

    if first_arg in {"--ver", "--version"}:
        print(_normalize_version(__version__))
        return 0

    if first_arg == "--upgrade":
        return _run_management_command(
            [
                "uv",
                "tool",
                "install",
                PROGRAM,
                "--force",
                "--from",
                f"git+https://github.com/{OWNER}/{REPOSITORY}.git",
            ]
        )

    if first_arg == "--uninstall":
        return _run_management_command(["uv", "tool", "uninstall", PROGRAM])

    print(f"{BRIGHT_RED}Unknown command: {first_arg}{RESET_COLOR}", file=sys.stderr)
    print(_usage_text())
    return 2
