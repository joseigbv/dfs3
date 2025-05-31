"""
Module: system.py
Description: System-level utility functions (disk, uptime, etc.).
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-01
"""
# MIT License
# Copyright (c) 2025 José Ignacio Bravo <nacho.bravo@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Change history:
#   2025-04-30 - José Ignacio Bravo - Initial creation

import shutil
import socket


def get_total_disk_space(path: str = "/") -> int:
    """
    Returns total disk space in bytes for the given path.
    """
    return shutil.disk_usage(path).total


def get_uptime_seconds() -> int:
    """
    Returns the system uptime in seconds. Linux only.
    """
    try:
        with open("/proc/uptime", "r") as f:
            uptime_str = f.readline().split()[0]
            return int(float(uptime_str))

    except Exception:
        return 0


def get_local_ip() -> str:
    """
    Returns the local IP address of the machine (non-loopback).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No hace falta que haya conexión real
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

