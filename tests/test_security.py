"""Tests for cascade/security.py."""

import tempfile
from pathlib import Path
from unittest import TestCase

from cascade.security import scan_file, scan_project


class TestSecurity(TestCase):
    def test_no_secrets_in_safe_code(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def hello():
    print("Hello world")
    x = 1 + 2
    return x
''')
            f.flush()
            results = scan_file(Path(f.name))
            self.assertEqual(len(results), 0)
        Path(f.name).unlink(missing_ok=True)

    def test_detects_hardcoded_password(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
DB_PASSWORD = "super_secret_password_123"
''')
            f.flush()
            results = scan_file(Path(f.name))
            passwords = [r for r in results if "password" in r["category"].lower() or "secret" in r["category"].lower()]
            self.assertTrue(len(passwords) > 0)
        Path(f.name).unlink(missing_ok=True)

    def test_detects_eval(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
result = eval(user_input)
''')
            f.flush()
            results = scan_file(Path(f.name))
            evals = [r for r in results if r["category"] == "Eval Usage"]
            self.assertEqual(len(evals), 1)
        Path(f.name).unlink(missing_ok=True)

    def test_detects_shell_true(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
import subprocess
subprocess.run(["ls"], shell=True)
''')
            f.flush()
            results = scan_file(Path(f.name))
            shells = [r for r in results if r["category"] == "Shell True"]
            self.assertEqual(len(shells), 1)
        Path(f.name).unlink(missing_ok=True)

    def test_scan_project(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "safe.py").write_text('x = 1\n')
            Path(td, "bad.py").write_text('password = "secret123"\n')
            report = scan_project(Path(td), max_files=10)
            self.assertGreater(report["total"], 0)
            self.assertEqual(report["scanned"], 2)
