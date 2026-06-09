"""Tests for scaffold module."""

from cascade.scaffold import list_templates, scaffold_project


class TestScaffold:
    def test_list_templates_returns_known(self):
        templates = list_templates()
        assert "fastapi" in templates
        assert "react" in templates
        assert "flask" in templates

    def test_scaffold_fastapi_creates_files(self, tmp_path):
        count = scaffold_project("fastapi", "test_api", tmp_path)
        assert count > 0
        assert (tmp_path / "test_api" / "main.py").exists()
        assert (tmp_path / "test_api" / "requirements.txt").exists()

    def test_scaffold_unknown_returns_zero(self, tmp_path):
        count = scaffold_project("unknown", "test", tmp_path)
        assert count == 0
