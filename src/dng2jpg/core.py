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
    try:
        with request.urlopen(req, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as http_error:
        if http_error.code == 429:
            _write_version_cache(3600)
        print(
            f"\033[91mVersion check failed (HTTP {http_error.code}).\033[0m",
            file=sys.stderr,
        )
        return
    except error.URLError as url_error:
        print(f"\033[91mVersion check failed: {url_error.reason}.\033[0m", file=sys.stderr)
        return
    except (OSError, ValueError, json.JSONDecodeError) as generic_error:
        print(f"\033[91mVersion check failed: {generic_error}.\033[0m", file=sys.stderr)
        return

    latest_raw = payload.get("tag_name")
    latest = str(latest_raw or "").strip()
    if latest.startswith("v"):
        latest = latest[1:]

    _write_version_cache(300)

    if latest and latest != __version__:
        print(
            f"\033[92mVersione Disponibile: {latest} | Versione Installata: {__version__}\033[0m"
        )
    else:
        print(
            f"\033[91mVersione Disponibile: {latest or 'unknown'} | Versione Installata: {__version__}\033[0m",
            file=sys.stderr,
        )


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
