#!/usr/bin/env python3
"""
Module: test_validation.py
Description: Unit tests for MQTT and event JSON validation in dfs3
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

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from mqtt.listener import validate_event as validate_mqtt_event
from core.event_handler import validate_event 


# ---------- Tests for MQTT event validation ----------

def test_valid_mqtt_event():
    """Test that a fully valid MQTT message is accepted."""

    valid = {
        "block_id": "a"*64,
        "event_type": "node_status",
        "timestamp": "2025-04-30T21:00:00Z",
        "source_node_id": "b"*64
    }

    assert validate_mqtt_event(valid) is True


def test_invalid_mqtt_event_missing_field():
    """Test that an MQTT message missing required fields is rejected."""

    invalid = {
        "block_id": "a"*64,
        "event_type": "node_status",
        "timestamp": "2025-04-30T21:00:00Z"
        # missing source_node_id
    }

    assert validate_mqtt_event(invalid) is False


def test_invalid_mqtt_event_bad_format():
    """Test that an MQTT message with invalid SHA-256 or event type is rejected."""

    invalid = {
        "block_id": "XYZ123",  # not sha256 hex
        "event_type": "invalid_type",
        "timestamp": "2025-04-30T21:00:00Z",
        "source_node_id": "123"
    }

    assert validate_mqtt_event(invalid) is False


# ---------- Tests for IOTA event validation ----------

def test_valid_event():
    """Test that a fully valid dfs3 event JSON is accepted."""

    valid_event = {
        "event_type": "node_status",
        "timestamp": "2025-04-30T21:00:00Z",
        "origin": "a"*64,
        "payload": {"uptime": 1234}
    }

    assert validate_event(valid_event) is True


def test_invalid_event_missing_field():
    """Test that a dfs3 event JSON missing required fields is rejected."""

    invalid_event = {
        "event_type": "node_status",
        "timestamp": "2025-04-30T21:00:00Z",
        # missing origin and payload
    }

    assert validate_event(invalid_event) is False


def test_invalid_event_bad_origin():
    """Test that a dfs3 event JSON with invalid origin format is rejected."""

    invalid_event = {
        "event_type": "node_status",
        "timestamp": "2025-04-30T21:00:00Z",
        "origin": "NOT_SHA256",
        "payload": {}
    }

    assert validate_event(invalid_event) is False

