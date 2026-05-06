"""Pytest configuration — ensures the project root is on sys.path.

This allows tests to import ``utils`` and ``main`` without installing the
package, regardless of the directory from which pytest is invoked.
"""

import sys
import os

# Insert the project root (parent of this file) at the front of sys.path
sys.path.insert(0, os.path.dirname(__file__))
