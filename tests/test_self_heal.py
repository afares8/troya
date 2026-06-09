"""Tests for self_heal module."""

from cascade.self_heal import analyze_error, _apply_heuristic_fix


class TestSelfHeal:
    def test_analyze_nameerror(self):
        error = "Traceback:\n  File 'test.py', line 1\nNameError: name 'y' is not defined"
        info = analyze_error(error)
        assert info["error_type"] == "NameError"
        assert "y" in info["error_message"]
        assert "not defined" in info["suggestion"]

    def test_analyze_syntaxerror(self):
        error = "SyntaxError: invalid syntax"
        info = analyze_error(error)
        assert info["error_type"] == "SyntaxError"
        assert "syntax" in info["suggestion"]

    def test_heuristic_nameerror_fix(self):
        code = "print(y)"
        info = {"error_type": "NameError", "error_message": "'y'"}
        fixed = _apply_heuristic_fix(code, info)
        assert "y = None" in fixed

    def test_heuristic_divzero_fix(self):
        code = "x = 1 / 0"
        info = {"error_type": "ZeroDivisionError", "error_message": "division by zero"}
        fixed = _apply_heuristic_fix(code, info)
        assert "/ 1" in fixed
