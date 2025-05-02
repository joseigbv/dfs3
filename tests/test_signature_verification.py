#!/usr/bin/env python3
"""
Test: test_signature_verification.py
Description: Tests signature validation for dfs3 events.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
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
#   2025-04-30 - José Ignacio Bravo - Initial creation
# =============================================================

import pytest
import tempfile

from pathlib import Path

from utils.crypto import decrypt_private_key
from core.nodes import init_or_load_node
from core.events import build_node_registered_event, verify_event_signature


def test_event_signature_verification(monkeypatch):
    """Test that the generated event has a valid signature."""

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"

        monkeypatch.setattr("getpass.getpass", lambda prompt="": "test-passphrase")
        config = init_or_load_node(config_path=str(config_path))
        private_key = decrypt_private_key(config, "test-passphrase")
        event = build_node_registered_event(config, private_key)

        assert verify_event_signature(event) is True

        # Modify event to invalidate signature
        event["payload"]["alias"] = "tampered-node"
        assert verify_event_signature(event) is False

