#!/usr/bin/env python3
"""Compatibility helpers required by ported dng2jpg source."""

import platform
import sys


def get_runtime_os():
    system = platform.system().lower()
    if system.startswith("linux"):
        return "linux"
    if system.startswith("darwin"):
        return "darwin"
    if system.startswith("win"):
        return "windows"
    return system


def print_error(message):
    print(message, file=sys.stderr)


def print_info(message):
    print(message)


def print_success(message):
    print(message)
