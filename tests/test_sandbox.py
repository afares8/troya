"""Tests for sandbox module."""

from cascade.sandbox import is_safe_code, run_sandboxed


class TestSandbox:
    def test_safe_code_runs(self):
        result = run_sandboxed("print('hello')")
        assert result["success"]
        assert "hello" in result["output"]

    def test_math_works(self):
        result = run_sandboxed("print(2 + 2)")
        assert result["success"]
        assert "4" in result["output"]

    def test_os_system_blocked(self):
        result = run_sandboxed("import os\nos.system('ls')")
        assert not result["success"]
        assert "Blocked" in result["error"]

    def test_eval_blocked(self):
        result = run_sandboxed("eval('1+1')")
        assert not result["success"]
        assert "Blocked" in result["error"]

    def test_nameerror_detected(self):
        result = run_sandboxed("print(undefined_var)")
        assert not result["success"]
        assert "NameError" in result["error"]
