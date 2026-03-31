#!/usr/bin/env python3
## @file core.py
# @brief Thin wrapper that dispatches to the 1:1 ported implementation module.

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from . import dng2jpg as ported

PROGRAM = "dng2jpg"
OWNER = "Ogekuri"
REPOSITORY = "DNG2JPG"

_VERSION_CACHE_FILE = (
    Path.home() / ".cache" / PROGRAM / "check_version_idle-time.json"
)
## @brief Idle-delay applied after successful latest-release checks.
_VERSION_CHECK_SUCCESS_IDLE_DELAY_SECONDS = 3600
## @brief Idle-delay applied after any latest-release check error.
_VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS = 86400


def _management_help() -> str:
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


def _write_version_cache(idle_delay_seconds: int) -> None:
    """
    @brief Persist latest-release cache metadata as JSON.
    @details Computes `last_check_*` and `idle_time_*` fields from the current
    epoch, creates the cache parent directory when missing, and rewrites the
    cache JSON atomically via `Path.write_text`. Complexity: O(1). Side
    effects: directory creation and cache file overwrite.
    @param idle_delay_seconds {int} Idle-delay in seconds added to the current
    epoch to derive the next `idle_time_epoch`.
    @return {None} No return value.
    @throws {OSError} Directory creation or cache-file write failure.
    @satisfies REQ-016, REQ-150, REQ-151
    @post `_VERSION_CACHE_FILE` stores the latest check epoch and derived
    idle-time metadata.
    """
    import json
    import time

    now_epoch = int(time.time())
    idle_time_epoch = now_epoch + int(idle_delay_seconds)
    payload = {
        "last_check_epoch": now_epoch,
        "last_check_human": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_epoch)),
        "idle_time_epoch": idle_time_epoch,
        "idle_time_human": time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(idle_time_epoch)
        ),
    }
    _VERSION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _VERSION_CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _should_skip_version_check(force: bool) -> bool:
    """
    @brief Evaluate whether cached idle-time suppresses a network version check.
    @details Returns `False` when forced, when the cache file is absent, when
    cache JSON decoding fails, or when `idle_time_epoch` is missing/invalid.
    Returns `True` only when the current epoch is strictly earlier than the
    cached idle-time. Complexity: O(1). Side effect: cache-file read.
    @param force {bool} Bypass flag that disables cache suppression when true.
    @return {bool} True if the current invocation must skip the network check;
    False otherwise.
    @throws {None} Cache read and decode failures are converted to `False`.
    @satisfies REQ-016
    """
    import json
    import time

    if force or not _VERSION_CACHE_FILE.exists():
        return False
    try:
        data = json.loads(_VERSION_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    idle_time_epoch = data.get("idle_time_epoch")
    if not isinstance(idle_time_epoch, int):
        return False
    return int(time.time()) < idle_time_epoch


def _check_online_version(force: bool) -> None:
    """
    @brief Execute the latest-release check and refresh cache idle-time policy.
    @details Skips the network request when `_should_skip_version_check(...)`
    returns true. Otherwise performs one GitHub latest-release API request,
    normalizes the returned tag name, assigns idle-delay `3600` seconds after a
    successful attempt, assigns idle-delay `86400` seconds after any handled
    request/parsing error, rewrites the cache JSON after every attempted API
    call, and then emits the status or error message. Complexity: O(1). Side
    effects: network I/O, cache-file rewrite, stdout/stderr output.
    @param force {bool} Bypass flag that forces a network request even when the
    cache idle-time is still active.
    @return {None} No return value.
    @throws {OSError} Cache-file rewrite failure after a completed API attempt.
    @satisfies REQ-016, REQ-150, REQ-151
    @see _should_skip_version_check
    @see _write_version_cache
    """
    import json
    from urllib import error, request

    if _should_skip_version_check(force):
        return

    endpoint = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/releases/latest"
    req = request.Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{PROGRAM}/version-check",
        },
    )
    idle_delay_seconds = _VERSION_CHECK_SUCCESS_IDLE_DELAY_SECONDS
    status_message = ""
    status_stream = sys.stderr
    try:
        with request.urlopen(req, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Unexpected latest-release payload shape.")
        latest_raw = payload.get("tag_name")
        latest = str(latest_raw or "").strip()
        if latest.startswith("v"):
            latest = latest[1:]
        if latest and latest != __version__:
            status_message = (
                f"\033[92mVersione Disponibile: {latest} | "
                f"Versione Installata: {__version__}\033[0m"
            )
            status_stream = sys.stdout
        else:
            status_message = (
                f"\033[91mVersione Disponibile: {latest or 'unknown'} | "
                f"Versione Installata: {__version__}\033[0m"
            )
    except error.HTTPError as http_error:
        idle_delay_seconds = _VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS
        status_message = (
            f"\033[91mVersion check failed (HTTP {http_error.code}).\033[0m"
        )
    except error.URLError as url_error:
        idle_delay_seconds = _VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS
        status_message = (
            f"\033[91mVersion check failed: {url_error.reason}.\033[0m"
        )
    except (OSError, ValueError, json.JSONDecodeError) as generic_error:
        idle_delay_seconds = _VERSION_CHECK_ERROR_IDLE_DELAY_SECONDS
        status_message = f"\033[91mVersion check failed: {generic_error}.\033[0m"

    _write_version_cache(idle_delay_seconds)
    print(status_message, file=status_stream)


def _run_management(command: list[str]) -> int:
    import platform
    import subprocess

    if platform.system() == "Linux":
        return int(subprocess.run(command, check=False).returncode)
    print(
        "\033[91mThis command is automatic only on Linux. Run it manually:\033[0m",
        file=sys.stderr,
    )
    print(" ".join(command))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    first = args[0] if args else None

    force_check = first in {"--ver", "--version"}
    _check_online_version(force=force_check)

    if not args:
        ported.print_help(__version__)
        return 0

    if first == "--help":
        print(_management_help())
        print()
        ported.print_help(__version__)
        return 0

    if first in {"--ver", "--version"}:
        print(__version__)
        return 0

    if first == "--upgrade":
        return _run_management(
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

    if first == "--uninstall":
        return _run_management(["uv", "tool", "uninstall", PROGRAM])

    return int(ported.run(args))
