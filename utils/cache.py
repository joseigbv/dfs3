"""
Module: cache.py
Description: Implements a TTL-based user cache that resets expiration on access,
             extending cachetools.TTLCache with access-aware eviction policy.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-11
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
#   2025-05-12 - José Ignacio Bravo - Initial creation

from cachetools import TTLCache
from typing import TypeVar, Generic

K = TypeVar("K")
V = TypeVar("V")

class UserCache(TTLCache, Generic[K, V]):
    """
    Custom TTLCache that resets the TTL of an item on each access,
    simulating an access-based expiration policy.
    """
    def __getitem__(self, key: K) -> V:
        value = super().__getitem__(key)
        # Refresh the TTL by reinserting the item
        super().__setitem__(key, value)
        return value

