"""Tests for cascade/explain.py."""

import tempfile
from pathlib import Path
from unittest import TestCase

from cascade.explain import explain_file, explain_function


class TestExplain(TestCase):
    def test_explain_function(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def add(a, b):
    """Add two numbers."""
    result = a + b
    return result
''')
            f.flush()
            result = explain_function(Path(f.name), "add")
            self.assertIn("add()", result)
            self.assertIn("Parameters", result)
            Path(f.name).unlink(missing_ok=True)

    def test_explain_file_structure(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import os
import sys

def hello(name):
    return f"Hello {name}"

class Greeter:
    def greet(self):
        return "Hi"
''')
            f.flush()
            result = explain_file(Path(f.name))
            self.assertIn("def hello(name)", result)
            self.assertIn("Greeter", result)
            Path(f.name).unlink(missing_ok=True)

    def test_explain_missing_function(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('x = 1\n')
            f.flush()
            result = explain_function(Path(f.name), "nonexistent")
            self.assertIn("not found", result)
            Path(f.name).unlink(missing_ok=True)
