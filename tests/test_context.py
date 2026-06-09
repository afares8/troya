"""Tests for context module."""

from cascade.context import ContextManager


class TestContextManager:
    def test_add_message(self):
        ctx = ContextManager(system_prompt="test")
        ctx.add_message("user", "hello")
        assert len(ctx.messages) == 1
        assert ctx.messages[0]["role"] == "user"

    def test_clear_removes_messages(self):
        ctx = ContextManager(system_prompt="test")
        ctx.add_message("user", "hello")
        ctx.clear()
        assert len(ctx.messages) == 0

    def test_build_prompt_includes_files(self):
        ctx = ContextManager(system_prompt="test")
        ctx.files["test.py"] = "x = 1"
        prompt = ctx.build_prompt("What does this do?")
        assert "test.py" in prompt
        assert "x = 1" in prompt
