"""Tests for indexer module."""

import pytest

from cascade.indexer import CodeIndex, cosine_similarity, tokenize


class TestIndexer:
    def test_tokenize_extracts_words(self):
        tokens = tokenize("hello world foo bar")
        assert "hello" in tokens
        assert "world" in tokens

    def test_cosine_similarity_identical(self):
        vec = {"a": 1.0, "b": 0.5}
        score = cosine_similarity(vec, vec)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_code_index_builds_and_searches(self, tmp_path):
        (tmp_path / "utils.py").write_text("def add(a, b):\n    return a + b")
        (tmp_path / "main.py").write_text("from utils import add\n\nresult = add(1, 2)")
        idx = CodeIndex(tmp_path)
        idx.build(max_files=10)
        assert idx.loaded
        results = idx.search("add function", top_k=3)
        assert len(results) > 0
        paths = [r[0] for r in results]
        assert "utils.py" in paths or "main.py" in paths

    def test_get_snippet_returns_context(self, tmp_path):
        (tmp_path / "code.py").write_text("line1\nline2\nline3\ntarget\nline5\nline6")
        idx = CodeIndex(tmp_path)
        idx.build(max_files=10)
        snippet = idx.get_snippet("code.py", "target")
        assert "target" in snippet
