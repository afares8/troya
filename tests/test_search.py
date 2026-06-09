"""Tests for search module."""

from pathlib import Path

from cascade.search import build_tree, get_project_stats, grep_project


class TestSearch:
    def test_build_tree_shows_files(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "nested.py").write_text("y = 2")
        tree = build_tree(str(tmp_path), max_depth=3)
        assert "test.py" in tree
        assert "nested.py" in tree

    def test_get_project_stats_counts_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "sub").mkdir()
        stats = get_project_stats(str(tmp_path))
        assert stats["total_files"] == 2
        assert ".py" in stats["languages"]
        assert stats["languages"][".py"] == 2

    def test_grep_project_finds_pattern(self, tmp_path):
        (tmp_path / "main.py").write_text("def hello():\n    return 42")
        results = grep_project("hello", root=str(tmp_path))
        assert len(results) > 0
        assert results[0]["file"] == "main.py"
        assert "hello" in results[0]["text"]
