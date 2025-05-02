"""
Module: time.py
Description: Utility functions for handling date and time conversions in the dfs3 system.
Includes helpers for converting between ISO 8601 and Unix epoch formats.

Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-01
"""

# =============================================================
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
#   2025-05-02 - José Ignacio Bravo - Initial creation
# =============================================================

from datetime import datetime, timezone


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_to_epoch(iso_str: str) -> int:
    """
    Converts an ISO 8601 datetime string to a Unix epoch timestamp in seconds.

    Args:
        iso_str: The datetime string (e.g. '2025-05-01T12:34:56Z').

    Returns:
        Epoch time as integer (seconds since 1970-01-01).
    """
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str.replace("Z", "+00:00")

        # Aqui se produce la "magia"
        dt = datetime.fromisoformat(iso_str)

        return int(dt.timestamp())

    except Exception:
        return 0

