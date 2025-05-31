"""
Module: utils/logger.py
Description: Simple logging utility with verbosity levels
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
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
#   2025-04-30 - José Ignacio - Initial creation

import sys

from core.constants import Verbosity
from config.settings import VERBOSITY_LEVEL


def LOG(msg, level=Verbosity.MEDIUM):
    """
    Logs a general informational message if the given verbosity level is allowed.
    """
    if level <= VERBOSITY_LEVEL:
        print(f"[LOG] {msg}")


def WRN(msg):
    """
    Logs a warning message, regardless of the global verbosity setting.
    """
    print(f"[WRN] {msg}")


def ERR(msg):
    """
    Logs an error message, regardless of the global verbosity setting.
    """
    print(f"[ERR] {msg}")


def ABR(msg):
    """
    Logs an error message, and abort !!!
    """
    print(f"[ABR] {msg}")
    sys.exit(1)


def DBG(msg):
    """
    Logs a debug message if the given verbosity level is high (equivalent to LOG(msg, level=HIGH).
    """
    if VERBOSITY_LEVEL == Verbosity.DEBUG:
        print(f"[DBG] {msg}")

